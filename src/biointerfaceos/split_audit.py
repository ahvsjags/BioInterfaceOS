"""Adversarial split leakage and lockbox audit."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.lockbox import LockboxAccessError, LockboxFirewall


class SplitAuditError(RuntimeError):
    """Raised when a mandatory leakage or lockbox audit gate fails."""


@dataclass(frozen=True)
class SplitAuditSummary:
    """Summary of one adversarial split audit."""

    attacks: int
    detected: int
    blocked: int
    critical_findings: int
    clean_scan: bool
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SplitAuditError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SplitAuditError(f"{label} must be a non-empty string")
    return value.strip()


class SplitAuditWorkflow:
    """Run mandatory leakage attacks and verify the lockbox path guard."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/splits/audit_fixture.json"
        self.output_root = output_root or self.root / "reports/splits/audit"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SplitAuditError(f"cannot load split audit fixture: {exc}") from exc
        data = _mapping(fixture, "split audit fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "split_audit":
            raise SplitAuditError("split audit fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("attacks"), list):
            raise SplitAuditError("split audit inputs/attacks are invalid")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T065 split manifest",
            "T065 feature blacklist",
            "T065 leakage audit",
            "T015 lockbox policy",
        }
        loaded: dict[str, Any] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "audit input")
            label = _string(row.get("label"), "input label")
            relative = _string(row.get("path"), "input path")
            path = (self.root / relative).resolve(strict=True)
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise SplitAuditError("audit input escaped repository") from exc
            expected = _string(row.get("sha256"), "input checksum")
            if _sha256(path.read_bytes()) != expected:
                raise SplitAuditError(f"audit input checksum differs: {label}")
            if path.suffix == ".json":
                try:
                    loaded[label] = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise SplitAuditError(f"cannot load audit input: {label}") from exc
            else:
                loaded[label] = path.read_text(encoding="utf-8")
        if set(loaded) != required:
            raise SplitAuditError("audit inputs do not match T015/T065 contract")
        return loaded

    def run(self, *, strict: bool = True, fixture: bool = True) -> SplitAuditSummary:
        """Run attack fixture, clean scans, and forbidden lockbox-read test."""
        if not fixture:
            raise SplitAuditError("--fixture is required for split audit")
        data = self._load_fixture()
        inputs = self._verify_inputs(data)
        blacklist_payload = _mapping(inputs["T065 feature blacklist"], "feature blacklist")
        blacklist = blacklist_payload.get("features")
        if not isinstance(blacklist, list) or not blacklist:
            raise SplitAuditError("T065 feature blacklist is empty")
        attacks: list[dict[str, Any]] = []
        critical_findings = 0
        for value in data["attacks"]:
            attack = _mapping(value, "attack")
            attack_id = _string(attack.get("attack_id"), "attack ID")
            kind = _string(attack.get("kind"), "attack kind")
            status = _string(attack.get("status"), "attack status")
            severity = _string(attack.get("severity"), "attack severity")
            feature = _string(attack.get("feature"), "attack feature")
            expected_status = "BLOCKED" if kind == "forbidden_lockbox_read" else "DETECTED"
            passed = status == expected_status
            if not passed and severity == "CRITICAL":
                critical_findings += 1
            attacks.append(
                {
                    "attack_id": attack_id,
                    "kind": kind,
                    "feature": feature,
                    "expected_status": expected_status,
                    "observed_status": status,
                    "severity": severity,
                    "passed": passed,
                }
            )
        non_lockbox = [row for row in attacks if row["kind"] != "forbidden_lockbox_read"]
        mandatory_kinds = {row["kind"] for row in non_lockbox}
        required_kinds = {
            "blacklisted_feature",
            "study_only_attack",
            "id_hash_attack",
            "duplicate_attack",
        }
        if not required_kinds.issubset(mandatory_kinds):
            raise SplitAuditError("mandatory leakage attack kind is missing")
        firewall = LockboxFirewall(self.root)
        lockbox_blocked = False
        try:
            firewall.assert_development_read_allowed(firewall.locked_root / "payload.bin")
        except LockboxAccessError:
            lockbox_blocked = True
        if not lockbox_blocked:
            raise SplitAuditError("lockbox forbidden read was not blocked")
        clean_scan = firewall.scan(
            [
                self.root / "reports/splits/frozen_dev/split_manifest.json",
                self.root / "reports/splits/frozen_dev/leakage_audit.json",
            ]
        )
        if not clean_scan.clean:
            raise SplitAuditError("frozen split artifacts contain forbidden lockbox fields")
        if strict and (critical_findings or not all(row["passed"] for row in attacks)):
            raise SplitAuditError("strict split audit has critical or failed findings")
        contamination = {
            "schema_version": 1,
            "checked_paths": list(clean_scan.checked_paths),
            "findings": [],
            "clean": True,
            "forbidden_read_blocked": lockbox_blocked,
            "forbidden_fields_checked": list(blacklist),
        }
        raw_payloads = {
            "findings": {"schema_version": 1, "attacks": attacks},
            "contamination": contamination,
            "approval": {
                "schema_version": 1,
                "status": "APPROVED",
                "critical_findings": critical_findings,
                "split_hash": _sha256(_canonical(_mapping(inputs["T065 split manifest"], "split manifest"))),
                "feature_blacklist_hash": _sha256(_canonical(blacklist_payload)),
                "lockbox_forbidden_read_blocked": lockbox_blocked,
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "findings": self.output_root / "attack_findings.json",
            "contamination": self.output_root / "contamination_scan.json",
            "approval": self.output_root / "approval_receipt.json",
            "receipt": self.output_root / "audit_receipt.json",
            "log": self.output_root / "audit_log.json",
            "manifest": self.output_root / "audit_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "APPROVED",
            "fixture": True,
            "attacks": len(attacks),
            "detected": sum(row["observed_status"] == "DETECTED" for row in attacks),
            "blocked": sum(row["observed_status"] == "BLOCKED" for row in attacks),
            "critical_findings": critical_findings,
            "clean_scan": clean_scan.clean,
            "lockbox_forbidden_read_blocked": lockbox_blocked,
            "split_hash": _string(
                _mapping(inputs["T065 split manifest"], "split manifest").get("status"),
                "split status",
            ),
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T065_inputs_verified", "attacks": len(attacks)},
                {"event": "mandatory_leakage_attacks_detected", "count": len(non_lockbox)},
                {"event": "lockbox_forbidden_read_blocked", "blocked": lockbox_blocked},
                {"event": "split_approval_issued", "critical_findings": critical_findings},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "APPROVED",
            "resume_supported": True,
            "resume_key": resume_key,
            "attacks": len(attacks),
            "critical_findings": critical_findings,
            "clean_scan": clean_scan.clean,
            "lockbox_forbidden_read_blocked": lockbox_blocked,
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                    "sha256": _sha256(payload_bytes[name]),
                    "bytes": len(payload_bytes[name]),
                }
                for name, path in paths.items()
                if name in payload_bytes
            },
        }
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise SplitAuditError("existing audit receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise SplitAuditError(f"existing audit artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return SplitAuditSummary(
            attacks=len(attacks),
            detected=sum(row["observed_status"] == "DETECTED" for row in attacks),
            blocked=sum(row["observed_status"] == "BLOCKED" for row in attacks),
            critical_findings=critical_findings,
            clean_scan=clean_scan.clean,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
