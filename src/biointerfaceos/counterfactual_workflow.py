"""Fixture-backed counterfactual ranking and contradiction analysis."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class CounterfactualError(RuntimeError):
    """Raised when the T095 counterfactual contract is invalid."""


@dataclass(frozen=True)
class CounterfactualSummary:
    """Summary of one deterministic counterfactual run."""

    rows: int
    interventions: int
    supported: int
    rejected: int
    model_families: int
    scored: int
    abstentions: int
    rank_pairs: int
    rank_stability: float
    contradictions: int
    unresolved: int
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
        raise CounterfactualError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CounterfactualError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CounterfactualError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CounterfactualError(f"{label} must be finite")
    return result


class CounterfactualWorkflow:
    """Rank supported interventions and preserve contradictory strata."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/counterfactuals_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/counterfactuals"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "counterfactual fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CounterfactualError(f"cannot load counterfactual fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "counterfactual_ranking":
            raise CounterfactualError("counterfactual fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise CounterfactualError("counterfactual inputs/rows are invalid")
        if not isinstance(data.get("contradictions"), list) or not data["contradictions"]:
            raise CounterfactualError("counterfactual contradiction graph is empty")
        preregistration = _mapping(data.get("preregistration"), "counterfactual preregistration")
        if preregistration.get("schema_version") != 1:
            raise CounterfactualError("counterfactual preregistration schema is invalid")
        if preregistration.get("model_families") != ["linear", "protocol_adjusted"]:
            raise CounterfactualError("counterfactual model family list is not frozen")
        if preregistration.get("positivity_threshold") != 0.15:
            raise CounterfactualError("counterfactual positivity threshold is not frozen")
        if preregistration.get("ood_threshold") != 0.40:
            raise CounterfactualError("counterfactual OOD threshold is not frozen")
        if preregistration.get("disagreement_threshold") != 0.15:
            raise CounterfactualError("counterfactual disagreement threshold is not frozen")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        expected = {
            "T076 M6 receipt": self.root / "reports/models/m6/m6_receipt.json",
            "T090 functional axes receipt": (
                self.root / "reports/omics/functional_axes/functional_axes_receipt.json"
            ),
            "T091 mediation receipt": self.root / "reports/omics/mediation/mediation_receipt.json",
            "T093 symbolic laws receipt": (
                self.root / "reports/omics/symbolic_laws/symbolic_laws_receipt.json"
            ),
            "T094 protocol effects receipt": (
                self.root / "reports/omics/protocol_effects/protocol_effects_receipt.json"
            ),
        }
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "counterfactual input")
            label = _string(row.get("label"), "counterfactual input label")
            if label not in expected:
                raise CounterfactualError(f"unexpected counterfactual input: {label}")
            path = (self.root / _string(row.get("path"), "counterfactual input path")).resolve(
                strict=True
            )
            if path != expected[label].resolve(strict=True):
                raise CounterfactualError(f"counterfactual input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(
                row.get("sha256"), "counterfactual input checksum"
            ):
                raise CounterfactualError(f"counterfactual input checksum differs: {label}")
            loaded[label] = _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        if set(loaded) != set(expected):
            raise CounterfactualError(
                "counterfactual inputs do not match T076/T090/T091/T093/T094 contract"
            )
        if loaded["T076 M6 receipt"].get("causal_claim_permitted") is not False:
            raise CounterfactualError("T076 causal claim downgrade is not preserved")
        if loaded["T090 functional axes receipt"].get("candidate_axes") != 2:
            raise CounterfactualError("T090 axes are not available")
        if loaded["T091 mediation receipt"].get("language_status") != "ASSOCIATION_ONLY":
            raise CounterfactualError("T091 association-only status is not preserved")
        if loaded["T093 symbolic laws receipt"].get("status") != "VALID":
            raise CounterfactualError("T093 symbolic-law receipt is invalid")
        if (
            loaded["T094 protocol effects receipt"].get("language_status")
            != "PROTOCOL_DEPENDENT_BOUNDARY"
        ):
            raise CounterfactualError("T094 protocol boundary status is not preserved")
        return loaded

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "case_id",
            "material_id",
            "intervention_id",
            "stratum",
            "split",
            "surface_norm",
            "functional_axis",
            "positivity",
            "ood_distance",
            "model_linear",
            "model_protocol_adjusted",
            "uncertainty_linear",
            "uncertainty_protocol_adjusted",
            "target_available",
            "target_value",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "counterfactual row")
            if set(row) != required:
                raise CounterfactualError("counterfactual row fields do not match schema")
            case_id = _string(row.get("case_id"), "counterfactual case ID")
            if case_id in seen:
                raise CounterfactualError(f"duplicate counterfactual case: {case_id}")
            target_available = row.get("target_available") is True
            target_value = row.get("target_value")
            if target_available:
                target = _number(target_value, "counterfactual target")
            elif target_value is not None:
                raise CounterfactualError(f"unavailable target has a value: {case_id}")
            else:
                target = None
            rows.append(
                {
                    "case_id": case_id,
                    "material_id": _string(row.get("material_id"), "counterfactual material ID"),
                    "intervention_id": _string(
                        row.get("intervention_id"), "counterfactual intervention ID"
                    ),
                    "stratum": _string(row.get("stratum"), "counterfactual stratum"),
                    "split": _string(row.get("split"), "counterfactual split"),
                    "surface_norm": _number(row.get("surface_norm"), "counterfactual surface"),
                    "functional_axis": _number(
                        row.get("functional_axis"), "counterfactual functional axis"
                    ),
                    "positivity": row.get("positivity") is True,
                    "ood_distance": _number(row.get("ood_distance"), "counterfactual OOD distance"),
                    "model_linear": _number(row.get("model_linear"), "linear prediction"),
                    "model_protocol_adjusted": _number(
                        row.get("model_protocol_adjusted"), "protocol prediction"
                    ),
                    "uncertainty_linear": _number(
                        row.get("uncertainty_linear"), "linear uncertainty"
                    ),
                    "uncertainty_protocol_adjusted": _number(
                        row.get("uncertainty_protocol_adjusted"), "protocol uncertainty"
                    ),
                    "target_available": target_available,
                    "target_value": target,
                }
            )
            seen.add(case_id)
        if not rows or not any(row["split"] == "development" for row in rows):
            raise CounterfactualError("counterfactual fixture has no development rows")
        if not any(row["split"] == "validation" for row in rows):
            raise CounterfactualError("counterfactual fixture has no validation rows")
        return rows

    @staticmethod
    def _rank(values: dict[str, float]) -> dict[str, int]:
        ordered = sorted(values, key=lambda item: (-values[item], item))
        return {case_id: index + 1 for index, case_id in enumerate(ordered)}

    @staticmethod
    def _pair_agreement(left: dict[str, int], right: dict[str, int]) -> tuple[int, int]:
        case_ids = sorted(left)
        pairs = 0
        agreeing = 0
        for index, first in enumerate(case_ids):
            for second in case_ids[index + 1 :]:
                pairs += 1
                left_delta = left[first] - left[second]
                right_delta = right[first] - right[second]
                agreeing += int(left_delta * right_delta > 0)
        return pairs, agreeing

    def run(self, *, fixture: bool = True) -> CounterfactualSummary:
        """Rank supported counterfactuals and preserve contradiction edges."""
        if not fixture:
            raise CounterfactualError("--fixture is required for counterfactuals")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        preregistration = _mapping(
            fixture_data["preregistration"], "counterfactual preregistration"
        )
        positivity_threshold = float(preregistration["positivity_threshold"])
        ood_threshold = float(preregistration["ood_threshold"])
        disagreement_threshold = float(preregistration["disagreement_threshold"])
        supported: list[dict[str, Any]] = []
        exclusions: list[dict[str, Any]] = []
        abstentions: list[dict[str, Any]] = []
        for row in rows:
            if not row["positivity"]:
                exclusions.append(
                    {
                        "case_id": row["case_id"],
                        "reason": "positivity_failed",
                        "threshold": positivity_threshold,
                    }
                )
                abstentions.append({"case_id": row["case_id"], "reason": "positivity_failed"})
                continue
            if row["ood_distance"] > ood_threshold:
                exclusions.append(
                    {
                        "case_id": row["case_id"],
                        "reason": "ood_distance_exceeded",
                        "threshold": ood_threshold,
                    }
                )
                abstentions.append({"case_id": row["case_id"], "reason": "ood_distance_exceeded"})
                continue
            disagreement = abs(row["model_linear"] - row["model_protocol_adjusted"])
            row_with_gate = dict(row, model_disagreement=round(disagreement, 8))
            if disagreement > disagreement_threshold:
                exclusions.append(
                    {
                        "case_id": row["case_id"],
                        "reason": "model_disagreement_exceeded",
                        "threshold": disagreement_threshold,
                        "disagreement": round(disagreement, 8),
                    }
                )
                abstentions.append(
                    {
                        "case_id": row["case_id"],
                        "reason": "model_disagreement_exceeded",
                        "threshold": disagreement_threshold,
                        "disagreement": round(disagreement, 8),
                    }
                )
                continue
            supported.append(row_with_gate)
        models = ["linear", "protocol_adjusted"]
        rankings: dict[str, dict[str, Any]] = {}
        rank_maps: dict[str, dict[str, int]] = {}
        for model in models:
            prediction_key = "model_linear" if model == "linear" else "model_protocol_adjusted"
            uncertainty_key = (
                "uncertainty_linear" if model == "linear" else "uncertainty_protocol_adjusted"
            )
            predictions = {row["case_id"]: row[prediction_key] for row in supported}
            rank_map = self._rank(predictions)
            rank_maps[model] = rank_map
            rankings[model] = {
                "ranked_cases": [
                    {
                        "case_id": case_id,
                        "rank": rank_map[case_id],
                        "prediction": round(predictions[case_id], 8),
                        "uncertainty": round(
                            next(
                                row[uncertainty_key]
                                for row in supported
                                if row["case_id"] == case_id
                            ),
                            8,
                        ),
                    }
                    for case_id in sorted(rank_map, key=lambda item: rank_map[item])
                ],
                "supported_only": True,
            }
        rank_pairs, agreeing = self._pair_agreement(
            rank_maps["linear"], rank_maps["protocol_adjusted"]
        )
        rank_stability = round(agreeing / rank_pairs, 8) if rank_pairs else 1.0
        contradiction_rows: list[dict[str, Any]] = []
        category_counts: dict[str, int] = {}
        for value in fixture_data["contradictions"]:
            contradiction = _mapping(value, "contradiction edge")
            edge_id = _string(contradiction.get("edge_id"), "contradiction edge ID")
            category = _string(contradiction.get("category"), "contradiction category")
            if category not in {"resolved_by_protocol", "model_disagreement", "unresolved"}:
                raise CounterfactualError(f"unsupported contradiction category: {category}")
            record = {
                "edge_id": edge_id,
                "stratum": _string(contradiction.get("stratum"), "contradiction stratum"),
                "claim_a": _string(contradiction.get("claim_a"), "claim A"),
                "claim_b": _string(contradiction.get("claim_b"), "claim B"),
                "category": category,
                "resolution": _string(contradiction.get("resolution"), "contradiction resolution"),
                "evidence_links": contradiction.get("evidence_links"),
            }
            if not isinstance(record["evidence_links"], list) or not record["evidence_links"]:
                raise CounterfactualError(f"contradiction evidence is missing: {edge_id}")
            contradiction_rows.append(record)
            category_counts[category] = category_counts.get(category, 0) + 1
        unresolved = category_counts.get("unresolved", 0)
        language_gate = {
            "schema_version": 1,
            "status": (
                "MODEL_BASED_HYPOTHESIS" if abstentions or unresolved else "SUPPORTED_RANKING"
            ),
            "universal_ranking_permitted": not (abstentions or unresolved),
            "abstention_required": bool(abstentions),
            "unresolved_contradictions": unresolved,
            "allowed_wording": "model-based hypotheses with supported-scope ranking",
            "blocked_wording": ["universal ranking", "causal intervention effect"],
        }
        raw_payloads: dict[str, Any] = {
            "preregistration": {
                "schema_version": 1,
                "interventions": preregistration["interventions"],
                "admissible_ranges": preregistration["admissible_ranges"],
                "model_families": models,
                "positivity_threshold": positivity_threshold,
                "ood_threshold": ood_threshold,
                "disagreement_threshold": disagreement_threshold,
                "frozen_before_calculation": True,
            },
            "intervention_audit": {
                "schema_version": 1,
                "rows": len(rows),
                "supported": len(supported),
                "rejected": exclusions,
                "supported_only_predictions": True,
            },
            "predictions": {
                "schema_version": 1,
                "models": rankings,
                "scored_cases": len(supported),
                "target_values_exposed": False,
            },
            "rankings": {
                "schema_version": 1,
                "models": models,
                "rank_pairs": rank_pairs,
                "agreeing_pairs": agreeing,
                "rank_stability": rank_stability,
                "stable": rank_stability >= 0.75 and not abstentions,
            },
            "uncertainty": {
                "schema_version": 1,
                "model_disagreement_threshold": disagreement_threshold,
                "abstentions": len(abstentions),
                "supported_uncertainty_reported": True,
            },
            "abstentions": {
                "schema_version": 1,
                "entries": abstentions,
                "count": len(abstentions),
                "unsupported_interventions_excluded": True,
            },
            "contradictions": {
                "schema_version": 1,
                "edges": contradiction_rows,
                "category_counts": category_counts,
                "unresolved": unresolved,
                "all_edges_preserved": True,
            },
            "language_gate": language_gate,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "preregistration": self.output_root / "counterfactual_preregistration.json",
            "intervention_audit": self.output_root / "intervention_audit.json",
            "predictions": self.output_root / "counterfactual_predictions.json",
            "rankings": self.output_root / "counterfactual_rankings.json",
            "uncertainty": self.output_root / "ranking_uncertainty.json",
            "abstentions": self.output_root / "abstention_ledger.json",
            "contradictions": self.output_root / "contradiction_graph.json",
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
        receipt_path = self.output_root / "counterfactuals_receipt.json"
        resumed = int(receipt_path.exists())
        receipt = {
            "schema_version": 1,
            "status": "VALID" if not found else "INVALID",
            "fixture": True,
            "rows": len(rows),
            "interventions": len(preregistration["interventions"]),
            "supported": len(supported),
            "rejected": len(exclusions),
            "model_families": len(models),
            "scored": len(supported),
            "abstentions": len(abstentions),
            "rank_pairs": rank_pairs,
            "rank_stability": rank_stability,
            "contradictions": len(contradiction_rows),
            "unresolved": unresolved,
            "target_values_exposed": False,
            "lockbox_clean": not found,
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
            "workflow": "COUNTERFACTUAL_RANKING_CONTRADICTIONS",
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
        (self.output_root / "counterfactuals_manifest.json").write_bytes(_canonical(manifest))
        return CounterfactualSummary(
            rows=len(rows),
            interventions=len(preregistration["interventions"]),
            supported=len(supported),
            rejected=len(exclusions),
            model_families=len(models),
            scored=len(supported),
            abstentions=len(abstentions),
            rank_pairs=rank_pairs,
            rank_stability=rank_stability,
            contradictions=len(contradiction_rows),
            unresolved=unresolved,
            resumed=resumed,
            receipt_path=receipt_path,
        )
