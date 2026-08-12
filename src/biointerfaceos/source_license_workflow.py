"""Offline SourceScout and LicenseGate evaluation over policy-backed fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string
from biointerfaceos.policy import (
    CANDIDATE_FIELDS,
    PolicyDecision,
    RejectionRecord,
    RejectionRegistry,
    SourceCandidate,
    SourcePolicyEngine,
)


class SourceLicenseError(RuntimeError):
    """Raised when the SourceScout/LicenseGate contract is invalid."""


@dataclass(frozen=True)
class SourceLicenseSummary:
    """Summary of one deterministic source-license evaluation."""

    cases: int
    recovered: int
    rejected_or_quarantined: int
    evidence_complete: bool
    no_credentials_requested: bool
    agent_value: int
    resumed: int
    receipt_path: Path


class SourceLicenseWorkflow:
    """Recover public metadata and apply the existing default-deny policy offline."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/agents/source_license_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/agents/source_license"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "source-license fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SourceLicenseError(f"cannot load source-license fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "source_license_fixture":
            raise SourceLicenseError("source-license fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("cases"), list):
            raise SourceLicenseError("source-license inputs/cases are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> None:
        expected_path = self.root / "reports/agents/agent_receipt.json"
        expected_hash = "09750940ab002de284939df873657c6013db25ef21e1d26c243d15046884094f"
        seen = False
        for value in fixture["inputs"]:
            row = _mapping(value, "source-license input")
            _strict = {"label", "path", "sha256"}
            if set(row) != _strict:
                raise SourceLicenseError("source-license input fields do not match schema")
            if _string(row.get("label"), "source-license input label") != "T080 agent receipt":
                raise SourceLicenseError("unexpected source-license input")
            path = (self.root / _string(row.get("path"), "source-license input path")).resolve(
                strict=True
            )
            if path != expected_path.resolve(strict=True) or row.get("sha256") != expected_hash:
                raise SourceLicenseError("T080 agent receipt path or checksum differs")
            if _sha256(path.read_bytes()) != expected_hash:
                raise SourceLicenseError("T080 agent receipt checksum differs")
            receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), "agent receipt")
            if receipt.get("status") != "VALID" or receipt.get("trace_sealed") is not True:
                raise SourceLicenseError("T080 agent receipt is not valid and sealed")
            seen = True
        if not seen:
            raise SourceLicenseError("T080 agent receipt input is missing")

    @staticmethod
    def _cases(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        seen: set[str] = set()
        required = {"case_id", "query", "candidate", "expected_decision", "expected_code"}
        for value in fixture["cases"]:
            case = _mapping(value, "source-license case")
            if set(case) != required:
                raise SourceLicenseError("source-license case fields do not match schema")
            case_id = _string(case.get("case_id"), "source-license case ID")
            if case_id in seen:
                raise SourceLicenseError(f"duplicate source-license case: {case_id}")
            candidate = _mapping(case.get("candidate"), "source-license candidate")
            if set(candidate) != set(CANDIDATE_FIELDS):
                raise SourceLicenseError(f"candidate fields mismatch: {case_id}")
            if not _string(candidate.get("evidence_location"), "candidate evidence location"):
                raise SourceLicenseError(f"candidate evidence is missing: {case_id}")
            expected_decision = _string(case.get("expected_decision"), "expected decision")
            expected_code = case.get("expected_code")
            if not isinstance(expected_code, str):
                raise SourceLicenseError(f"expected rejection code is not a string: {case_id}")
            cases.append(
                {
                    "case_id": case_id,
                    "query": _string(case.get("query"), "source-license query"),
                    "candidate": candidate,
                    "expected_decision": expected_decision,
                    "expected_code": expected_code,
                }
            )
            seen.add(case_id)
        if not cases:
            raise SourceLicenseError("source-license fixture has no cases")
        return cases

    @staticmethod
    def _scout(case: dict[str, Any]) -> dict[str, Any]:
        candidate = case["candidate"]
        url = str(candidate["url"])
        credentials_requested = any(
            bool(candidate[field])
            for field in (
                "registration_required",
                "login_required",
                "api_key_required",
                "application_required",
                "approval_required",
                "institution_required",
                "data_use_agreement_required",
                "paid_required",
            )
        )
        return {
            "case_id": case["case_id"],
            "query": case["query"],
            "source_id": candidate["source_id"],
            "recovered": url.startswith("https://") and not credentials_requested,
            "metadata_only": True,
            "credentials_requested": False,
            "evidence_location": candidate["evidence_location"],
        }

    @staticmethod
    def _record(
        candidate: SourceCandidate, decision: PolicyDecision, checked_at: str
    ) -> RejectionRecord:
        return RejectionRecord(
            source_id=candidate.source_id,
            source_name=candidate.source_name,
            url=candidate.url,
            accession=candidate.accession,
            decision=decision.decision,
            rejection_code=decision.rejection_code or "",
            reason=decision.reason,
            evidence_location=decision.evidence_location,
            license_identifier=candidate.license_identifier,
            license_text=candidate.license_text,
            checked_at=checked_at,
        )

    def run(self, *, fixture: bool = True) -> SourceLicenseSummary:
        """Run SourceScout and LicenseGate without network or credential lookup."""
        if not fixture:
            raise SourceLicenseError("--fixture is required for source-license evaluation")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        cases = self._cases(fixture_data)
        engine = SourcePolicyEngine.from_yaml(self.root)
        scout_results: list[dict[str, Any]] = []
        gate_results: list[dict[str, Any]] = []
        rejection_records: list[RejectionRecord] = []
        recovered = 0
        rejected_or_quarantined = 0
        evidence_complete = True
        no_credentials_requested = True
        for case in cases:
            scout = self._scout(case)
            candidate = SourceCandidate.from_mapping(case["candidate"])
            decision = engine.evaluate(candidate)
            if (
                decision.decision != case["expected_decision"]
                or (decision.rejection_code or "") != case["expected_code"]
            ):
                raise SourceLicenseError(
                    f"case mismatch {case['case_id']}: "
                    f"{decision.decision}/{decision.rejection_code}"
                )
            if decision.decision.startswith("ADMIT"):
                recovered += 1
            else:
                rejected_or_quarantined += 1
                rejection_records.append(
                    self._record(candidate, decision, "2026-08-12T00:00:00+00:00")
                )
            evidence_complete = evidence_complete and bool(decision.evidence_location)
            no_credentials_requested = (
                no_credentials_requested and not scout["credentials_requested"]
            )
            scout_results.append(scout)
            gate_results.append(
                {
                    "case_id": case["case_id"],
                    "source_id": decision.source_id,
                    "decision": decision.decision,
                    "rejection_code": decision.rejection_code or "",
                    "reason": decision.reason,
                    "evidence_location": decision.evidence_location,
                    "normalized_license": decision.normalized_license,
                }
            )
        self.output_root.mkdir(parents=True, exist_ok=True)
        registry = RejectionRegistry(self.output_root, "rejected_sources.parquet")
        registry.write(rejection_records)
        rejection_rows = registry.validate()
        agent_value = 0
        audit = {
            "schema_version": 1,
            "cases": len(cases),
            "recovered": recovered,
            "rejected_or_quarantined": rejected_or_quarantined,
            "evidence_complete": evidence_complete,
            "no_credentials_requested": no_credentials_requested,
            "rejection_registry_rows": rejection_rows,
            "agent_value": agent_value,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "scout": {
                "schema_version": 1,
                "decisions": scout_results,
                "target_values_exposed": False,
            },
            "gate": {
                "schema_version": 1,
                "decisions": gate_results,
                "target_values_exposed": False,
            },
            "audit": audit,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads) + registry.path.read_bytes())
        paths = {
            "scout": self.output_root / "source_scout.json",
            "gate": self.output_root / "license_gate.json",
            "audit": self.output_root / "source_license_audit.json",
            "failures": self.output_root / "failure_ledger.json",
            "registry": registry.path,
            "receipt": self.output_root / "source_license_receipt.json",
            "log": self.output_root / "source_license_log.json",
            "manifest": self.output_root / "source_license_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        payload_bytes["registry"] = registry.path.read_bytes()
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
            "model": "SOURCE_SCOUT_LICENSE_GATE",
            "status": "VALID",
            "fixture": True,
            "cases": len(cases),
            "recovered": recovered,
            "rejected_or_quarantined": rejected_or_quarantined,
            "evidence_complete": evidence_complete,
            "no_credentials_requested": no_credentials_requested,
            "agent_value": agent_value,
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
                    {"event": "T080_runtime_receipt_verified", "cases": len(cases)},
                    {"event": "sourcescout_metadata_recovered", "recovered": recovered},
                    {
                        "event": "licensegate_policy_evaluated",
                        "rejected_or_quarantined": rejected_or_quarantined,
                    },
                    {"event": "evidence_locations_audited", "complete": evidence_complete},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "SOURCE_SCOUT_LICENSE_GATE",
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
                raise SourceLicenseError("existing source-license receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise SourceLicenseError(f"existing source-license artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return SourceLicenseSummary(
            cases=len(cases),
            recovered=recovered,
            rejected_or_quarantined=rejected_or_quarantined,
            evidence_complete=evidence_complete,
            no_credentials_requested=no_credentials_requested,
            agent_value=agent_value,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
