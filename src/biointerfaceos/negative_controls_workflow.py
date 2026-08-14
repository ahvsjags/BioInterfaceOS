"""Fixture-backed negative controls and deliberate leakage attack suite."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class NegativeControlsError(RuntimeError):
    """Raised when the T102 attack-suite contract is invalid."""


@dataclass(frozen=True)
class NegativeControlsSummary:
    """Summary of the strict negative-control gate."""

    attacks: int
    expected_failures: int
    detected: int
    critical_leaks: int
    duplicate_hits: int
    strict_pass: bool
    claim_status: str
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NegativeControlsError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NegativeControlsError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise NegativeControlsError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise NegativeControlsError(f"{label} must be finite")
    return result


class NegativeControlsWorkflow:
    """Run expected-failure controls and critical leakage detection."""

    ATTACKS = (
        "label_shuffle",
        "random_mediator",
        "study_proxy",
        "journal_proxy",
        "year_proxy",
        "layout_proxy",
        "unit_proxy",
        "missingness_proxy",
        "duplicate_attack",
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/robustness/negative_controls_fixture.json")
        self.output_root = output_root or self.root / "reports/robustness/negative_controls"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "negative-controls fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise NegativeControlsError(f"cannot load negative-controls fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != ("negative_controls_and_deliberate_leakage_attacks"):
            raise NegativeControlsError("negative-controls fixture schema or mode is invalid")
        for key in ("inputs", "preregistration", "attacks"):
            if key not in data:
                raise NegativeControlsError(f"negative-controls fixture is missing {key}")
        if not isinstance(data["inputs"], list) or not isinstance(data["attacks"], list):
            raise NegativeControlsError("negative-controls fixture list fields are invalid")
        preregistration = _mapping(data["preregistration"], "attack preregistration")
        if preregistration.get("schema_version") != 1 or preregistration.get("strict") is not True:
            raise NegativeControlsError("strict attack policy is not frozen")
        if preregistration.get("target_values_exposed") is not False:
            raise NegativeControlsError("attack fixture target values must remain hidden")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected: dict[str, tuple[Path, str]] = {
            "T086 extraction/red-team receipt": (
                self.root / "reports/agents/extraction/extraction_agent_receipt.json",
                "2a024779827fd8cde45822e347bd40f03d3d0411764fa30c0a667598f297a1c4",
            ),
            "T099 ablations receipt": (
                self.root / "reports/robustness/ablations/ablations_receipt.json",
                "bde553a6a188e2b0a733495d8b89493f9573086e05dd639db7c47edb7a2cee54",
            ),
            "T100 OOD receipt": (
                self.root / "reports/robustness/ood/ood_receipt.json",
                "2172d6139361a6b10e5d80ba199c21c7854830eeaa2152dc82f10931387beb2e",
            ),
            "T101 bias receipt": (
                self.root / "reports/robustness/bias/bias_receipt.json",
                "9e989284b402ae6709d8b4ad5c042b8c5385d4b13fc2ba0208fa0fbc7ae38c97",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "attack input")
            label = _string(row.get("label"), "attack input label")
            if label not in expected:
                raise NegativeControlsError(f"unexpected attack input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "attack input path")).resolve(strict=True)
            raw = path.read_bytes()
            payload = _mapping(json.loads(raw), label)
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise NegativeControlsError(f"attack input path/checksum differs: {label}")
            if _sha256(raw) != checksum or payload.get("status") != "VALID":
                raise NegativeControlsError(f"attack input is not valid: {label}")
            seen.add(label)
        if seen != set(expected):
            raise NegativeControlsError("attack inputs do not match T086/T099/T100/T101")

    @classmethod
    def _attacks(cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "attack_id",
            "category",
            "performance",
            "detected",
            "critical",
            "duplicate_count",
            "expected_outcome",
            "remediation",
        }
        attacks: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["attacks"]:
            source = _mapping(value, "negative-control attack")
            if set(source) != required:
                raise NegativeControlsError("attack fields do not match schema")
            attack_id = _string(source.get("attack_id"), "attack ID")
            category = _string(source.get("category"), "attack category")
            if attack_id in seen or category not in cls.ATTACKS:
                raise NegativeControlsError("attack ID/category is invalid or duplicated")
            if not isinstance(source.get("detected"), bool) or not isinstance(source.get("critical"), bool):
                raise NegativeControlsError("attack flags are invalid")
            performance = _number(source.get("performance"), "attack performance")
            if performance < 0 or performance > 1:
                raise NegativeControlsError("attack performance is out of range")
            attacks.append(
                {
                    "attack_id": attack_id,
                    "category": category,
                    "performance": performance,
                    "detected": source["detected"],
                    "critical": source["critical"],
                    "duplicate_count": int(source["duplicate_count"]),
                    "expected_outcome": _string(source.get("expected_outcome"), "expected outcome"),
                    "remediation": _string(source.get("remediation"), "remediation"),
                }
            )
            seen.add(attack_id)
        if {row["category"] for row in attacks} != set(cls.ATTACKS):
            raise NegativeControlsError("mandatory attack set is incomplete")
        if preregistration["split_id"] != "frozen_group_split_v1" or preregistration["budget"] != 8:
            raise NegativeControlsError("attack split/budget is not frozen")
        return attacks

    def run(self, *, strict: bool = True) -> NegativeControlsSummary:
        """Run all attacks and return strict release/claim gate."""
        if not strict:
            raise NegativeControlsError("--strict is required for negative controls")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = _mapping(fixture_data["preregistration"], "attack preregistration")
        attacks = self._attacks(fixture_data, preregistration)
        baseline = float(preregistration["baseline_performance"])
        threshold = float(preregistration["expected_failure_threshold"])
        evaluated: list[dict[str, Any]] = []
        for attack in attacks:
            expected_failure = attack["performance"] <= baseline * threshold
            passed = expected_failure or attack["detected"]
            critical_leak = attack["critical"] and not attack["detected"]
            evaluated.append(
                {
                    **attack,
                    "expected_failure": expected_failure,
                    "critical_leak": critical_leak,
                    "pass": passed and not critical_leak,
                }
            )
        critical_leaks = sum(row["critical_leak"] for row in evaluated)
        strict_pass = all(row["pass"] for row in evaluated) and critical_leaks == 0
        duplicate_hits = sum(row["duplicate_count"] for row in evaluated)
        expected_failures = sum(row["expected_failure"] for row in evaluated)
        detected = sum(row["detected"] for row in evaluated)
        claim_status = "ATTACKS_CLEAN" if strict_pass else "RELEASE_INVALIDATED_CRITICAL_LEAK"
        rollback = {
            "schema_version": 1,
            "strict_pass": strict_pass,
            "critical_leaks": critical_leaks,
            "release_action": "CLEAN_RELEASE_RETAINED" if strict_pass else "INVALIDATE_AND_ROLLBACK",
            "last_clean_release": "bioif-data-20260811-42783ef-e32d9290",
            "claim_status": claim_status,
        }
        fixture_text = self.fixture_path.read_text(encoding="utf-8").lower()
        prohibited = ["api_key", "credential", "private_key", "locked_payload", "secret"]
        found = [token for token in prohibited if token in fixture_text]
        lockbox = {
            "schema_version": 1,
            "status": "CLEAN" if not found else "BLOCKED",
            "prohibited_tokens": found,
            "target_values_exposed": False,
            "raw_download": False,
            "network_accessed": False,
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                **preregistration,
                "frozen_before_attack": True,
                "target_values_exposed": False,
            },
            "results": {"schema_version": 1, "attacks": evaluated},
            "leakage": {
                "schema_version": 1,
                "records": [row for row in evaluated if row["category"] != "duplicate_attack"],
                "critical_leaks": critical_leaks,
            },
            "duplicates": {
                "schema_version": 1,
                "records": [row for row in evaluated if row["category"] == "duplicate_attack"],
                "duplicate_hits": duplicate_hits,
            },
            "rollback": rollback,
            "failures": {
                "schema_version": 1,
                "status": "VALID" if not found else "INVALID",
                "failures": [],
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "attack_preregistration.json",
            "results": self.output_root / "control_results.json",
            "leakage": self.output_root / "leakage_audit.json",
            "duplicates": self.output_root / "duplicate_audit.json",
            "rollback": self.output_root / "rollback_claim_gate.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        artifacts: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            payload = _canonical(raw_payloads[name])
            path.write_bytes(payload)
            artifacts[name] = {
                "path": (str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path)),
                "sha256": _sha256(payload),
                "bytes": len(payload),
            }
        lockbox_path = self.output_root / "lockbox_scan.json"
        lockbox_bytes = _canonical(lockbox)
        lockbox_path.write_bytes(lockbox_bytes)
        artifacts["lockbox"] = {
            "path": (
                str(lockbox_path.relative_to(self.root))
                if lockbox_path.is_relative_to(self.root)
                else str(lockbox_path)
            ),
            "sha256": _sha256(lockbox_bytes),
            "bytes": len(lockbox_bytes),
        }
        receipt_path = self.output_root / "negative_controls_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found and strict_pass else "INVALID",
            "fixture": True,
            "attacks": len(attacks),
            "expected_failures": expected_failures,
            "detected": detected,
            "critical_leaks": critical_leaks,
            "duplicate_hits": duplicate_hits,
            "strict_pass": strict_pass,
            "claim_status": claim_status,
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifacts,
        }
        receipt_bytes = _canonical(receipt)
        receipt_path.write_bytes(receipt_bytes)
        manifest = {
            "schema_version": 1,
            "workflow": "NEGATIVE_CONTROLS_AND_DELIBERATE_LEAKAGE_ATTACKS",
            "status": receipt["status"],
            "resume_key": resume_key,
            "resume_supported": True,
            "target_values_exposed": False,
            "artifacts": {
                **artifacts,
                "receipt": {
                    "path": (
                        str(receipt_path.relative_to(self.root))
                        if receipt_path.is_relative_to(self.root)
                        else str(receipt_path)
                    ),
                    "sha256": _sha256(receipt_bytes),
                    "bytes": len(receipt_bytes),
                },
            },
        }
        (self.output_root / "negative_controls_manifest.json").write_bytes(_canonical(manifest))
        return NegativeControlsSummary(
            attacks=len(attacks),
            expected_failures=expected_failures,
            detected=detected,
            critical_leaks=critical_leaks,
            duplicate_hits=duplicate_hits,
            strict_pass=strict_pass,
            claim_status=claim_status,
            resumed=resumed,
            receipt_path=receipt_path,
        )
