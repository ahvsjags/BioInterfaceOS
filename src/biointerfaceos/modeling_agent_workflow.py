"""Offline ModelBuilder and Statistician agent evaluation."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.agent_runtime import TraceLedger
from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string


class ModelingAgentError(RuntimeError):
    """Raised when modeling-agent contracts are invalid."""


@dataclass(frozen=True)
class ModelingSummary:
    """Summary of one deterministic model-plan evaluation."""

    plans: int
    executable_plans: int
    rejected: int
    metric_hacking_rejected: int
    split_modification_rejected: int
    heldout_tuning_rejected: int
    tests_generated: int
    preregistration_complete: bool
    sandbox_passed: bool
    splits_unchanged: bool
    selected_pipeline: str
    trace_events: int
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise ModelingAgentError(f"{label} fields do not match schema")


class ModelingAgentWorkflow:
    """Validate executable modeling plans without allowing metric hacking."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/agents/modeling_fixture.json")
        self.output_root = output_root or self.root / "reports/agents/modeling"
        self.schema_path = schema_path or self.root / "agents/modeling/modeling.v1.json"

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "modeling schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ModelingAgentError(f"cannot load modeling schema: {exc}") from exc
        _keys(
            schema,
            {"schema_version", "agent", "plan_fields", "rejection_reasons"},
            "modeling schema",
        )
        if schema.get("schema_version") != 1 or schema.get("agent") != "ModelBuilderStatistician":
            raise ModelingAgentError("modeling schema version or agent is invalid")
        fields = schema.get("plan_fields")
        reasons = schema.get("rejection_reasons")
        if (
            not isinstance(fields, list)
            or not fields
            or not all(isinstance(field, str) and field for field in fields)
            or not isinstance(reasons, list)
            or not reasons
            or not all(isinstance(reason, str) and reason for reason in reasons)
        ):
            raise ModelingAgentError("modeling schema fields or reasons are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "modeling fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ModelingAgentError(f"cannot load modeling fixture: {exc}") from exc
        _keys(data, {"schema_version", "mode", "inputs", "plans"}, "modeling fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "modeling_fixture":
            raise ModelingAgentError("modeling fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("plans"), list):
            raise ModelingAgentError("modeling inputs/plans are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        expected = {
            "T068 grading metrics": (
                self.root / "reports/benchmark/grading/metrics.json",
                "a73e438ccde47a883fd7a9e0e6c566be6c66e39f6e96be100968bd749b6f32e5",
            ),
            "T071 model results": (
                self.root / "reports/models/m1/m1_results.json",
                "46777fd6dc4838e027ae1da95e71de32d8cc66c2cd0717130ae9b17947059a39",
            ),
            "T078 uncertainty results": (
                self.root / "reports/models/uncertainty/uncertainty_results.json",
                "5712a16ac04b2ac80ae972f962e234c1cc34f7d3f7c93283174895bbd00cc5e2",
            ),
            "frozen development split": (
                self.root / "reports/splits/frozen_dev/split_manifest.json",
                "c1b32d9b2b23cca7ec9ba7bf7cc0471514fdf2a0fb07a3204461b5b8cfa150c2",
            ),
        }
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for value in fixture["inputs"]:
            row = _mapping(value, "modeling input")
            _keys(row, {"label", "path", "sha256", "split"}, "modeling input")
            label = _string(row.get("label"), "modeling input label")
            if label not in expected:
                raise ModelingAgentError(f"unexpected modeling input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "modeling input path")).resolve(strict=True)
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise ModelingAgentError(f"modeling input path or checksum differs: {label}")
            if row.get("split") not in {"train", "validation", "frozen"}:
                raise ModelingAgentError(f"modeling input split is invalid: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise ModelingAgentError(f"modeling input checksum differs: {label}")
            rows.append({"label": label, "path": row["path"], "split": row["split"]})
            seen.add(label)
        if seen != set(expected):
            raise ModelingAgentError("modeling inputs are incomplete")
        return tuple(rows)

    @staticmethod
    def _plans(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        required = {
            "plan_id",
            "role",
            "model_api",
            "code",
            "generated_tests",
            "preregistration",
            "metric_policy",
            "split_policy",
            "expected_status",
        }
        plans: list[dict[str, Any]] = []
        seen: set[str] = set()
        allowed = {
            "EXECUTE",
            "REJECT_METRIC_HACKING",
            "REJECT_SPLIT_MODIFICATION",
            "REJECT_HELDOUT_TUNING",
        }
        for value in fixture["plans"]:
            plan = _mapping(value, "modeling plan")
            _keys(plan, required, "modeling plan")
            plan_id = _string(plan.get("plan_id"), "modeling plan ID")
            if plan_id in seen:
                raise ModelingAgentError(f"duplicate modeling plan: {plan_id}")
            if _string(plan.get("role"), "modeling plan role") not in {
                "ModelBuilder",
                "Statistician",
            }:
                raise ModelingAgentError(f"unsupported modeling role: {plan_id}")
            expected = _string(plan.get("expected_status"), "modeling expected status")
            if expected not in allowed:
                raise ModelingAgentError(f"unsupported modeling status: {expected}")
            if not isinstance(plan.get("code"), str) or not plan["code"].strip():
                raise ModelingAgentError(f"modeling plan code is empty: {plan_id}")
            if not isinstance(plan.get("generated_tests"), list) or not plan["generated_tests"]:
                raise ModelingAgentError(f"generated tests are missing: {plan_id}")
            _mapping(plan.get("preregistration"), "modeling preregistration")
            _mapping(plan.get("metric_policy"), "modeling metric policy")
            _mapping(plan.get("split_policy"), "modeling split policy")
            seen.add(plan_id)
            plans.append(dict(plan))
        if not plans:
            raise ModelingAgentError("modeling fixture has no plans")
        return plans

    @staticmethod
    def _preregistered(plan: dict[str, Any]) -> bool:
        value = _mapping(plan["preregistration"], "modeling preregistration")
        required = {
            "primary_metric",
            "direction",
            "minimum_effect",
            "exclusion_rule",
            "frozen_before_run",
        }
        return (
            set(value) == required
            and isinstance(value["primary_metric"], str)
            and value["direction"] in {"minimize", "maximize"}
            and isinstance(value["minimum_effect"], int | float)
            and not isinstance(value["minimum_effect"], bool)
            and isinstance(value["exclusion_rule"], str)
            and value["frozen_before_run"] is True
        )

    @staticmethod
    def _metric_hacking(plan: dict[str, Any]) -> bool:
        value = _mapping(plan["metric_policy"], "modeling metric policy")
        return (
            value.get("select_after_evaluation") is True
            or value.get("metric_source") == "validation_target"
            or value.get("adaptive_tuning") is True
        )

    @staticmethod
    def _split_modification(plan: dict[str, Any]) -> bool:
        value = _mapping(plan["split_policy"], "modeling split policy")
        return value.get("modify_assignments") is True or value.get("allow_resplit") is True

    @staticmethod
    def _heldout_tuning(plan: dict[str, Any]) -> bool:
        value = _mapping(plan["split_policy"], "modeling split policy")
        return value.get("tune_on_validation_targets") is True or value.get("use_test_targets") is True

    @staticmethod
    def _compile(code: str) -> tuple[bool, str]:
        try:
            tree = ast.parse(code, mode="exec")
            compile(tree, "generated_plan.py", "exec")
        except (SyntaxError, ValueError, TypeError) as exc:
            return False, str(exc)
        return True, "compiled"

    @staticmethod
    def _sandbox_run(code: str, root: Path) -> tuple[bool, str]:
        sandbox_root = root / ".tmp"
        sandbox_root.mkdir(parents=True, exist_ok=True)
        sandbox = Path(tempfile.mkdtemp(prefix="bioif-modeling-", dir=sandbox_root))
        try:
            script = sandbox / "generated_plan.py"
            script.write_text(code, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=sandbox,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return completed.returncode == 0, "sandbox_fixture_execution"
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)

    def run(self, *, fixture: bool = True) -> ModelingSummary:
        """Evaluate plans, execute only a valid plan, and preserve split hashes."""
        if not fixture:
            raise ModelingAgentError("--fixture is required for modeling evaluation")
        self._schema_valid()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        plans = self._plans(fixture_data)
        split_path = self.root / "reports/splits/frozen_dev/split_manifest.json"
        split_before = hashlib.sha256(split_path.read_bytes()).hexdigest()
        trace = TraceLedger()
        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        metric_hacking_rejected = 0
        split_modification_rejected = 0
        heldout_tuning_rejected = 0
        tests_generated = 0
        preregistration_complete = True
        sandbox_passed = True
        rows: list[dict[str, Any]] = []
        expected_by_reason = {
            "METRIC_HACKING": "REJECT_METRIC_HACKING",
            "SPLIT_MODIFICATION": "REJECT_SPLIT_MODIFICATION",
            "HELDOUT_TUNING": "REJECT_HELDOUT_TUNING",
        }
        for plan in plans:
            plan_id = _string(plan["plan_id"], "modeling plan ID")
            preregistered = self._preregistered(plan)
            metric_hacking = self._metric_hacking(plan)
            split_modification = self._split_modification(plan)
            heldout_tuning = self._heldout_tuning(plan)
            compiled, compile_reason = self._compile(plan["code"])
            if metric_hacking:
                reason = "METRIC_HACKING"
                status = "REJECTED"
                metric_hacking_rejected += 1
            elif split_modification:
                reason = "SPLIT_MODIFICATION"
                status = "REJECTED"
                split_modification_rejected += 1
            elif heldout_tuning:
                reason = "HELDOUT_TUNING"
                status = "REJECTED"
                heldout_tuning_rejected += 1
            elif not preregistered:
                reason = "INCOMPLETE_PREREGISTRATION"
                status = "REJECTED"
            elif not compiled:
                reason = "PLAN_DOES_NOT_COMPILE"
                status = "REJECTED"
            else:
                reason = "EXECUTABLE_PLAN"
                status = "EXECUTE"
            expected = plan["expected_status"]
            if reason in expected_by_reason and expected != expected_by_reason[reason]:
                raise ModelingAgentError(f"fixture expectation differs: {plan_id}")
            if reason == "EXECUTABLE_PLAN" and expected != "EXECUTE":
                raise ModelingAgentError(f"fixture execute expectation differs: {plan_id}")
            trace.append(
                "model_plan_audited",
                plan_id,
                0,
                {"status": status, "reason": reason, "compiled": compiled},
            )
            tests_generated += len(plan["generated_tests"])
            preregistration_complete = preregistration_complete and preregistered
            row = {
                "plan_id": plan_id,
                "role": plan["role"],
                "model_api": plan["model_api"],
                "status": status,
                "reason": reason,
                "compiled": compiled,
                "compile_reason": compile_reason,
                "generated_tests": plan["generated_tests"],
                "preregistration": plan["preregistration"],
                "split_policy": plan["split_policy"],
                "claim_accepted": False,
            }
            rows.append(row)
            if status == "EXECUTE":
                sandbox_ok, sandbox_reason = self._sandbox_run(plan["code"], self.root)
                sandbox_passed = sandbox_passed and sandbox_ok
                row["sandbox"] = {"passed": sandbox_ok, "reason": sandbox_reason}
                accepted.append(row)
            else:
                rejected.append({**row, "rejection_reason": reason})
        split_after = hashlib.sha256(split_path.read_bytes()).hexdigest()
        splits_unchanged = split_before == split_after
        if not splits_unchanged:
            raise ModelingAgentError("frozen split manifest changed during modeling evaluation")
        trace.validate()
        selected = (
            "modeling_agent"
            if accepted and sandbox_passed and preregistration_complete and splits_unchanged
            else "deterministic_ci_fallback"
        )
        comparison = {
            "schema_version": 1,
            "plans": len(plans),
            "executable_plans": len(accepted),
            "rejected": len(rejected),
            "metric_hacking_rejected": metric_hacking_rejected,
            "split_modification_rejected": split_modification_rejected,
            "heldout_tuning_rejected": heldout_tuning_rejected,
            "tests_generated": tests_generated,
            "preregistration_complete": preregistration_complete,
            "sandbox_passed": sandbox_passed,
            "splits_unchanged": splits_unchanged,
            "selected_pipeline": selected,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "plans": {"schema_version": 1, "plans": rows, "target_values_exposed": False},
            "rejections": {
                "schema_version": 1,
                "rejections": rejected,
                "target_values_exposed": False,
            },
            "comparison": comparison,
            "preregistration": {
                "schema_version": 1,
                "complete": preregistration_complete,
                "plans": [row["plan_id"] for row in accepted],
                "target_values_exposed": False,
            },
            "sandbox": {
                "schema_version": 1,
                "passed": sandbox_passed,
                "executed_plans": [row["plan_id"] for row in accepted],
                "target_values_exposed": False,
            },
            "split_audit": {
                "schema_version": 1,
                "before_sha256": split_before,
                "after_sha256": split_after,
                "unchanged": splits_unchanged,
                "target_values_exposed": False,
            },
            "inputs": {
                "schema_version": 1,
                "sources": list(inputs),
                "target_values_exposed": False,
            },
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        trace_bytes = trace.to_bytes()
        seal = trace.seal()
        resume_key = _sha256(_canonical(raw_payloads) + trace_bytes + _canonical(seal))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "plans": self.output_root / "modeling_plans.json",
            "rejections": self.output_root / "modeling_rejections.json",
            "comparison": self.output_root / "modeling_comparison.json",
            "preregistration": self.output_root / "preregistration.json",
            "sandbox": self.output_root / "sandbox_receipt.json",
            "split_audit": self.output_root / "split_integrity_audit.json",
            "inputs": self.output_root / "input_manifest.json",
            "failures": self.output_root / "failure_ledger.json",
            "trace": self.output_root / "modeling_trace.jsonl",
            "seal": self.output_root / "modeling_trace_seal.json",
            "receipt": self.output_root / "modeling_receipt.json",
            "log": self.output_root / "modeling_log.json",
            "manifest": self.output_root / "modeling_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        payload_bytes["trace"] = trace_bytes
        payload_bytes["seal"] = _canonical(seal)
        artifact_records = {
            name: {
                "path": path.relative_to(self.root).as_posix() if path.is_relative_to(self.root) else path.as_posix(),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "model": "MODEL_BUILDER_STATISTICIAN",
            "status": "VALID",
            "fixture": True,
            "plans": len(plans),
            "executable_plans": len(accepted),
            "rejected": len(rejected),
            "metric_hacking_rejected": metric_hacking_rejected,
            "split_modification_rejected": split_modification_rejected,
            "heldout_tuning_rejected": heldout_tuning_rejected,
            "tests_generated": tests_generated,
            "preregistration_complete": preregistration_complete,
            "sandbox_passed": sandbox_passed,
            "splits_unchanged": splits_unchanged,
            "selected_pipeline": selected,
            "trace_events": len(trace.records),
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        payload_bytes["log"] = _canonical(
            {
                "schema_version": 1,
                "resume_key": resume_key,
                "events": [
                    {"event": "modeling_inputs_verified", "sources": len(inputs)},
                    {"event": "plans_audited", "plans": len(plans)},
                    {"event": "metric_hacking_rejected", "count": metric_hacking_rejected},
                    {"event": "split_modification_rejected", "count": split_modification_rejected},
                    {"event": "heldout_tuning_rejected", "count": heldout_tuning_rejected},
                    {"event": "valid_plan_sandbox_executed", "passed": sandbox_passed},
                    {"event": "split_integrity_verified", "unchanged": splits_unchanged},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "MODEL_BUILDER_STATISTICIAN",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": path.relative_to(self.root).as_posix()
                        if path.is_relative_to(self.root)
                        else path.as_posix(),
                        "sha256": _sha256(payload_bytes[name]),
                        "bytes": len(payload_bytes[name]),
                    }
                    for name, path in paths.items()
                    if name in payload_bytes
                },
            }
        )
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise ModelingAgentError("existing modeling receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise ModelingAgentError(f"existing modeling artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return ModelingSummary(
            plans=len(plans),
            executable_plans=len(accepted),
            rejected=len(rejected),
            metric_hacking_rejected=metric_hacking_rejected,
            split_modification_rejected=split_modification_rejected,
            heldout_tuning_rejected=heldout_tuning_rejected,
            tests_generated=tests_generated,
            preregistration_complete=preregistration_complete,
            sandbox_passed=sandbox_passed,
            splits_unchanged=splits_unchanged,
            selected_pipeline=selected,
            trace_events=len(trace.records),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
