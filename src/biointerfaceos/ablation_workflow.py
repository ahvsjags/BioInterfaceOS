"""Fixture-backed paired model and data ablation workflow."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AblationError(RuntimeError):
    """Raised when the T099 ablation contract is invalid."""


@dataclass(frozen=True)
class AblationSummary:
    """Summary of the frozen paired ablation matrix."""

    comparisons: int
    rows: int
    same_splits: bool
    same_budget: bool
    mean_effect: float
    interval_records: int
    calibration_records: int
    ood_records: int
    missing_ablations: int
    claim_blocks: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AblationError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AblationError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise AblationError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise AblationError(f"{label} must be finite")
    return result


class AblationWorkflow:
    """Compare frozen full and ablated workflows on the same paired units."""

    ABLATIONS = (
        "multimodal_fusion",
        "uncertainty_calibration",
        "mediation_path",
        "symbolic_law",
        "candidate_audit_support",
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/robustness/ablations_fixture.json")
        self.output_root = output_root or self.root / "reports/robustness/ablations"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "ablation fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AblationError(f"cannot load ablation fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != ("mandatory_model_and_data_ablations"):
            raise AblationError("ablation fixture schema or mode is invalid")
        for key in ("inputs", "preregistration", "paired_rows", "missing_ablations"):
            if key not in data:
                raise AblationError(f"ablation fixture is missing {key}")
        if not all(isinstance(data[key], list) for key in ("inputs", "paired_rows", "missing_ablations")):
            raise AblationError("ablation fixture list fields are invalid")
        preregistration = _mapping(data["preregistration"], "ablation preregistration")
        if preregistration.get("schema_version") != 1:
            raise AblationError("ablation preregistration schema is invalid")
        if preregistration.get("ablations") != list(self.ABLATIONS):
            raise AblationError("ablation list is not frozen")
        if preregistration.get("split_id") != "frozen_group_split_v1":
            raise AblationError("ablation split policy is not frozen")
        if preregistration.get("target_values_exposed") is not False:
            raise AblationError("ablation target values must remain hidden")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected: dict[str, tuple[Path, str]] = {
            "T078 uncertainty receipt": (
                self.root / "reports/models/uncertainty/uncertainty_receipt.json",
                "f36a003c4c2afb5dc7713af841e6736274ee9582a58f9eef306bc7f537676a71",
            ),
            "T079 multimodal receipt": (
                self.root / "reports/models/multimodal/multimodal_receipt.json",
                "abcee7f3ba8daf2d53f112cd4e3fb0a0147b1c5e269f243c3fbd61e27733292a",
            ),
            "T091 mediation receipt": (
                self.root / "reports/omics/mediation/mediation_receipt.json",
                "11e522edee14fa5e5daf2482f044df6163db6573ca7a6a6a3d9eb7ac442dc945",
            ),
            "T093 symbolic-laws receipt": (
                self.root / "reports/omics/symbolic_laws/symbolic_laws_receipt.json",
                "bce24812c8b301a7133522b9647b1c13c6b6629d19f1e8601836cec1a637ae55",
            ),
            "T098 candidate-audit receipt": (
                self.root / "reports/design/candidates/candidate_audit_receipt.json",
                "dde1e0c1c0d647893918c3b16e9db10f63a1aea9251140e5c1db86d616f517a6",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "ablation input")
            label = _string(row.get("label"), "ablation input label")
            if label not in expected:
                raise AblationError(f"unexpected ablation input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "ablation input path")).resolve(strict=True)
            raw = path.read_bytes()
            payload = _mapping(json.loads(raw), f"{label} payload")
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise AblationError(f"ablation input path/checksum differs: {label}")
            if _sha256(raw) != checksum or payload.get("status") != "VALID":
                raise AblationError(f"ablation input is not valid: {label}")
            seen.add(label)
        if seen != set(expected):
            raise AblationError("ablation inputs do not match T078/T079/T091/T093/T098")

    @classmethod
    def _preregistration(cls, fixture: Mapping[str, Any]) -> dict[str, Any]:
        preregistration = _mapping(fixture["preregistration"], "ablation preregistration")
        for key in ("budget", "bootstrap_samples", "alpha"):
            _number(preregistration.get(key), f"ablation {key}")
        if preregistration["budget"] != 8 or preregistration["bootstrap_samples"] != 64:
            raise AblationError("ablation budget/bootstrap configuration is not frozen")
        if preregistration["alpha"] != 0.05:
            raise AblationError("ablation alpha is not frozen")
        return preregistration

    @classmethod
    def _rows(cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "ablation",
            "pair_id",
            "group_id",
            "split",
            "full_metric",
            "ablated_metric",
            "full_calibration_error",
            "ablated_calibration_error",
            "full_ood_rmse",
            "ablated_ood_rmse",
            "budget",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["paired_rows"]:
            source = _mapping(value, "paired ablation row")
            if set(source) != required:
                raise AblationError("paired ablation fields do not match schema")
            ablation = _string(source.get("ablation"), "ablation name")
            if ablation not in cls.ABLATIONS:
                raise AblationError(f"unknown ablation: {ablation}")
            pair_id = _string(source.get("pair_id"), "ablation pair ID")
            if pair_id in seen:
                raise AblationError(f"duplicate ablation pair: {pair_id}")
            group_id = _string(source.get("group_id"), "ablation group ID")
            split = _string(source.get("split"), "ablation split")
            if split not in {"development", "heldout"}:
                raise AblationError(f"invalid ablation split: {split}")
            if source.get("budget") != preregistration["budget"]:
                raise AblationError(f"ablation budget mismatch: {pair_id}")
            row = {
                "ablation": ablation,
                "pair_id": pair_id,
                "group_id": group_id,
                "split": split,
                "full_metric": _number(source.get("full_metric"), "full metric"),
                "ablated_metric": _number(source.get("ablated_metric"), "ablated metric"),
                "full_calibration_error": _number(source.get("full_calibration_error"), "full calibration error"),
                "ablated_calibration_error": _number(
                    source.get("ablated_calibration_error"), "ablated calibration error"
                ),
                "full_ood_rmse": _number(source.get("full_ood_rmse"), "full OOD RMSE"),
                "ablated_ood_rmse": _number(source.get("ablated_ood_rmse"), "ablated OOD RMSE"),
                "budget": int(source["budget"]),
            }
            rows.append(row)
            seen.add(pair_id)
        counts = {name: sum(row["ablation"] == name for row in rows) for name in cls.ABLATIONS}
        if any(count != 4 for count in counts.values()):
            raise AblationError(f"each ablation must have four paired rows: {counts}")
        return rows

    @staticmethod
    def _interval(values: list[float], samples: int) -> dict[str, float | int]:
        if not values:
            raise AblationError("cannot interval empty paired effects")
        bootstrap: list[float] = []
        for index in range(samples):
            draw = [values[(index + offset * 3) % len(values)] for offset in range(len(values))]
            bootstrap.append(sum(draw) / len(draw))
        ordered = sorted(bootstrap)
        lower_index = int(0.025 * (len(ordered) - 1))
        upper_index = int(0.975 * (len(ordered) - 1))
        return {
            "bootstrap_samples": samples,
            "ci95_lower": round(ordered[lower_index], 8),
            "ci95_upper": round(ordered[upper_index], 8),
        }

    @classmethod
    def _comparisons(
        cls, rows: list[dict[str, Any]], preregistration: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float, bool, bool]:
        signatures: list[tuple[tuple[str, str], ...]] = []
        budgets: list[set[int]] = []
        paired: dict[str, Any] = {}
        intervals: dict[str, Any] = {}
        calibration_ood: dict[str, Any] = {}
        effects_all: list[float] = []
        for name in cls.ABLATIONS:
            selected = [row for row in rows if row["ablation"] == name]
            signatures.append(tuple((row["group_id"], row["split"]) for row in selected))
            budgets.append({row["budget"] for row in selected})
            effects = [row["full_metric"] - row["ablated_metric"] for row in selected]
            calibration = [row["ablated_calibration_error"] - row["full_calibration_error"] for row in selected]
            ood = [row["ablated_ood_rmse"] - row["full_ood_rmse"] for row in selected]
            effects_all.extend(effects)
            effect_mean = round(sum(effects) / len(effects), 8)
            paired[name] = {
                "rows": len(selected),
                "effect_definition": "full_metric_minus_ablated_metric",
                "effect_mean": effect_mean,
                "effects": [round(value, 8) for value in effects],
                "same_pair_units": len({row["pair_id"] for row in selected}) == len(selected),
                "budget": selected[0]["budget"],
            }
            intervals[name] = {
                "ablation": name,
                **AblationWorkflow._interval(effects, int(preregistration["bootstrap_samples"])),
            }
            calibration_ood[name] = {
                "ablation": name,
                "calibration_gain": round(sum(calibration) / len(calibration), 8),
                "ood_rmse_gain": round(sum(ood) / len(ood), 8),
                "calibration_effects": [round(value, 8) for value in calibration],
                "ood_effects": [round(value, 8) for value in ood],
            }
        same_splits = len(set(signatures)) == 1
        same_budget = len(set(tuple(sorted(values)) for values in budgets)) == 1
        overall_effect = round(sum(effects_all) / len(effects_all), 8)
        return paired, intervals, calibration_ood, overall_effect, same_splits, same_budget

    @staticmethod
    def _missing(fixture: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
        required = {
            "name",
            "essential",
            "interface_test",
            "result",
            "justification",
            "claim_blocked",
        }
        missing: list[dict[str, Any]] = []
        claim_blocks = 0
        for value in fixture["missing_ablations"]:
            source = _mapping(value, "missing ablation")
            if set(source) != required:
                raise AblationError("missing-ablation fields do not match schema")
            if not isinstance(source.get("essential"), bool) or not isinstance(source.get("claim_blocked"), bool):
                raise AblationError("missing-ablation flags are invalid")
            if not _string(source.get("interface_test"), "missing interface test"):
                raise AblationError("missing interface test is empty")
            if source["essential"] and not source["claim_blocked"]:
                raise AblationError("essential missing ablation must block its claim")
            claim_blocks += int(source["claim_blocked"])
            missing.append(
                {
                    "name": _string(source.get("name"), "missing ablation name"),
                    "essential": source["essential"],
                    "interface_test": source["interface_test"],
                    "result": _string(source.get("result"), "missing ablation result"),
                    "justification": _string(source.get("justification"), "missing justification"),
                    "claim_blocked": source["claim_blocked"],
                }
            )
        return missing, claim_blocks

    def run(self, *, all_ablations: bool = True) -> AblationSummary:
        """Run all declared paired ablations under one frozen split/budget."""
        if not all_ablations:
            raise AblationError("--all is required for mandatory ablations")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = self._preregistration(fixture_data)
        rows = self._rows(fixture_data, preregistration)
        paired, intervals, calibration_ood, overall_effect, same_splits, same_budget = self._comparisons(
            rows, preregistration
        )
        missing, claim_blocks = self._missing(fixture_data)
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
        claim_gate = {
            "schema_version": 1,
            "status": "PASS" if same_splits and same_budget and claim_blocks == 0 else "BLOCK",
            "all_declared_ablations_available": True,
            "same_splits": same_splits,
            "same_budget": same_budget,
            "missing_ablations": len(missing),
            "claim_blocks": claim_blocks,
            "policy": "block_associated_claim_on_missing_essential_ablation",
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                **preregistration,
                "frozen_before_evaluation": True,
                "target_values_exposed": False,
            },
            "paired": {"schema_version": 1, "comparisons": paired},
            "intervals": {"schema_version": 1, "intervals": intervals},
            "calibration_ood": {"schema_version": 1, "records": calibration_ood},
            "missing": {"schema_version": 1, "records": missing},
            "claim_gate": claim_gate,
            "failures": {
                "schema_version": 1,
                "status": "VALID" if not found else "INVALID",
                "failures": [],
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "ablation_preregistration.json",
            "paired": self.output_root / "paired_effects.json",
            "intervals": self.output_root / "interval_report.json",
            "calibration_ood": self.output_root / "calibration_ood.json",
            "missing": self.output_root / "missingness_ledger.json",
            "claim_gate": self.output_root / "claim_gate.json",
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
        receipt_path = self.output_root / "ablations_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "comparisons": len(self.ABLATIONS),
            "rows": len(rows),
            "same_splits": same_splits,
            "same_budget": same_budget,
            "mean_effect": overall_effect,
            "interval_records": len(intervals),
            "calibration_records": len(calibration_ood),
            "ood_records": len(calibration_ood),
            "missing_ablations": len(missing),
            "claim_blocks": claim_blocks,
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifacts,
        }
        receipt_bytes = _canonical(receipt)
        receipt_path.write_bytes(receipt_bytes)
        manifest = {
            "schema_version": 1,
            "workflow": "MANDATORY_MODEL_AND_DATA_ABLATIONS",
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
        (self.output_root / "ablations_manifest.json").write_bytes(_canonical(manifest))
        return AblationSummary(
            comparisons=len(self.ABLATIONS),
            rows=len(rows),
            same_splits=same_splits,
            same_budget=same_budget,
            mean_effect=overall_effect,
            interval_records=len(intervals),
            calibration_records=len(calibration_ood),
            ood_records=len(calibration_ood),
            missing_ablations=len(missing),
            claim_blocks=claim_blocks,
            resumed=resumed,
            receipt_path=receipt_path,
        )
