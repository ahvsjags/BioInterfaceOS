"""Fixture-backed target-corona conditional generative design workflow."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TargetCoronaGenerativeError(RuntimeError):
    """Raised when the T097 generative-design contract is invalid."""


@dataclass(frozen=True)
class TargetCoronaGenerativeSummary:
    """Summary of one gated conditional design comparison."""

    rows: int
    groups: int
    heldout: int
    sufficiency_passed: bool
    generator_attempted: bool
    baseline_validity: float
    generator_validity: float
    novelty_gain: float
    pareto_gain: int
    ood_uncertainty_delta: float
    ablations: int
    selected_method: str
    fallback: int
    abstentions: int
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
        raise TargetCoronaGenerativeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TargetCoronaGenerativeError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TargetCoronaGenerativeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise TargetCoronaGenerativeError(f"{label} must be finite")
    return result


class TargetCoronaGenerativeWorkflow:
    """Gate a bounded conditional generator and compare it to the T096 baseline."""

    METHODS = ("bo_style_baseline", "conditional_generator")
    ABLATIONS = (
        "without_conditioning",
        "without_uncertainty_penalty",
        "without_support_restriction",
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/design/target_corona_generative_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/design/generative"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "generative-design fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TargetCoronaGenerativeError(f"cannot load generative fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != (
            "target_corona_generative_design"
        ):
            raise TargetCoronaGenerativeError("generative fixture schema or mode is invalid")
        for key in ("inputs", "preregistration", "support_rows", "proposals", "ablations"):
            if key not in data:
                raise TargetCoronaGenerativeError(f"generative fixture is missing {key}")
        if not isinstance(data["inputs"], list) or not isinstance(data["support_rows"], list):
            raise TargetCoronaGenerativeError("generative fixture inputs/support rows are invalid")
        if not isinstance(data["proposals"], list) or not isinstance(data["ablations"], list):
            raise TargetCoronaGenerativeError("generative fixture proposals/ablations are invalid")
        preregistration = _mapping(data["preregistration"], "generative preregistration")
        if preregistration.get("schema_version") != 1:
            raise TargetCoronaGenerativeError("generative preregistration schema is invalid")
        if preregistration.get("methods") != list(self.METHODS):
            raise TargetCoronaGenerativeError("generative method list is not frozen")
        if preregistration.get("ablations") != list(self.ABLATIONS):
            raise TargetCoronaGenerativeError("generative ablation list is not frozen")
        if preregistration.get("target_values_exposed") is not False:
            raise TargetCoronaGenerativeError("generative target values must remain hidden")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected: dict[str, tuple[Path, str]] = {
            "T079 multimodal receipt": (
                self.root / "reports/models/multimodal/multimodal_receipt.json",
                "abcee7f3ba8daf2d53f112cd4e3fb0a0147b1c5e269f243c3fbd61e27733292a",
            ),
            "T096 constrained design receipt": (
                self.root / "reports/design/baseline/design_baseline_receipt.json",
                "e6fc606f63b278246e4bb5c150c139fd5b389d6a15016d7f61d5365a9a551bee",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "generative input")
            label = _string(row.get("label"), "generative input label")
            if label not in expected:
                raise TargetCoronaGenerativeError(f"unexpected generative input: {label}")
            path, checksum = expected[label]
            declared_path = (self.root / _string(row.get("path"), "generative input path")).resolve(
                strict=True
            )
            if declared_path != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise TargetCoronaGenerativeError(
                    f"generative input path/checksum differs: {label}"
                )
            payload = _mapping(json.loads(path.read_text(encoding="utf-8")), f"{label} payload")
            if _sha256(path.read_bytes()) != checksum or payload.get("status") != "VALID":
                raise TargetCoronaGenerativeError(f"{label} is not a valid frozen input")
            seen.add(label)
        if seen != set(expected):
            raise TargetCoronaGenerativeError("generative inputs do not match T079/T096 contract")

    @staticmethod
    def _preregistration(fixture: Mapping[str, Any]) -> dict[str, Any]:
        preregistration = _mapping(fixture["preregistration"], "generative preregistration")
        numeric = (
            "min_independent_groups",
            "min_train_rows",
            "min_heldout_rows",
            "min_target_coverage",
            "min_support_density",
            "support_distance_threshold",
            "validity_margin",
            "novelty_margin",
            "pareto_margin",
            "ood_uncertainty_tolerance",
            "budget",
            "seed",
        )
        for key in numeric:
            _number(preregistration.get(key), f"generative preregistration {key}")
        if preregistration["budget"] != 6 or preregistration["seed"] != 97:
            raise TargetCoronaGenerativeError("generative budget/seed is not frozen")
        return preregistration

    @classmethod
    def _support_audit(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        required = {"row_id", "group_id", "split", "target_covered", "support_distance"}
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["support_rows"]:
            source = _mapping(value, "support row")
            if set(source) != required:
                raise TargetCoronaGenerativeError("support-row fields do not match schema")
            row_id = _string(source.get("row_id"), "support row ID")
            if row_id in seen:
                raise TargetCoronaGenerativeError(f"duplicate support row: {row_id}")
            split = _string(source.get("split"), "support split")
            if split not in {"train", "heldout"}:
                raise TargetCoronaGenerativeError(f"invalid support split: {split}")
            if not isinstance(source.get("target_covered"), bool):
                raise TargetCoronaGenerativeError("target coverage flag must be boolean")
            rows.append(
                {
                    "row_id": row_id,
                    "group_id": _string(source.get("group_id"), "support group ID"),
                    "split": split,
                    "target_covered": source["target_covered"],
                    "support_distance": _number(source.get("support_distance"), "support distance"),
                }
            )
            seen.add(row_id)
        train = [row for row in rows if row["split"] == "train"]
        heldout = [row for row in rows if row["split"] == "heldout"]
        groups = {row["group_id"] for row in train}
        coverage = sum(row["target_covered"] for row in train) / max(len(train), 1)
        threshold = float(preregistration["support_distance_threshold"])
        density = sum(row["support_distance"] <= threshold for row in train) / max(len(train), 1)
        checks = {
            "independent_groups": len(groups),
            "train_rows": len(train),
            "heldout_rows": len(heldout),
            "target_coverage": round(coverage, 8),
            "support_density": round(density, 8),
            "minimums": {
                "independent_groups": preregistration["min_independent_groups"],
                "train_rows": preregistration["min_train_rows"],
                "heldout_rows": preregistration["min_heldout_rows"],
                "target_coverage": preregistration["min_target_coverage"],
                "support_density": preregistration["min_support_density"],
            },
        }
        checks["passed"] = (
            checks["independent_groups"] >= checks["minimums"]["independent_groups"]
            and checks["train_rows"] >= checks["minimums"]["train_rows"]
            and checks["heldout_rows"] >= checks["minimums"]["heldout_rows"]
            and checks["target_coverage"] >= checks["minimums"]["target_coverage"]
            and checks["support_density"] >= checks["minimums"]["support_density"]
        )
        checks["target_values_exposed"] = False
        return checks, rows

    @classmethod
    def _proposals(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        required = {
            "proposal_id",
            "method",
            "valid",
            "ood",
            "uncertainty",
            "novelty",
            "pareto_member",
            "abstain",
        }
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        allowed = set(cls.METHODS) | set(cls.ABLATIONS)
        for value in fixture["proposals"]:
            source = _mapping(value, "design proposal")
            if set(source) != required:
                raise TargetCoronaGenerativeError("design proposal fields do not match schema")
            proposal_id = _string(source.get("proposal_id"), "proposal ID")
            method = _string(source.get("method"), "proposal method")
            if proposal_id in seen or method not in allowed:
                raise TargetCoronaGenerativeError("design proposal ID/method is invalid")
            for key in ("valid", "ood", "pareto_member", "abstain"):
                if not isinstance(source.get(key), bool):
                    raise TargetCoronaGenerativeError(f"proposal {key} flag is invalid")
            if source["ood"] and not source["abstain"]:
                raise TargetCoronaGenerativeError("OOD proposal must abstain")
            records.append(
                {
                    "proposal_id": proposal_id,
                    "method": method,
                    "valid": source["valid"],
                    "ood": source["ood"],
                    "uncertainty": _number(source.get("uncertainty"), "proposal uncertainty"),
                    "novelty": _number(source.get("novelty"), "proposal novelty"),
                    "pareto_member": source["pareto_member"],
                    "abstain": source["abstain"],
                }
            )
            seen.add(proposal_id)
        budget = int(preregistration["budget"])
        for method in cls.METHODS:
            if len([row for row in records if row["method"] == method]) != budget:
                raise TargetCoronaGenerativeError(f"{method} proposal budget is not frozen")
        return records

    @staticmethod
    def _method_metrics(records: list[dict[str, Any]], method: str) -> dict[str, float | int]:
        selected = [row for row in records if row["method"] == method]
        if not selected:
            return {
                "proposals": 0,
                "validity_rate": 0.0,
                "novelty_score": 0.0,
                "pareto_members": 0,
                "ood_uncertainty": 0.0,
                "abstentions": 0,
            }
        valid = [row for row in selected if row["valid"]]
        supported = [row for row in valid if not row["abstain"]]
        ood = [row for row in selected if row["ood"]]
        return {
            "proposals": len(selected),
            "validity_rate": round(len(valid) / len(selected), 8),
            "novelty_score": round(
                sum(row["novelty"] for row in supported) / max(len(supported), 1), 8
            ),
            "pareto_members": sum(row["pareto_member"] for row in supported),
            "ood_uncertainty": round(sum(row["uncertainty"] for row in ood) / max(len(ood), 1), 8),
            "abstentions": sum(row["abstain"] for row in selected),
        }

    @classmethod
    def _ablations(
        cls, fixture: Mapping[str, Any], preregistration: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        required = {
            "name",
            "validity_rate",
            "novelty_score",
            "pareto_members",
            "ood_uncertainty",
            "complete",
        }
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["ablations"]:
            source = _mapping(value, "design ablation")
            if set(source) != required:
                raise TargetCoronaGenerativeError("ablation fields do not match schema")
            name = _string(source.get("name"), "ablation name")
            if name in seen or name not in cls.ABLATIONS:
                raise TargetCoronaGenerativeError("ablation name is invalid or duplicated")
            if source.get("complete") is not True:
                raise TargetCoronaGenerativeError(f"ablation is incomplete: {name}")
            records.append(
                {
                    "name": name,
                    "validity_rate": round(
                        _number(source.get("validity_rate"), "ablation validity"), 8
                    ),
                    "novelty_score": round(
                        _number(source.get("novelty_score"), "ablation novelty"), 8
                    ),
                    "pareto_members": int(
                        _number(source.get("pareto_members"), "ablation Pareto members")
                    ),
                    "ood_uncertainty": round(
                        _number(source.get("ood_uncertainty"), "ablation OOD uncertainty"), 8
                    ),
                    "complete": True,
                }
            )
            seen.add(name)
        if seen != set(cls.ABLATIONS):
            raise TargetCoronaGenerativeError("ablation matrix is incomplete")
        return sorted(records, key=lambda row: row["name"])

    def run(self, *, fixture: bool = True) -> TargetCoronaGenerativeSummary:
        """Run the sufficiency-gated conditional generator comparison."""
        if not fixture:
            raise TargetCoronaGenerativeError("--fixture is required for generative design")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        preregistration = self._preregistration(fixture_data)
        sufficiency, support_rows = self._support_audit(fixture_data, preregistration)
        proposals = self._proposals(fixture_data, preregistration)
        ablations = self._ablations(fixture_data, preregistration)
        baseline = self._method_metrics(proposals, "bo_style_baseline")
        generator = self._method_metrics(proposals, "conditional_generator")
        abstentions = [row for row in proposals if row["abstain"] and row["method"] in self.METHODS]
        generator_attempted = bool(sufficiency["passed"])
        validity_margin = float(preregistration["validity_margin"])
        novelty_margin = float(preregistration["novelty_margin"])
        pareto_margin = int(preregistration["pareto_margin"])
        ood_tolerance = float(preregistration["ood_uncertainty_tolerance"])
        novelty_gain = round(
            float(generator["novelty_score"]) - float(baseline["novelty_score"]), 8
        )
        pareto_gain = int(generator["pareto_members"]) - int(baseline["pareto_members"])
        ood_delta = round(
            float(generator["ood_uncertainty"]) - float(baseline["ood_uncertainty"]), 8
        )
        generator_beats = (
            generator_attempted
            and float(generator["validity_rate"])
            >= float(baseline["validity_rate"]) + validity_margin
            and novelty_gain >= novelty_margin
            and pareto_gain >= pareto_margin
            and ood_delta <= ood_tolerance
        )
        selected_method = "conditional_generator" if generator_beats else "bo_style_baseline"
        fallback = int(not generator_beats)
        if not generator_attempted:
            fallback = 1
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
                "frozen_before_generation": True,
                "target_values_exposed": False,
            },
            "sufficiency": sufficiency,
            "proposals": {
                "schema_version": 1,
                "rows": proposals,
                "target_values_exposed": False,
            },
            "comparison": {
                "schema_version": 1,
                "baseline": baseline,
                "generator": generator,
                "generator_attempted": generator_attempted,
                "generator_beats_baseline": generator_beats,
                "validity_margin": validity_margin,
                "novelty_gain": novelty_gain,
                "pareto_gain": pareto_gain,
                "ood_uncertainty_delta": ood_delta,
                "ood_uncertainty_tolerance": ood_tolerance,
                "selected_method": selected_method,
            },
            "uncertainty": {
                "schema_version": 1,
                "ood_uncertainty_delta": ood_delta,
                "tolerance": ood_tolerance,
                "abstentions": abstentions,
                "abstention_count": len(abstentions),
                "ood_excluded_from_supported_selection": True,
            },
            "ablations": {"schema_version": 1, "rows": ablations, "complete": True},
            "failures": {
                "schema_version": 1,
                "status": "VALID" if not found else "INVALID",
                "failures": [] if generator_attempted else ["data_sufficiency_failed"],
                "fallback": bool(fallback),
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "generative_preregistration.json",
            "sufficiency": self.output_root / "sufficiency_audit.json",
            "proposals": self.output_root / "proposal_ledger.json",
            "comparison": self.output_root / "validity_novelty_pareto.json",
            "uncertainty": self.output_root / "uncertainty_abstentions.json",
            "ablations": self.output_root / "ablation_matrix.json",
            "failures": self.output_root / "failure_ledger.json",
        }
        artifact_records: dict[str, dict[str, Any]] = {}
        for name, path in paths.items():
            payload = _canonical(raw_payloads[name])
            path.write_bytes(payload)
            artifact_records[name] = {
                "path": (
                    str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path)
                ),
                "sha256": _sha256(payload),
                "bytes": len(payload),
            }
        lockbox_path = self.output_root / "lockbox_scan.json"
        lockbox_bytes = _canonical(lockbox)
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
        receipt_path = self.output_root / "target_corona_generative_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "rows": len(support_rows),
            "groups": sufficiency["independent_groups"],
            "heldout": sufficiency["heldout_rows"],
            "sufficiency_passed": bool(sufficiency["passed"]),
            "generator_attempted": generator_attempted,
            "baseline_validity": baseline["validity_rate"],
            "generator_validity": generator["validity_rate"],
            "novelty_gain": novelty_gain,
            "pareto_gain": pareto_gain,
            "ood_uncertainty_delta": ood_delta,
            "ablations": len(ablations),
            "selected_method": selected_method,
            "fallback": bool(fallback),
            "abstentions": len(abstentions),
            "target_values_exposed": False,
            "lockbox_clean": not found,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        receipt_bytes = _canonical(receipt)
        receipt_path.write_bytes(receipt_bytes)
        manifest = {
            "schema_version": 1,
            "workflow": "TARGET_CORONA_CONDITIONAL_GENERATIVE_DESIGN",
            "status": receipt["status"],
            "resume_key": resume_key,
            "resume_supported": True,
            "target_values_exposed": False,
            "artifacts": {
                **artifact_records,
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
        (self.output_root / "target_corona_generative_manifest.json").write_bytes(
            _canonical(manifest)
        )
        return TargetCoronaGenerativeSummary(
            rows=len(support_rows),
            groups=sufficiency["independent_groups"],
            heldout=sufficiency["heldout_rows"],
            sufficiency_passed=bool(sufficiency["passed"]),
            generator_attempted=generator_attempted,
            baseline_validity=float(baseline["validity_rate"]),
            generator_validity=float(generator["validity_rate"]),
            novelty_gain=novelty_gain,
            pareto_gain=pareto_gain,
            ood_uncertainty_delta=ood_delta,
            ablations=len(ablations),
            selected_method=selected_method,
            fallback=fallback,
            abstentions=len(abstentions),
            resumed=resumed,
            receipt_path=receipt_path,
        )
