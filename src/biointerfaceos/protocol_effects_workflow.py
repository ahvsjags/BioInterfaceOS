"""Fixture-backed protocol correction and reversal hypothesis tests."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ProtocolEffectsError(RuntimeError):
    """Raised when the T094 protocol-effects contract is invalid."""


@dataclass(frozen=True)
class ProtocolEffectsSummary:
    """Summary of one deterministic protocol-effects run."""

    rows: int
    variables: int
    studies: int
    raw_effect: float
    adjusted_effect: float
    reversal_tests: int
    reversals_detected: int
    counterexamples: int
    heterogeneity_max: float
    universal_reversal_permitted: bool
    language_status: str
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtocolEffectsError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolEffectsError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ProtocolEffectsError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ProtocolEffectsError(f"{label} must be finite")
    return result


def _mean(values: list[float]) -> float:
    if not values:
        raise ProtocolEffectsError("cannot average an empty set")
    return sum(values) / len(values)


def _sign(value: float, tolerance: float = 1e-9) -> str:
    if value > tolerance:
        return "positive"
    if value < -tolerance:
        return "negative"
    return "zero"


class ProtocolEffectsWorkflow:
    """Evaluate protocol correction and reversal without post-hoc subgroup search."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/protocol_effects_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/protocol_effects"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "protocol-effects fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProtocolEffectsError(f"cannot load protocol-effects fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "protocol_effects_reversal":
            raise ProtocolEffectsError("protocol-effects fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise ProtocolEffectsError("protocol-effects inputs/rows are invalid")
        preregistration = _mapping(data.get("preregistration"), "protocol-effects preregistration")
        if preregistration.get("schema_version") != 1:
            raise ProtocolEffectsError("protocol-effects preregistration schema is invalid")
        required_variables = ["species", "biofluid", "assay", "dose_bin"]
        if preregistration.get("variables") != required_variables:
            raise ProtocolEffectsError("protocol ontology variables are not frozen")
        if preregistration.get("no_posthoc_subgroups") is not True:
            raise ProtocolEffectsError("post-hoc subgroup policy is not frozen")
        if preregistration.get("reversal_tolerance") != 0.02:
            raise ProtocolEffectsError("reversal tolerance is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        expected = {
            "T071 model receipt": self.root / "reports/models/m1/m1_receipt.json",
            "T089 tournament config": (
                self.root / "reports/claims/tournament/tournament_config.json"
            ),
            "T091 mediation receipt": self.root / "reports/omics/mediation/mediation_receipt.json",
        }
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "protocol-effects input")
            label = _string(row.get("label"), "protocol-effects input label")
            if label not in expected:
                raise ProtocolEffectsError(f"unexpected protocol-effects input: {label}")
            path = (self.root / _string(row.get("path"), "protocol-effects input path")).resolve(
                strict=True
            )
            if path != expected[label].resolve(strict=True):
                raise ProtocolEffectsError(f"protocol-effects input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(
                row.get("sha256"), "protocol-effects input checksum"
            ):
                raise ProtocolEffectsError(f"protocol-effects input checksum differs: {label}")
            loaded[label] = _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        if set(loaded) != set(expected):
            raise ProtocolEffectsError(
                "protocol-effects inputs do not match T071/T089/T091 contract"
            )
        if loaded["T071 model receipt"].get("target_values_exposed") is not False:
            raise ProtocolEffectsError("T071 model receipt is not target-isolated")
        if loaded["T089 tournament config"].get("frozen_before_primary") is not True:
            raise ProtocolEffectsError("T089 config is not frozen")
        if loaded["T091 mediation receipt"].get("language_status") != "ASSOCIATION_ONLY":
            raise ProtocolEffectsError("T091 mediation language gate is not preserved")
        return loaded

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "study_id",
            "material_id",
            "split",
            "species",
            "biofluid",
            "assay",
            "dose_bin",
            "protocol_family",
            "comparable",
            "raw_effect",
            "adjusted_effect",
            "sample_size",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "protocol-effects row")
            if set(row) != required:
                raise ProtocolEffectsError("protocol-effects row fields do not match schema")
            row_id = _string(row.get("row_id"), "protocol-effects row ID")
            split = _string(row.get("split"), "protocol-effects split")
            if row_id in seen or split not in {"development", "validation"}:
                raise ProtocolEffectsError(
                    f"protocol-effects row identity or split invalid: {row_id}"
                )
            sample_size = int(_number(row.get("sample_size"), "protocol sample size"))
            if sample_size < 1:
                raise ProtocolEffectsError(f"protocol sample size is invalid: {row_id}")
            rows.append(
                {
                    "row_id": row_id,
                    "study_id": _string(row.get("study_id"), "protocol study ID"),
                    "material_id": _string(row.get("material_id"), "protocol material ID"),
                    "split": split,
                    "species": _string(row.get("species"), "protocol species"),
                    "biofluid": _string(row.get("biofluid"), "protocol biofluid"),
                    "assay": _string(row.get("assay"), "protocol assay"),
                    "dose_bin": _string(row.get("dose_bin"), "protocol dose bin"),
                    "protocol_family": _string(row.get("protocol_family"), "protocol family"),
                    "comparable": row.get("comparable") is True,
                    "raw_effect": _number(row.get("raw_effect"), "raw effect"),
                    "adjusted_effect": _number(row.get("adjusted_effect"), "adjusted effect"),
                    "sample_size": sample_size,
                }
            )
            seen.add(row_id)
        if not rows or not any(row["split"] == "development" for row in rows):
            raise ProtocolEffectsError("protocol-effects fixture has no development rows")
        if not any(row["split"] == "validation" for row in rows):
            raise ProtocolEffectsError("protocol-effects fixture has no validation rows")
        if not all(row["comparable"] for row in rows):
            raise ProtocolEffectsError(
                "non-comparable rows must be explicitly excluded before analysis"
            )
        return rows

    @staticmethod
    def _effect_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        raw = _mean([row["raw_effect"] for row in rows])
        adjusted = _mean([row["adjusted_effect"] for row in rows])
        return {
            "n": len(rows),
            "studies": sorted({row["study_id"] for row in rows}),
            "raw_effect": round(raw, 8),
            "adjusted_effect": round(adjusted, 8),
            "raw_sign": _sign(raw),
            "adjusted_sign": _sign(adjusted),
            "reversal": _sign(raw) != "zero"
            and _sign(adjusted) != "zero"
            and _sign(raw) != _sign(adjusted),
        }

    @staticmethod
    def _group(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[str(row[key])].append(row)
        result = []
        for value in sorted(groups):
            summary = ProtocolEffectsWorkflow._effect_summary(groups[value])
            result.append({"variable": key, "level": value, **summary})
        return result

    @staticmethod
    def _heterogeneity(groups: list[dict[str, Any]]) -> dict[str, Any]:
        effects = [float(group["adjusted_effect"]) for group in groups]
        if len(effects) < 2:
            return {"groups": len(effects), "range": 0.0, "sign_discordance": False}
        signs = {_sign(effect) for effect in effects}
        return {
            "groups": len(effects),
            "range": round(max(effects) - min(effects), 8),
            "sign_discordance": len(signs - {"zero"}) > 1,
        }

    def run(self, *, fixture: bool = True) -> ProtocolEffectsSummary:
        """Run predefined protocol corrections and reversal tests."""
        if not fixture:
            raise ProtocolEffectsError("--fixture is required for protocol effects")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        preregistration = _mapping(
            fixture_data["preregistration"], "protocol-effects preregistration"
        )
        variables = [_string(value, "protocol variable") for value in preregistration["variables"]]
        development = [row for row in rows if row["split"] == "development"]
        validation = [row for row in rows if row["split"] == "validation"]
        raw_adjusted = {
            "development": self._effect_summary(development),
            "validation": self._effect_summary(validation),
            "all": self._effect_summary(rows),
        }
        strata: dict[str, list[dict[str, Any]]] = {
            variable: self._group(rows, variable) for variable in variables
        }
        within_study = [
            {"study_id": study_id, **self._effect_summary(group)}
            for study_id, group in sorted(
                (
                    (study_id, [row for row in rows if row["study_id"] == study_id])
                    for study_id in {row["study_id"] for row in rows}
                ),
                key=lambda pair: pair[0],
            )
        ]
        reversal_tests: list[dict[str, Any]] = [
            {"scope": "within_study", "tests": within_study},
            {"scope": "aggregate", "tests": [raw_adjusted["all"]]},
        ] + [{"scope": variable, "tests": tests} for variable, tests in strata.items()]
        reversals = [
            test for block in reversal_tests for test in block["tests"] if test["reversal"]
        ]
        heterogeneity = {variable: self._heterogeneity(tests) for variable, tests in strata.items()}
        counterexamples = [
            {
                "row_id": row["row_id"],
                "study_id": row["study_id"],
                "protocol_family": row["protocol_family"],
                "raw_effect": row["raw_effect"],
                "adjusted_effect": row["adjusted_effect"],
                "reason": "no_sign_reversal",
            }
            for row in rows
            if _sign(row["raw_effect"]) == _sign(row["adjusted_effect"])
        ]
        reversal_tolerance = float(preregistration["reversal_tolerance"])
        heterogeneity_max = max(
            (float(value["range"]) for value in heterogeneity.values()), default=0.0
        )
        stable_reversal = (
            bool(reversals)
            and all(test["reversal"] for test in within_study)
            and all(test["reversal"] for tests in strata.values() for test in tests)
            and heterogeneity_max <= reversal_tolerance
        )
        universal_reversal_permitted = stable_reversal and not counterexamples
        language_status = (
            "UNIVERSAL_REVERSAL" if universal_reversal_permitted else "PROTOCOL_DEPENDENT_BOUNDARY"
        )
        language_gate = {
            "schema_version": 1,
            "status": language_status,
            "universal_reversal_permitted": universal_reversal_permitted,
            "protocol_dependence_reported": not universal_reversal_permitted,
            "posthoc_subgroups": False,
            "blocked_wording": ["universal reversal", "causal correction"],
            "allowed_wording": (
                "protocol-dependent boundary effect"
                if not universal_reversal_permitted
                else "predefined protocol reversal"
            ),
        }
        ontology = {
            "schema_version": 1,
            "variables": variables,
            "levels": {
                variable: sorted({str(row[variable]) for row in rows}) for variable in variables
            },
            "frozen_before_analysis": True,
            "no_posthoc_subgroups": True,
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                "schema_version": 1,
                "variables": variables,
                "contrast": preregistration["contrast"],
                "reversal_tolerance": reversal_tolerance,
                "heterogeneity_threshold": preregistration["heterogeneity_threshold"],
                "no_posthoc_subgroups": True,
                "frozen_before_analysis": True,
            },
            "ontology": ontology,
            "raw_adjusted": {"schema_version": 1, **raw_adjusted},
            "within_study": {"schema_version": 1, "studies": within_study},
            "strata": {"schema_version": 1, "variables": strata},
            "reversal_tests": {
                "schema_version": 1,
                "tests": reversal_tests,
                "reversals_detected": len(reversals),
                "counterexamples": counterexamples,
            },
            "heterogeneity": {"schema_version": 1, "by_variable": heterogeneity},
            "exclusions": {
                "schema_version": 1,
                "append_only": True,
                "entries": [],
                "posthoc_subgroup_exclusions": 0,
            },
            "language_gate": language_gate,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "protocol_preregistration.json",
            "ontology": self.output_root / "protocol_ontology.json",
            "raw_adjusted": self.output_root / "raw_adjusted_effects.json",
            "within_study": self.output_root / "within_study_effects.json",
            "strata": self.output_root / "protocol_strata.json",
            "reversal_tests": self.output_root / "reversal_tests.json",
            "heterogeneity": self.output_root / "heterogeneity_map.json",
            "exclusions": self.output_root / "exclusion_ledger.json",
            "language_gate": self.output_root / "language_gate.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            path.write_bytes(payload_bytes[name])
            artifact_records[name] = {
                "path": (
                    str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path)
                ),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
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
        lockbox_bytes = _canonical(lockbox)
        lockbox_path = self.output_root / "lockbox_scan.json"
        lockbox_path.write_bytes(lockbox_bytes)
        artifact_records["lockbox"] = {
            "path": (
                str(lockbox_path.relative_to(self.root))
                if lockbox_path.is_relative_to(self.root)
                else str(lockbox_path)
            ),
            "sha256": _sha256(lockbox_bytes),
            "bytes": len(lockbox_bytes),
        }
        receipt_path = self.output_root / "protocol_effects_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "rows": len(rows),
            "variables": len(variables),
            "studies": len({row["study_id"] for row in rows}),
            "raw_effect": raw_adjusted["all"]["raw_effect"],
            "adjusted_effect": raw_adjusted["all"]["adjusted_effect"],
            "reversal_tests": len(reversal_tests),
            "reversals_detected": len(reversals),
            "counterexamples": len(counterexamples),
            "heterogeneity_max": heterogeneity_max,
            "universal_reversal_permitted": universal_reversal_permitted,
            "language_status": language_status,
            "lockbox_clean": not found,
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        receipt_path.write_bytes(_canonical(receipt))
        receipt_relative = (
            str(receipt_path.relative_to(self.root))
            if receipt_path.is_relative_to(self.root)
            else str(receipt_path)
        )
        manifest = {
            "schema_version": 1,
            "workflow": "PROTOCOL_EFFECTS_REVERSAL",
            "status": receipt["status"],
            "resume_key": resume_key,
            "resume_supported": True,
            "target_values_exposed": False,
            "artifacts": {
                **artifact_records,
                "receipt": {
                    "path": receipt_relative,
                    "sha256": _sha256(receipt_path.read_bytes()),
                    "bytes": receipt_path.stat().st_size,
                },
            },
        }
        (self.output_root / "protocol_effects_manifest.json").write_bytes(_canonical(manifest))
        return ProtocolEffectsSummary(
            rows=len(rows),
            variables=len(variables),
            studies=len({row["study_id"] for row in rows}),
            raw_effect=float(raw_adjusted["all"]["raw_effect"]),
            adjusted_effect=float(raw_adjusted["all"]["adjusted_effect"]),
            reversal_tests=len(reversal_tests),
            reversals_detected=len(reversals),
            counterexamples=len(counterexamples),
            heterogeneity_max=heterogeneity_max,
            universal_reversal_permitted=universal_reversal_permitted,
            language_status=language_status,
            resumed=resumed,
            receipt_path=receipt_path,
        )
