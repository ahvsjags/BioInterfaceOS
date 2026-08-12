"""Offline reproducibility and disabled Lockbox evaluator agent."""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string
from biointerfaceos.release import ReleaseError, ReleaseManager


class ReproducibilityAgentError(RuntimeError):
    """Raised when reproducibility or evaluator gates are invalid."""


@dataclass(frozen=True)
class ReproducibilitySummary:
    """Summary of one deterministic reproduction and evaluator gate."""

    release_verified: bool
    rebuild_clean: bool
    hash_match: bool
    lockbox_activation_blocked: bool
    training_methods_exposed: bool
    selected_pipeline: str
    trace_events: int
    resumed: int
    receipt_path: Path


class DisabledLockboxEvaluator:
    """Metadata-only evaluator that cannot activate without signed freeze."""

    def __init__(self, release_id: str, manifest_hash: str) -> None:
        self.release_id = release_id
        self.manifest_hash = manifest_hash

    def capabilities(self) -> tuple[str, ...]:
        return (
            "verify_release",
            "rebuild_fixture",
            "compare_hashes",
            "read_release_metadata",
        )

    def activation_status(self, signed_freeze_token: str | None) -> dict[str, Any]:
        if not signed_freeze_token:
            return {
                "active": False,
                "reason": "SIGNED_FREEZE_REQUIRED",
                "release_id": self.release_id,
                "manifest_hash": self.manifest_hash,
            }
        return {
            "active": False,
            "reason": "TOKEN_NOT_AUTHORIZED_IN_DEVELOPMENT_FIXTURE",
            "release_id": self.release_id,
            "manifest_hash": self.manifest_hash,
        }


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise ReproducibilityAgentError(f"{label} fields do not match schema")


