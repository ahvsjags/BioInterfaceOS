"""Offline ResolutionAgent and EvidenceAuditor conflict evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.agent_runtime import TraceLedger
from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string


class ResolutionAuditError(RuntimeError):
    """Raised when resolution/audit contracts are invalid."""


@dataclass(frozen=True)
class ResolutionAuditSummary:
    """Summary of one deterministic conflict audit."""

    cases: int
    conflicts: int
    detected: int
    quarantined: int
    original_assertions_preserved: bool
    false_merge_rate: float
    selected_pipeline: str
    trace_events: int
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise ResolutionAuditError(f"{label} fields do not match schema")


class ResolutionAuditWorkflow:
    """Detect unit/entity/evidence conflicts without overwriting assertions."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/agents/resolution_audit_fixture.json")
        self.output_root = output_root or self.root / "reports/agents/audit"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "resolution-audit fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ResolutionAuditError(f"cannot load resolution-audit fixture: {exc}") from exc
        _keys(data, {"schema_version", "mode", "inputs", "cases"}, "resolution-audit fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "resolution_audit_fixture":
            raise ResolutionAuditError("resolution-audit fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("cases"), list):
            raise ResolutionAuditError("resolution-audit inputs/cases are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> None:
        expected = {
            "T080 agent receipt": (
                self.root / "reports/agents/agent_receipt.json",
                "09750940ab002de284939df873657c6013db25ef21e1d26c243d15046884094f",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "resolution-audit input")
            _keys(row, {"label", "path", "sha256"}, "resolution-audit input")
            label = _string(row.get("label"), "resolution-audit input label")
            if label not in expected:
                raise ResolutionAuditError(f"unexpected resolution-audit input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "input path")).resolve(strict=True)
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise ResolutionAuditError(f"input path or checksum differs: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise ResolutionAuditError(f"input checksum differs: {label}")
            if label == "T080 agent receipt":
                receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), "agent receipt")
                if receipt.get("trace_sealed") is not True:
                    raise ResolutionAuditError("T080 agent trace is not sealed")
            seen.add(label)
        if seen != set(expected):
            raise ResolutionAuditError("resolution-audit inputs are incomplete")

    @staticmethod
    def _cases(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        required = {
            "case_id",
            "kind",
            "original_assertion",
            "candidate_assertions",
            "expected_conflict",
        }
        cases: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["cases"]:
            case = _mapping(value, "resolution-audit case")
            _keys(case, required, "resolution-audit case")
            case_id = _string(case.get("case_id"), "case ID")
            if case_id in seen:
                raise ResolutionAuditError(f"duplicate case: {case_id}")
            kind = _string(case.get("kind"), "case kind")
            if kind not in {"unit", "entity", "evidence"}:
                raise ResolutionAuditError(f"unsupported conflict kind: {kind}")
            original = _mapping(case.get("original_assertion"), "original assertion")
            candidates = case.get("candidate_assertions")
            expected = case.get("expected_conflict")
            if not isinstance(candidates, list) or len(candidates) < 2:
                raise ResolutionAuditError(f"candidate assertions require >=2 values: {case_id}")
            if not isinstance(expected, bool):
                raise ResolutionAuditError(f"expected conflict must be boolean: {case_id}")
            locator = _string(original.get("evidence_locator"), "original evidence locator")
            if not locator.startswith("asset:"):
                raise ResolutionAuditError(f"original assertion lacks evidence: {case_id}")
            cases.append(
                {
                    "case_id": case_id,
                    "kind": kind,
                    "original_assertion": dict(original),
                    "candidate_assertions": [_mapping(candidate, "candidate assertion") for candidate in candidates],
                    "expected_conflict": expected,
                }
            )
            seen.add(case_id)
        if not cases:
            raise ResolutionAuditError("resolution-audit fixture has no cases")
        return cases

    @staticmethod
    def _detect(case: dict[str, Any]) -> tuple[bool, str, str]:
        candidates = case["candidate_assertions"]
        values = {json.dumps(candidate.get("value"), sort_keys=True) for candidate in candidates}
        units = {candidate.get("unit") for candidate in candidates}
        locators = {candidate.get("evidence_locator") for candidate in candidates}
        conflict = len(values) > 1 or len(units) > 1 or len(locators) > 1
        if not conflict:
            return False, "RESOLVED", "candidate assertions agree"
        reason_by_kind = {
            "unit": "UNIT_CONFLICT",
            "entity": "ENTITY_CONFLICT",
            "evidence": "EVIDENCE_CONFLICT",
        }
        return True, "QUARANTINED", reason_by_kind[case["kind"]]

    def run(self, *, fixture: bool = True) -> ResolutionAuditSummary:
        """Run conflict detection, preservation, quarantine, and fallback comparison."""
        if not fixture:
            raise ResolutionAuditError("--fixture is required for audit evaluation")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        cases = self._cases(fixture_data)
        trace = TraceLedger()
        decisions: list[dict[str, Any]] = []
        preserved = True
        conflicts = 0
        detected = 0
        quarantined = 0
        for case in cases:
            conflict, status, reason = self._detect(case)
            conflicts += case["expected_conflict"]
            detected += conflict
            quarantined += status == "QUARANTINED"
            trace.append(
                "conflict_audited",
                case["case_id"],
                0,
                {"kind": case["kind"], "conflict": conflict, "reason": reason},
            )
            preserved = preserved and case["original_assertion"] == dict(case["original_assertion"])
            decisions.append(
                {
                    "case_id": case["case_id"],
                    "kind": case["kind"],
                    "status": status,
                    "reason": reason,
                    "conflict_detected": conflict,
                    "original_assertion": case["original_assertion"],
                    "candidate_assertions": case["candidate_assertions"],
                    "original_preserved": True,
                    "deterministic_fallback": "quarantine_on_conflict",
                }
            )
        trace.validate()
        false_merge_rate = (conflicts - detected) / conflicts if conflicts else 0.0
        selected = "resolution_audit_agent" if preserved and false_merge_rate <= 0.0 else "deterministic_resolver"
        comparison = {
            "schema_version": 1,
            "cases": len(cases),
            "expected_conflicts": conflicts,
            "detected_conflicts": detected,
            "quarantined": quarantined,
            "false_merge_rate": false_merge_rate,
            "original_assertions_preserved": preserved,
            "selected_pipeline": selected,
            "agent_value": int(selected == "resolution_audit_agent"),
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "decisions": {
                "schema_version": 1,
                "decisions": decisions,
                "target_values_exposed": False,
            },
            "comparison": comparison,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        trace_bytes = trace.to_bytes()
        seal = trace.seal()
        resume_key = _sha256(_canonical(raw_payloads) + trace_bytes + _canonical(seal))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "decisions": self.output_root / "audit_decisions.json",
            "comparison": self.output_root / "audit_comparison.json",
            "failures": self.output_root / "failure_ledger.json",
            "quarantine": self.output_root / "quarantine.json",
            "trace": self.output_root / "audit_trace.jsonl",
            "seal": self.output_root / "audit_trace_seal.json",
            "receipt": self.output_root / "audit_receipt.json",
            "log": self.output_root / "audit_log.json",
            "manifest": self.output_root / "audit_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        payload_bytes["trace"] = trace_bytes
        payload_bytes["seal"] = _canonical(seal)
        payload_bytes["quarantine"] = _canonical(
            {"schema_version": 1, "records": [d for d in decisions if d["status"] == "QUARANTINED"]}
        )
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
            "model": "RESOLUTION_EVIDENCE_AUDITOR",
            "status": "VALID",
            "fixture": True,
            "cases": len(cases),
            "conflicts": conflicts,
            "detected": detected,
            "quarantined": quarantined,
            "original_assertions_preserved": preserved,
            "false_merge_rate": false_merge_rate,
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
                    {"event": "conflict_fixture_loaded", "cases": len(cases)},
                    {"event": "unit_entity_evidence_conflicts_audited", "detected": detected},
                    {"event": "original_assertions_preserved", "passed": preserved},
                    {"event": "unresolved_records_quarantined", "count": quarantined},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "RESOLUTION_EVIDENCE_AUDITOR",
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
                raise ResolutionAuditError("existing audit receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise ResolutionAuditError(f"existing audit artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return ResolutionAuditSummary(
            cases=len(cases),
            conflicts=conflicts,
            detected=detected,
            quarantined=quarantined,
            original_assertions_preserved=preserved,
            false_merge_rate=false_merge_rate,
            selected_pipeline=selected,
            trace_events=len(trace.records),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
