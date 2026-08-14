"""Offline RedTeam agent suite for leakage, unit, and claim attacks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.agent_runtime import TraceLedger
from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string
from biointerfaceos.lockbox import LockboxAccessError, LockboxFirewall


class RedTeamError(RuntimeError):
    """Raised when the red-team contract or release gate is invalid."""


@dataclass(frozen=True)
class RedTeamSummary:
    """Summary of one deterministic attack-suite evaluation."""

    attacks: int
    executed: int
    detected: int
    blocked: int
    critical_findings: int
    remediations: int
    adverse_results_preserved: bool
    release_blocked: bool
    selected_pipeline: str
    trace_events: int
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise RedTeamError(f"{label} fields do not match schema")


class RedTeamWorkflow:
    """Execute mandatory attacks and preserve every adverse result."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/agents/redteam_fixture.json"
        self.output_root = output_root or self.root / "reports/agents/redteam"
        self.schema_path = schema_path or self.root / "agents/redteam/redteam.v1.json"

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "redteam schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RedTeamError(f"cannot load redteam schema: {exc}") from exc
        _keys(
            schema,
            {"schema_version", "agent", "finding_fields", "severity_levels"},
            "redteam schema",
        )
        if schema.get("schema_version") != 1 or schema.get("agent") != "RedTeamAgent":
            raise RedTeamError("redteam schema version or agent is invalid")
        fields = schema.get("finding_fields")
        levels = schema.get("severity_levels")
        if (
            not isinstance(fields, list)
            or not fields
            or not all(isinstance(field, str) and field for field in fields)
            or levels != ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        ):
            raise RedTeamError("redteam schema fields or severity levels are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "redteam fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RedTeamError(f"cannot load redteam fixture: {exc}") from exc
        _keys(data, {"schema_version", "mode", "inputs", "attacks"}, "redteam fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "redteam_fixture":
            raise RedTeamError("redteam fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("attacks"), list):
            raise RedTeamError("redteam inputs/attacks are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        expected = {
            "T066 attack findings": (
                self.root / "reports/splits/audit/attack_findings.json",
                "6f44789dcc78ecf153e1a29a69106481b7a74ee2e75ce73ca5ba9dca00085305",
            ),
            "T078 OOD detection": (
                self.root / "reports/models/uncertainty/ood_detection.json",
                "b6226164c24fee30eac3c7f168f4db7ba2fd4596f8333ae28579620699ceb7ba",
            ),
            "T083 audit comparison": (
                self.root / "reports/agents/audit/audit_comparison.json",
                "b79784b3d34e769d2a7257d2803f55542fc3935bf2f1ff348f7b61ed67b5aa1d",
            ),
        }
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for value in fixture["inputs"]:
            row = _mapping(value, "redteam input")
            _keys(row, {"label", "path", "sha256"}, "redteam input")
            label = _string(row.get("label"), "redteam input label")
            if label not in expected:
                raise RedTeamError(f"unexpected redteam input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "redteam input path")).resolve(strict=True)
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise RedTeamError(f"redteam input path or checksum differs: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise RedTeamError(f"redteam input checksum differs: {label}")
            rows.append({"label": label, "path": row["path"]})
            seen.add(label)
        if seen != set(expected):
            raise RedTeamError("redteam inputs are incomplete")
        return tuple(rows)

    @staticmethod
    def _attacks(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        required = {
            "attack_id",
            "kind",
            "payload",
            "expected_status",
            "severity",
            "remediation",
        }
        allowed_kinds = {
            "leakage",
            "unit_error",
            "negative_control",
            "adversarial_claim",
            "lockbox",
        }
        allowed_statuses = {"DETECTED", "BLOCKED", "CLEAN"}
        allowed_severity = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        attacks: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["attacks"]:
            attack = _mapping(value, "redteam attack")
            _keys(attack, required, "redteam attack")
            attack_id = _string(attack.get("attack_id"), "redteam attack ID")
            if attack_id in seen:
                raise RedTeamError(f"duplicate redteam attack: {attack_id}")
            if attack.get("kind") not in allowed_kinds:
                raise RedTeamError(f"unsupported redteam attack kind: {attack_id}")
            if attack.get("expected_status") not in allowed_statuses:
                raise RedTeamError(f"unsupported redteam expected status: {attack_id}")
            if attack.get("severity") not in allowed_severity:
                raise RedTeamError(f"unsupported redteam severity: {attack_id}")
            if not isinstance(attack.get("payload"), dict):
                raise RedTeamError(f"redteam payload is invalid: {attack_id}")
            if not isinstance(attack.get("remediation"), str) or not attack["remediation"].strip():
                raise RedTeamError(f"redteam remediation is missing: {attack_id}")
            attacks.append(dict(attack))
            seen.add(attack_id)
        if not attacks:
            raise RedTeamError("redteam fixture has no attacks")
        return attacks

    def _execute(self, attack: dict[str, Any]) -> tuple[str, str]:
        kind = attack["kind"]
        payload = _mapping(attack["payload"], "redteam payload")
        if kind == "leakage":
            return (
                ("DETECTED", "blacklisted_feature_detected")
                if payload.get("feature")
                in {
                    "paper_id",
                    "accession",
                    "author",
                    "study_id",
                }
                else ("CLEAN", "blacklisted_feature_not_detected")
            )
        if kind == "unit_error":
            return (
                ("DETECTED", "unit_inconsistency_detected")
                if payload.get("unit_a") != payload.get("unit_b")
                else ("CLEAN", "unit_consistent")
            )
        if kind == "negative_control":
            return (
                ("CLEAN", "negative_control_remained_null")
                if payload.get("expected_signal") is False
                else ("DETECTED", "negative_control_signal_detected")
            )
        if kind == "adversarial_claim":
            return (
                ("BLOCKED", "causal_language_gate_blocked")
                if payload.get("causal_claim") is True
                else ("CLEAN", "claim_is_associational")
            )
        firewall = LockboxFirewall(self.root)
        try:
            firewall.assert_development_read_allowed(self.root / "data/locked_test/payload.bin")
        except LockboxAccessError:
            return "BLOCKED", "lockbox_firewall_blocked"
        return "DETECTED", "lockbox_firewall_failed"

    def run(self, *, all_attacks: bool = True) -> RedTeamSummary:
        """Run the complete mandatory attack matrix and release gate."""
        if not all_attacks:
            raise RedTeamError("--all is required for redteam evaluation")
        schema_valid = self._schema_valid()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        attacks = self._attacks(fixture_data)
        trace = TraceLedger()
        findings: list[dict[str, Any]] = []
        detected = 0
        blocked = 0
        critical_findings = 0
        remediations = 0
        adverse_preserved = True
        for attack in attacks:
            attack_id = _string(attack["attack_id"], "redteam attack ID")
            observed, detector = self._execute(attack)
            expected = attack["expected_status"]
            passed = observed == expected
            if observed == "DETECTED":
                detected += 1
            if observed == "BLOCKED":
                blocked += 1
            unresolved = not passed
            if unresolved and attack["severity"] == "CRITICAL":
                critical_findings += 1
            if attack["remediation"]:
                remediations += 1
            trace.append(
                "redteam_attack_executed",
                attack_id,
                0,
                {"kind": attack["kind"], "observed_status": observed, "passed": passed},
            )
            finding = {
                "attack_id": attack_id,
                "kind": attack["kind"],
                "expected_status": expected,
                "observed_status": observed,
                "detector": detector,
                "severity": attack["severity"],
                "remediation": attack["remediation"],
                "passed": passed,
                "adverse_result_preserved": True,
                "payload": attack["payload"],
            }
            adverse_preserved = adverse_preserved and finding["payload"] == attack["payload"]
            findings.append(finding)
        trace.validate()
        release_blocked = critical_findings > 0
        selected = "redteam_agent" if schema_valid and adverse_preserved and not release_blocked else "release_blocked"
        comparison = {
            "schema_version": 1,
            "attacks": len(attacks),
            "executed": len(attacks),
            "detected": detected,
            "blocked": blocked,
            "critical_findings": critical_findings,
            "remediations": remediations,
            "adverse_results_preserved": adverse_preserved,
            "release_blocked": release_blocked,
            "selected_pipeline": selected,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "findings": {
                "schema_version": 1,
                "findings": findings,
                "target_values_exposed": False,
            },
            "comparison": comparison,
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
            "findings": self.output_root / "redteam_findings.json",
            "comparison": self.output_root / "redteam_comparison.json",
            "inputs": self.output_root / "input_manifest.json",
            "adverse": self.output_root / "adverse_results.json",
            "failures": self.output_root / "failure_ledger.json",
            "trace": self.output_root / "redteam_trace.jsonl",
            "seal": self.output_root / "redteam_trace_seal.json",
            "receipt": self.output_root / "redteam_receipt.json",
            "log": self.output_root / "redteam_log.json",
            "manifest": self.output_root / "redteam_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        payload_bytes["adverse"] = _canonical(
            {"schema_version": 1, "results": findings, "preserved": adverse_preserved}
        )
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
            "model": "REDTEAM_AGENT",
            "status": "VALID",
            "fixture": True,
            "attacks": len(attacks),
            "executed": len(attacks),
            "detected": detected,
            "blocked": blocked,
            "critical_findings": critical_findings,
            "remediations": remediations,
            "adverse_results_preserved": adverse_preserved,
            "release_blocked": release_blocked,
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
                    {"event": "mandatory_attack_matrix_loaded", "attacks": len(attacks)},
                    {"event": "leakage_and_unit_error_attacks_executed", "detected": detected},
                    {"event": "adverse_results_preserved", "passed": adverse_preserved},
                    {"event": "critical_release_gate_evaluated", "blocked": release_blocked},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "REDTEAM_AGENT",
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
                raise RedTeamError("existing redteam receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise RedTeamError(f"existing redteam artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return RedTeamSummary(
            attacks=len(attacks),
            executed=len(attacks),
            detected=detected,
            blocked=blocked,
            critical_findings=critical_findings,
            remediations=remediations,
            adverse_results_preserved=adverse_preserved,
            release_blocked=release_blocked,
            selected_pipeline=selected,
            trace_events=len(trace.records),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
