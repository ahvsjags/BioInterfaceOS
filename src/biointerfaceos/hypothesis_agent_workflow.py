"""Offline exploratory Mechanism and hypothesis agent evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.agent_runtime import TraceLedger
from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string
from biointerfaceos.lockbox import LockboxFirewall


class HypothesisAgentError(RuntimeError):
    """Raised when mechanism and hypothesis contracts are invalid."""


@dataclass(frozen=True)
class HypothesisSummary:
    """Summary of one deterministic exploratory hypothesis evaluation."""

    proposals: int
    valid_proposals: int
    rejected: int
    duplicates_rejected: int
    falsifiable: int
    formalized: int
    evidence_linked: int
    schema_valid: bool
    lockbox_clean: bool
    claims_auto_accepted: bool
    selected_pipeline: str
    trace_events: int
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise HypothesisAgentError(f"{label} fields do not match schema")


class HypothesisAgentWorkflow:
    """Generate evidence-linked, falsifiable, exploratory hypotheses only."""

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
            self.root / "tests/fixtures/agents/hypothesis_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/agents/hypothesis"
        self.schema_path = schema_path or self.root / "agents/hypothesis/hypothesis.v1.json"

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "hypothesis schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise HypothesisAgentError(f"cannot load hypothesis schema: {exc}") from exc
        _keys(
            schema,
            {"schema_version", "agent", "proposal_fields", "rejection_reasons"},
            "hypothesis schema",
        )
        if schema.get("schema_version") != 1 or schema.get("agent") != "MechanismHypothesisAgent":
            raise HypothesisAgentError("hypothesis schema version or agent is invalid")
        fields = schema.get("proposal_fields")
        reasons = schema.get("rejection_reasons")
        if (
            not isinstance(fields, list)
            or not fields
            or not all(isinstance(field, str) and field for field in fields)
            or not isinstance(reasons, list)
            or not reasons
            or not all(isinstance(reason, str) and reason for reason in reasons)
        ):
            raise HypothesisAgentError("hypothesis schema fields or reasons are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "hypothesis fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise HypothesisAgentError(f"cannot load hypothesis fixture: {exc}") from exc
        _keys(data, {"schema_version", "mode", "inputs", "candidates"}, "hypothesis fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "hypothesis_fixture":
            raise HypothesisAgentError("hypothesis fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("candidates"), list):
            raise HypothesisAgentError("hypothesis inputs/candidates are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        expected = {
            "T080 agent receipt": (
                self.root / "reports/agents/agent_receipt.json",
                "09750940ab002de284939df873657c6013db25ef21e1d26c243d15046884094f",
            ),
            "T062 mechanism graph": (
                self.root / "reports/omics/modality_links/link_graph.json",
                "8833ff32e4ce55f2d502696119bc64431ecfb987a396fa888d8de20a2e9e6dbe",
            ),
            "T076 model residuals": (
                self.root / "reports/models/m6/m6_results.json",
                "33abc7c2ea291a765f7e54e062a803ba3028871696e78757a39d0d6dc6a09fc8",
            ),
        }
        seen: set[str] = set()
        source_rows: list[dict[str, Any]] = []
        for value in fixture["inputs"]:
            row = _mapping(value, "hypothesis input")
            _keys(row, {"label", "path", "sha256", "split"}, "hypothesis input")
            label = _string(row.get("label"), "hypothesis input label")
            if label not in expected:
                raise HypothesisAgentError(f"unexpected hypothesis input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "hypothesis input path")).resolve(
                strict=True
            )
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise HypothesisAgentError(f"hypothesis input path or checksum differs: {label}")
            if row.get("split") != "train":
                raise HypothesisAgentError(f"hypothesis input is not training-only: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise HypothesisAgentError(f"hypothesis input checksum differs: {label}")
            source_rows.append({"label": label, "path": row["path"], "split": "train"})
            seen.add(label)
        if seen != set(expected):
            raise HypothesisAgentError("hypothesis inputs are incomplete")
        receipt_path = expected["T080 agent receipt"][0]
        receipt = _mapping(json.loads(receipt_path.read_text(encoding="utf-8")), "agent receipt")
        if receipt.get("trace_sealed") is not True:
            raise HypothesisAgentError("T080 agent trace is not sealed")
        graph_path = expected["T062 mechanism graph"][0]
        graph = _mapping(json.loads(graph_path.read_text(encoding="utf-8")), "mechanism graph")
        if graph.get("target_values_exposed", False) is not False:
            raise HypothesisAgentError("mechanism graph exposes target values")
        residual_path = expected["T076 model residuals"][0]
        residuals = _mapping(
            json.loads(residual_path.read_text(encoding="utf-8")), "model residuals"
        )
        train_metrics = _mapping(residuals.get("train_metrics"), "training residual metrics")
        if residuals.get("target_values_exposed") is not False or "rmse" not in train_metrics:
            raise HypothesisAgentError("training residual input is invalid")
        return tuple(source_rows)

    @staticmethod
    def _candidates(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        required = {
            "case_id",
            "normalized_key",
            "mechanism",
            "formalization",
            "evidence_links",
            "falsifiability",
            "split",
            "expected_status",
        }
        candidates: list[dict[str, Any]] = []
        seen: set[str] = set()
        allowed_statuses = {
            "PROPOSE",
            "REJECT_DUPLICATE",
            "REJECT_NOT_FALSIFIABLE",
            "REJECT_UNGROUNDED",
        }
        for value in fixture["candidates"]:
            candidate = _mapping(value, "hypothesis candidate")
            _keys(candidate, required, "hypothesis candidate")
            case_id = _string(candidate.get("case_id"), "hypothesis case ID")
            if case_id in seen:
                raise HypothesisAgentError(f"duplicate hypothesis case: {case_id}")
            expected = _string(candidate.get("expected_status"), "hypothesis expected status")
            if expected not in allowed_statuses:
                raise HypothesisAgentError(f"unsupported hypothesis status: {expected}")
            if not _string(candidate.get("normalized_key"), "hypothesis normalized key"):
                raise HypothesisAgentError(f"hypothesis normalized key is empty: {case_id}")
            if not _string(candidate.get("mechanism"), "hypothesis mechanism"):
                raise HypothesisAgentError(f"hypothesis mechanism is empty: {case_id}")
            if candidate.get("split") != "train":
                raise HypothesisAgentError(f"hypothesis candidate is not training-only: {case_id}")
            _mapping(candidate.get("formalization"), "hypothesis formalization")
            links = candidate.get("evidence_links")
            if not isinstance(links, list):
                raise HypothesisAgentError(f"hypothesis evidence links are invalid: {case_id}")
            falsifiability = _mapping(candidate.get("falsifiability"), "falsifiability")
            _keys(
                falsifiability,
                {"test", "metric", "threshold", "direction"},
                "falsifiability",
            )
            seen.add(case_id)
            candidates.append(dict(candidate))
        if not candidates:
            raise HypothesisAgentError("hypothesis fixture has no candidates")
        return candidates

    @staticmethod
    def _formalized(candidate: dict[str, Any]) -> bool:
        value = _mapping(candidate["formalization"], "hypothesis formalization")
        if set(value) != {"equation", "variables", "direction"}:
            return False
        equation = value.get("equation")
        variables = value.get("variables")
        direction = value.get("direction")
        return (
            isinstance(equation, str)
            and bool(equation.strip())
            and isinstance(variables, list)
            and len(variables) >= 2
            and all(isinstance(item, str) and item for item in variables)
            and direction in {"positive", "negative", "conditional"}
        )

    @staticmethod
    def _evidence_linked(candidate: dict[str, Any]) -> bool:
        links = candidate["evidence_links"]
        if not isinstance(links, list) or not links:
            return False
        for value in links:
            link = _mapping(value, "hypothesis evidence link")
            if set(link) != {"locator", "source", "split", "role"}:
                return False
            locator = link.get("locator")
            if (
                not isinstance(locator, str)
                or not locator.startswith("T")
                or link.get("split") != "train"
                or not isinstance(link.get("source"), str)
                or not isinstance(link.get("role"), str)
            ):
                return False
        return True

    @staticmethod
    def _falsifiable(candidate: dict[str, Any]) -> bool:
        value = _mapping(candidate["falsifiability"], "falsifiability")
        test = value.get("test")
        metric = value.get("metric")
        threshold = value.get("threshold")
        direction = value.get("direction")
        return (
            isinstance(test, str)
            and bool(test.strip())
            and isinstance(metric, str)
            and bool(metric.strip())
            and isinstance(threshold, int | float)
            and not isinstance(threshold, bool)
            and threshold >= 0
            and direction in {"greater_than", "less_than", "outside_interval"}
        )

    def _lockbox_scan(self, paths: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        firewall = LockboxFirewall(self.root)
        report = firewall.scan([self.root / row["path"] for row in paths])
        if not report.clean:
            raise HypothesisAgentError("hypothesis input lockbox contamination detected")
        return {
            "schema_version": 1,
            "clean": True,
            "findings": [],
            "checked_paths": list(report.checked_paths),
            "locked_payload_opened": False,
        }

    def run(self, *, fixture: bool = True) -> HypothesisSummary:
        """Run exploratory proposal generation and deterministic rejection gates."""
        if not fixture:
            raise HypothesisAgentError("--fixture is required for hypothesis evaluation")
        schema_valid = self._schema_valid()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        candidates = self._candidates(fixture_data)
        lockbox_scan = self._lockbox_scan(inputs)
        trace = TraceLedger()
        normalized_seen: set[str] = set()
        proposals: list[dict[str, Any]] = []
        rejections: list[dict[str, Any]] = []
        audit_rows: list[dict[str, Any]] = []
        formalized_count = 0
        evidence_count = 0
        falsifiable_count = 0
        duplicate_count = 0
        for candidate in candidates:
            case_id = _string(candidate["case_id"], "hypothesis case ID")
            key = _string(candidate["normalized_key"], "hypothesis normalized key")
            is_duplicate = key in normalized_seen
            normalized_seen.add(key)
            formalized = self._formalized(candidate)
            evidence_linked = self._evidence_linked(candidate)
            falsifiable = self._falsifiable(candidate)
            formalized_count += formalized
            evidence_count += evidence_linked
            falsifiable_count += falsifiable
            if is_duplicate:
                reason = "DUPLICATE_NORMALIZED_HYPOTHESIS"
                status = "REJECTED"
                duplicate_count += 1
            elif not formalized:
                reason = "NOT_FORMALIZED"
                status = "REJECTED"
            elif not evidence_linked:
                reason = "UNGROUNDED_EVIDENCE"
                status = "REJECTED"
            elif not falsifiable:
                reason = "NOT_FALSIFIABLE"
                status = "REJECTED"
            else:
                reason = "EXPLORATORY_ONLY"
                status = "EXPLORATORY_PROPOSAL"
            expected_status = candidate["expected_status"]
            expected_by_reason = {
                "DUPLICATE_NORMALIZED_HYPOTHESIS": "REJECT_DUPLICATE",
                "NOT_FORMALIZED": "REJECT_NOT_FORMALIZED",
                "UNGROUNDED_EVIDENCE": "REJECT_UNGROUNDED",
                "NOT_FALSIFIABLE": "REJECT_NOT_FALSIFIABLE",
                "EXPLORATORY_ONLY": "PROPOSE",
            }
            if expected_status != expected_by_reason[reason]:
                raise HypothesisAgentError(f"fixture expectation differs: {case_id}")
            trace.append(
                "hypothesis_audited",
                case_id,
                0,
                {"status": status, "reason": reason, "training_only": True},
            )
            row = {
                "case_id": case_id,
                "normalized_key": key,
                "mechanism": candidate["mechanism"],
                "formalization": candidate["formalization"],
                "evidence_links": candidate["evidence_links"],
                "falsifiability": candidate["falsifiability"],
                "status": status,
                "reason": reason,
                "original_candidate_preserved": dict(candidate) == candidate,
                "claim_accepted": False,
                "split": "train",
            }
            audit_rows.append(
                {
                    "case_id": case_id,
                    "status": status,
                    "reason": reason,
                    "duplicate": is_duplicate,
                    "formalized": formalized,
                    "evidence_linked": evidence_linked,
                    "falsifiable": falsifiable,
                }
            )
            if status == "EXPLORATORY_PROPOSAL":
                proposals.append(row)
            else:
                rejections.append({**row, "rejection_reason": reason})
        trace.validate()
        claims_auto_accepted = any(row["claim_accepted"] for row in proposals)
        all_valid = all(
            row["status"] == "EXPLORATORY_PROPOSAL"
            and row["claim_accepted"] is False
            and row["split"] == "train"
            for row in proposals
        )
        selected = (
            "hypothesis_agent"
            if proposals and all_valid and lockbox_scan["clean"]
            else "curated_seed_fallback"
        )
        residual_path = self.root / "reports/models/m6/m6_results.json"
        residuals = _mapping(
            json.loads(residual_path.read_text(encoding="utf-8")), "model residuals"
        )
        train_metrics = _mapping(residuals["train_metrics"], "training residual metrics")
        residual_summary = {
            "schema_version": 1,
            "source": "T076:M6",
            "split": "train",
            "metric": "rmse",
            "train_residual_rmse": train_metrics["rmse"],
            "target_values_exposed": False,
        }
        comparison = {
            "schema_version": 1,
            "proposals": len(candidates),
            "valid_proposals": len(proposals),
            "rejected": len(rejections),
            "duplicates_rejected": duplicate_count,
            "falsifiable": falsifiable_count,
            "formalized": formalized_count,
            "evidence_linked": evidence_count,
            "all_valid_nonduplicate": all_valid,
            "all_valid_falsifiable": all_valid,
            "all_valid_formalized": all_valid,
            "all_valid_evidence_linked": all_valid,
            "lockbox_clean": lockbox_scan["clean"],
            "claims_auto_accepted": claims_auto_accepted,
            "selected_pipeline": selected,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "proposals": {
                "schema_version": 1,
                "status": "VALID",
                "proposals": proposals,
                "target_values_exposed": False,
            },
            "rejections": {
                "schema_version": 1,
                "status": "VALID",
                "rejections": rejections,
                "target_values_exposed": False,
            },
            "falsifiability": {
                "schema_version": 1,
                "audits": audit_rows,
                "passed": falsifiable_count,
                "target_values_exposed": False,
            },
            "provenance": {
                "schema_version": 1,
                "training_only": True,
                "inputs": list(inputs),
                "target_values_exposed": False,
            },
            "lockbox": lockbox_scan,
            "residuals": residual_summary,
            "comparison": comparison,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        trace_bytes = trace.to_bytes()
        seal = trace.seal()
        resume_key = _sha256(_canonical(raw_payloads) + trace_bytes + _canonical(seal))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "proposals": self.output_root / "hypothesis_proposals.json",
            "rejections": self.output_root / "hypothesis_rejections.json",
            "falsifiability": self.output_root / "falsifiability_audit.json",
            "provenance": self.output_root / "provenance_audit.json",
            "lockbox": self.output_root / "lockbox_scan.json",
            "residuals": self.output_root / "residual_summary.json",
            "comparison": self.output_root / "hypothesis_comparison.json",
            "failures": self.output_root / "failure_ledger.json",
            "trace": self.output_root / "hypothesis_trace.jsonl",
            "seal": self.output_root / "hypothesis_trace_seal.json",
            "receipt": self.output_root / "hypothesis_receipt.json",
            "log": self.output_root / "hypothesis_log.json",
            "manifest": self.output_root / "hypothesis_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        payload_bytes["trace"] = trace_bytes
        payload_bytes["seal"] = _canonical(seal)
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root))
                if path.is_relative_to(self.root)
                else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "model": "MECHANISM_HYPOTHESIS_AGENT",
            "status": "VALID",
            "fixture": True,
            "proposals": len(candidates),
            "valid_proposals": len(proposals),
            "rejected": len(rejections),
            "duplicates_rejected": duplicate_count,
            "falsifiable": falsifiable_count,
            "formalized": formalized_count,
            "evidence_linked": evidence_count,
            "schema_valid": schema_valid,
            "lockbox_clean": lockbox_scan["clean"],
            "claims_auto_accepted": claims_auto_accepted,
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
                    {"event": "training_inputs_verified", "sources": len(inputs)},
                    {"event": "residual_summary_loaded", "split": "train"},
                    {"event": "hypotheses_audited", "proposals": len(candidates)},
                    {
                        "event": "unsupported_or_duplicate_candidates_rejected",
                        "count": len(rejections),
                    },
                    {
                        "event": "automatic_claim_acceptance_blocked",
                        "passed": not claims_auto_accepted,
                    },
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "MECHANISM_HYPOTHESIS_AGENT",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": str(path.relative_to(self.root))
                        if path.is_relative_to(self.root)
                        else str(path),
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
                raise HypothesisAgentError("existing hypothesis receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise HypothesisAgentError(f"existing hypothesis artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return HypothesisSummary(
            proposals=len(candidates),
            valid_proposals=len(proposals),
            rejected=len(rejections),
            duplicates_rejected=duplicate_count,
            falsifiable=falsifiable_count,
            formalized=formalized_count,
            evidence_linked=evidence_count,
            schema_valid=schema_valid,
            lockbox_clean=lockbox_scan["clean"],
            claims_auto_accepted=claims_auto_accepted,
            selected_pipeline=selected,
            trace_events=len(trace.records),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