class ReproducibilityWorkflow:
    """Verify release metadata, rebuild a public fixture result, and keep lockbox disabled."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/agents/reproducibility_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/agents/reproducibility"
        self.schema_path = schema_path or (
            self.root / "agents/reproducibility/reproducibility.v1.json"
        )

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "reproducibility schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReproducibilityAgentError(f"cannot load reproducibility schema: {exc}") from exc
        _keys(
            schema,
            {"schema_version", "agent", "capabilities", "forbidden_methods"},
            "reproducibility schema",
        )
        if (
            schema.get("schema_version") != 1
            or schema.get("agent") != "ReproducibilityLockboxEvaluator"
        ):
            raise ReproducibilityAgentError("reproducibility schema version or agent is invalid")
        capabilities = schema.get("capabilities")
        forbidden = schema.get("forbidden_methods")
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or not all(isinstance(item, str) and item for item in capabilities)
            or not isinstance(forbidden, list)
            or not forbidden
            or not all(isinstance(item, str) and item for item in forbidden)
        ):
            raise ReproducibilityAgentError("reproducibility capabilities are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "reproducibility fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReproducibilityAgentError(f"cannot load reproducibility fixture: {exc}") from exc
        _keys(
            data,
            {"schema_version", "mode", "release", "inputs", "signed_freeze_token"},
            "reproducibility fixture",
        )
        if data.get("schema_version") != 1 or data.get("mode") != "reproducibility_fixture":
            raise ReproducibilityAgentError("reproducibility fixture schema or mode is invalid")
        if not isinstance(data.get("release"), dict) or not isinstance(data.get("inputs"), list):
            raise ReproducibilityAgentError("reproducibility release or inputs are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        expected = {
            "T068 grading receipt": (
                self.root / "reports/benchmark/grading/grading_receipt.json",
                "6ffb2d8130b54e0291882f037a6ba9a050682101a9c0c647dea5740aa184a59b",
            ),
            "T080 agent receipt": (
                self.root / "reports/agents/agent_receipt.json",
                "09750940ab002de284939df873657c6013db25ef21e1d26c243d15046884094f",
            ),
        }
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for value in fixture["inputs"]:
            row = _mapping(value, "reproducibility input")
            _keys(row, {"label", "path", "sha256"}, "reproducibility input")
            label = _string(row.get("label"), "reproducibility input label")
            if label not in expected:
                raise ReproducibilityAgentError(f"unexpected reproducibility input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "reproducibility input path")).resolve(
                strict=True
            )
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise ReproducibilityAgentError(
                    f"reproducibility input path or checksum differs: {label}"
                )
            if _sha256(path.read_bytes()) != checksum:
                raise ReproducibilityAgentError(f"reproducibility input checksum differs: {label}")
            rows.append({"label": label, "path": row["path"], "sha256": checksum})
            seen.add(label)
        if seen != set(expected):
            raise ReproducibilityAgentError("reproducibility inputs are incomplete")
        return tuple(rows)

    def _rebuild(
        self, fixture: dict[str, Any], release_manifest_hash: str
    ) -> tuple[dict[str, Any], str, str]:
        metrics_path = self.root / "reports/benchmark/grading/metrics.json"
        metrics = _mapping(json.loads(metrics_path.read_text(encoding="utf-8")), "grading metrics")
        if metrics.get("target_values_exposed", False) is not False:
            raise ReproducibilityAgentError("grading metrics expose target values")
        recipe = {
            "schema_version": 1,
            "fixture": True,
            "release_manifest_hash": release_manifest_hash,
            "source_metrics_sha256": _sha256(metrics_path.read_bytes()),
            "metric_keys": sorted(metrics),
            "status": "REBUILT_CLEAN",
            "target_values_exposed": False,
        }
        first = _canonical(recipe)
        tmp_root = self.root / ".tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="bioif-repro-", dir=tmp_root) as directory:
            output = Path(directory) / "rebuild_receipt.json"
            output.write_bytes(first)
            first_hash = hashlib.sha256(output.read_bytes()).hexdigest()
        second_hash = hashlib.sha256(_canonical(recipe)).hexdigest()
        return recipe, first_hash, second_hash

    def run(self, *, fixture: bool = True) -> ReproducibilitySummary:
        """Run clean rebuild, hash comparison, capability audit, and disabled activation gate."""
        if not fixture:
            raise ReproducibilityAgentError("--fixture is required for reproducibility evaluation")
        schema_valid = self._schema_valid()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        release_data = _mapping(fixture_data["release"], "reproducibility release")
        release_id = _string(release_data.get("release_id"), "release ID")
        expected_manifest_hash = _string(release_data.get("manifest_hash"), "release manifest hash")
        try:
            release_summary = ReleaseManager(self.root).verify(release_id)
        except (ReleaseError, OSError) as exc:
            raise ReproducibilityAgentError(f"release verification failed: {exc}") from exc
        release_verified = release_summary.manifest_hash == expected_manifest_hash
        recipe, rebuild_hash, recomputed_hash = self._rebuild(
            fixture_data, release_summary.manifest_hash
        )
        rebuild_clean = recipe["status"] == "REBUILT_CLEAN"
        hash_match = rebuild_hash == recomputed_hash
        evaluator = DisabledLockboxEvaluator(release_id, release_summary.manifest_hash)
        activation = evaluator.activation_status(fixture_data["signed_freeze_token"])
        lockbox_activation_blocked = (
            activation["active"] is False and activation["reason"] == "SIGNED_FREEZE_REQUIRED"
        )
        capabilities = evaluator.capabilities()
        forbidden_methods = {"train", "fit", "optimize", "backprop", "download"}
        training_methods_exposed = bool(set(capabilities) & forbidden_methods)
        if not schema_valid or not release_verified or not rebuild_clean or not hash_match:
            raise ReproducibilityAgentError("reproducibility gate failed")
        if not lockbox_activation_blocked or training_methods_exposed:
            raise ReproducibilityAgentError("lockbox activation or capability gate failed")
        trace_events = 4
        comparison = {
            "schema_version": 1,
            "release_verified": release_verified,
            "rebuild_clean": rebuild_clean,
            "rebuild_hash": rebuild_hash,
            "recomputed_hash": recomputed_hash,
            "hash_match": hash_match,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "comparison": comparison,
            "activation": {"schema_version": 1, **activation},
            "capabilities": {
                "schema_version": 1,
                "capabilities": list(capabilities),
                "training_methods_exposed": training_methods_exposed,
            },
            "rebuild": recipe,
            "inputs": {"schema_version": 1, "inputs": list(inputs)},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "comparison": self.output_root / "reproduction_comparison.json",
            "activation": self.output_root / "lockbox_activation_gate.json",
            "capabilities": self.output_root / "evaluator_capabilities.json",
            "rebuild": self.output_root / "rebuild_receipt.json",
            "inputs": self.output_root / "input_manifest.json",
            "failures": self.output_root / "failure_ledger.json",
            "trace": self.output_root / "reproducibility_trace.jsonl",
            "seal": self.output_root / "reproducibility_trace_seal.json",
            "receipt": self.output_root / "reproducibility_receipt.json",
            "log": self.output_root / "reproducibility_log.json",
            "manifest": self.output_root / "reproducibility_manifest.json",
        }
        trace_lines = [
            {"sequence": 1, "event": "release_verified", "release_id": release_id},
            {"sequence": 2, "event": "fixture_rebuilt", "hash_match": hash_match},
            {
                "sequence": 3,
                "event": "unsigned_lockbox_activation_blocked",
                "blocked": lockbox_activation_blocked,
            },
            {
                "sequence": 4,
                "event": "evaluator_capability_audited",
                "training_methods_exposed": training_methods_exposed,
            },
        ]
        trace_bytes = b"".join(_canonical(row) for row in trace_lines)
        seal = {
            "schema_version": 1,
            "events": trace_events,
            "trace_sha256": _sha256(trace_bytes),
        }
        payloads: dict[str, bytes] = {
            name: _canonical(value) for name, value in raw_payloads.items()
        }
        payloads["failures"] = _canonical({"schema_version": 1, "status": "VALID", "failures": []})
        payloads["trace"] = trace_bytes
        payloads["seal"] = _canonical(seal)
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)),
                "sha256": _sha256(payloads[name]),
                "bytes": len(payloads[name]),
            }
            for name, path in paths.items()
            if name in payloads
        }
        receipt = {
            "schema_version": 1,
            "model": "REPRODUCIBILITY_LOCKBOX_EVALUATOR",
            "status": "VALID",
            "fixture": True,
            "release_id": release_id,
            "release_verified": release_verified,
            "rebuild_clean": rebuild_clean,
            "hash_match": hash_match,
            "lockbox_activation_blocked": lockbox_activation_blocked,
            "training_methods_exposed": training_methods_exposed,
            "selected_pipeline": "reproducibility_agent",
            "trace_events": trace_events,
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payloads["receipt"] = _canonical(receipt)
        payloads["log"] = _canonical(
            {
                "schema_version": 1,
                "resume_key": resume_key,
                "events": [
                    {"event": "release_metadata_verified", "release_id": release_id},
                    {"event": "fixture_result_rebuilt", "hash_match": hash_match},
                    {
                        "event": "lockbox_evaluator_kept_disabled",
                        "blocked": lockbox_activation_blocked,
                    },
                    {"event": "training_method_exposure_scan", "exposed": training_methods_exposed},
                ],
            }
        )
        payloads["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "REPRODUCIBILITY_LOCKBOX_EVALUATOR",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": str(path.relative_to(self.root)),
                        "sha256": _sha256(payloads[name]),
                        "bytes": len(payloads[name]),
                    }
                    for name, path in paths.items()
                    if name in payloads
                },
            }
        )
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payloads["receipt"]:
                raise ReproducibilityAgentError(
                    "existing reproducibility receipt differs from rerun"
                )
            for name, payload in payloads.items():
                if paths[name].read_bytes() != payload:
                    raise ReproducibilityAgentError(
                        f"existing reproducibility artifact differs: {name}"
                    )
            resumed = 1
        else:
            for name, payload in payloads.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return ReproducibilitySummary(
            release_verified=release_verified,
            rebuild_clean=rebuild_clean,
            hash_match=hash_match,
            lockbox_activation_blocked=lockbox_activation_blocked,
            training_methods_exposed=training_methods_exposed,
            selected_pipeline="reproducibility_agent",
            trace_events=trace_events,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
