"""Generate an evidence-linked Paper B method manuscript."""

# The generated manuscript text is kept as readable prose literals.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.evidence_semantics import (
    AllowedClaimLevel,
    EvidenceClass,
    EvidenceSemanticsError,
    metadata_for,
    require_metadata,
)


class PaperBError(RuntimeError):
    """Raised when the Paper B evidence contract is invalid."""


@dataclass(frozen=True)
class PaperBSummary:
    """Summary of one deterministic Paper B draft generation."""

    release_id: str
    data_layers: int
    model_layers: int
    ablations: int
    ood_rows: int
    claims: int
    tables: int
    figures: int
    evidence_inputs: int
    style_passed: bool
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperBError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperBError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PaperBError(f"{label} must be numeric")
    return float(value)


class PaperBWorkflow:
    """Freeze method evidence and generate a manuscript without protected results."""

    REQUIRED_INPUTS = {
        "data model release manifest",
        "data model freeze manifest",
        "data model freeze receipt",
        "data model card",
        "T088 agent evidence report",
        "ablation paired effects",
        "ablation calibration OOD",
        "ablation claim gate",
        "ablation receipt",
        "ablation manifest",
        "OOD primary metrics",
        "OOD sensitivity report",
        "OOD claim gate",
        "OOD receipt",
        "OOD manifest",
    }

    BANNED_TERMS = (
        "novel",
        "significant",
        "substantial",
        "impressive",
        "promising",
        "comprehensive",
        "state-of-the-art",
        "utilize",
        "leverage",
        "in this paper, we",
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/manuscripts/paper_b_fixture.json"
        self.output_root = output_root or self.root / "release/manuscripts/paper_b"

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise PaperBError(f"{label} escaped repository")
        return path

    def _json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PaperBError(f"cannot load {label}: {exc}") from exc

    def _fixture(self) -> dict[str, Any]:
        fixture = self._json(self.fixture_path, "Paper B fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "paper_b_method_manuscript":
            raise PaperBError("Paper B fixture schema or mode is invalid")
        try:
            evidence_class, claim_level = require_metadata(fixture, "Paper B fixture")
        except EvidenceSemanticsError as exc:
            raise PaperBError(str(exc)) from exc
        if evidence_class is not EvidenceClass.FIXTURE_TEST or claim_level is not AllowedClaimLevel.CONTRACT_TEST:
            raise PaperBError("Paper B fixture must remain contract-only")
        inputs = fixture.get("inputs")
        if not isinstance(inputs, list) or {row.get("label") for row in inputs} != self.REQUIRED_INPUTS:
            raise PaperBError("Paper B input set does not match the evidence contract")
        return fixture

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        loaded: dict[str, Any] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "Paper B input")
            label = _string(row.get("label"), "Paper B input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            if _sha256(raw) != _string(row.get("sha256"), f"{label} checksum"):
                raise PaperBError(f"input checksum differs: {label}")
            kind = _string(row.get("kind"), f"{label} kind")
            if kind == "json":
                loaded[label] = self._json(path, label)
            elif kind == "text":
                loaded[label] = raw.decode("utf-8")
            else:
                raise PaperBError(f"unsupported input kind: {label}")
        return loaded

    @staticmethod
    def _agent_metrics(text: str) -> dict[str, Any]:
        match = re.search(
            r"AGENT_BENCHMARK_VALID tasks=(\d+) modes=(\d+) completion=([0-9.]+) "
            r"correctness=([0-9.]+) evidence=([0-9.]+) schema=([0-9.]+) "
            r"safety=([0-9.]+) reproducibility=([0-9.]+) failures=(\d+) "
            r"selected_mode=([a-z_]+)",
            text,
        )
        if match is None:
            raise PaperBError("T088 agent evidence line is missing")
        values = match.groups()
        return {
            "tasks": int(values[0]),
            "modes": int(values[1]),
            "completion": float(values[2]),
            "correctness": float(values[3]),
            "evidence": float(values[4]),
            "schema": float(values[5]),
            "safety": float(values[6]),
            "reproducibility": float(values[7]),
            "failures": int(values[8]),
            "selected_mode": values[9],
        }

    @classmethod
    def _validate_inputs(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        release = _mapping(data["data model release manifest"], "data model release manifest")
        if (
            release.get("status") != "FROZEN_DEV"
            or release.get("immutable") is not True
            or release.get("target_values_exposed") is not False
            or release.get("release_id") != "bioif-data-model-dev-v1.0.0"
        ):
            raise PaperBError("data/model release boundary is invalid")
        if release.get("robustness", {}).get("critical_leaks") != 0:
            raise PaperBError("data/model release retains critical leakage")
        freeze = _mapping(data["data model freeze manifest"], "data model freeze manifest")
        receipt = _mapping(data["data model freeze receipt"], "data model freeze receipt")
        if (
            freeze.get("status") != "FROZEN_DEV"
            or receipt.get("status") != "VALID"
            or freeze.get("target_values_exposed") is not False
            or receipt.get("target_values_exposed") is not False
        ):
            raise PaperBError("data/model freeze evidence is invalid")
        card = data["data model card"]
        if not isinstance(card, str) or "analysis-only" not in card or "Locked targets are not included" not in card:
            raise PaperBError("data/model card licensing boundary is missing")
        agent = cls._agent_metrics(_string(data["T088 agent evidence report"], "T088 evidence"))
        if agent["tasks"] != 7 or agent["modes"] != 3 or agent["selected_mode"] != "single_agent":
            raise PaperBError("agent evidence selection differs from T088")
        ablation_gate = _mapping(data["ablation claim gate"], "ablation claim gate")
        if (
            ablation_gate.get("status") != "PASS"
            or ablation_gate.get("all_declared_ablations_available") is not True
            or ablation_gate.get("same_budget") is not True
            or ablation_gate.get("same_splits") is not True
            or ablation_gate.get("claim_blocks") != 0
        ):
            raise PaperBError("ablation claim gate is invalid")
        paired = _mapping(data["ablation paired effects"], "ablation paired effects")
        comparisons = _mapping(paired.get("comparisons"), "ablation comparisons")
        if len(comparisons) != 5 or any(
            _mapping(row, "ablation comparison").get("rows") != 4 for row in comparisons.values()
        ):
            raise PaperBError("ablation comparison count or paired rows differ")
        calibration = _mapping(data["ablation calibration OOD"], "ablation calibration OOD")
        if len(_mapping(calibration.get("records"), "ablation calibration records")) != 5:
            raise PaperBError("ablation calibration record count differs")
        ood_gate = _mapping(data["OOD claim gate"], "OOD claim gate")
        if ood_gate.get("status") != "NARROWED_BY_OOD" or ood_gate.get("low_n_groups") != 6:
            raise PaperBError("OOD claim gate is not narrowed as required")
        primary = _mapping(data["OOD primary metrics"], "OOD primary metrics")
        rows = primary.get("rows")
        if not isinstance(rows, list) or len(rows) != 12:
            raise PaperBError("OOD primary row count differs")
        dimensions = {row.get("dimension") for row in rows}
        if dimensions != {"study", "lab", "family", "species", "biofluid", "time"}:
            raise PaperBError("OOD dimensions differ")
        if any(row.get("key_source") != "pre_outcome_group_key" for row in rows):
            raise PaperBError("OOD group key is not outcome-independent")
        sensitivity = _mapping(data["OOD sensitivity report"], "OOD sensitivity report")
        if len(sensitivity.get("rows", [])) != 3:
            raise PaperBError("OOD sensitivity record count differs")
        return {
            "release": release,
            "agent": agent,
            "comparisons": comparisons,
            "calibration": calibration,
            "primary": primary,
            "sensitivity": sensitivity,
        }

    @staticmethod
    def _style_audit(text: str) -> dict[str, Any]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        lower = text.lower()
        banned_hits = sorted({term for term in PaperBWorkflow.BANNED_TERMS if term in lower})
        lengths = [len(re.findall(r"\b[\w'-]+\b", sentence)) for sentence in sentences]
        overlong = sum(length > 40 for length in lengths)
        return {
            "rule_set": "paper-writing-skill-v1",
            "sentence_count": len(sentences),
            "max_sentence_words": max(lengths, default=0),
            "over_40_word_sentences": overlong,
            "banned_terms": banned_hits,
            "throat_clearing_hits": sum(
                phrase in lower for phrase in ("in order to", "it should be noted", "note that")
            ),
            "status": "PASS" if not banned_hits and overlong == 0 else "FAIL",
        }

    @staticmethod
    def _tables(validated: Mapping[str, Any]) -> dict[str, Any]:
        release = validated["release"]
        comparisons = validated["comparisons"]
        calibration = validated["calibration"]
        primary = validated["primary"]
        sensitivity = validated["sensitivity"]
        release_rows = [
            {"measure": "silver_tables", "value": release["data_layers"]["silver_tables"]},
            {"measure": "gold_auto_rows", "value": release["data_layers"]["gold_auto_rows"]},
            {"measure": "uncertainty_model", "value": release["model_layers"]["uncertainty"]},
            {"measure": "multimodal_model", "value": release["model_layers"]["multimodal"]},
            {"measure": "frozen_thresholds", "value": len(release["thresholds"])},
            {"measure": "dependency_entries", "value": len(release["dependencies"])},
        ]
        ablation_rows = []
        for name in sorted(comparisons):
            row = _mapping(comparisons[name], f"ablation {name}")
            cal = _mapping(calibration["records"][name], f"calibration {name}")
            ablation_rows.append(
                {
                    "module": name,
                    "rows": row["rows"],
                    "budget": row["budget"],
                    "effect_mean": _number(row["effect_mean"], f"{name} effect"),
                    "calibration_gain": _number(cal["calibration_gain"], f"{name} calibration"),
                    "ood_rmse_gain": _number(cal["ood_rmse_gain"], f"{name} OOD"),
                }
            )
        ood_rows = []
        for row in primary["rows"]:
            source = _mapping(row, "OOD row")
            ood_rows.append(
                {
                    "dimension": source["dimension"],
                    "group_id": source["group_id"],
                    "n": source["n"],
                    "coverage": source["coverage"],
                    "calibration_error": source["calibration_error"],
                    "selective_risk": source["selective_risk"],
                    "ood": source["ood"],
                }
            )
        agent = validated["agent"]
        return {
            "release_boundary": {
                "schema_version": 1,
                "title": "Frozen data/model method boundary",
                "rows": release_rows,
            },
            "ablation_results": {
                "schema_version": 1,
                "title": "Paired module ablation results",
                "rows": ablation_rows,
            },
            "ood_group_results": {
                "schema_version": 1,
                "title": "Outcome-independent OOD groups",
                "rows": ood_rows,
            },
            "sensitivity_results": {
                "schema_version": 1,
                "title": "OOD sensitivity scenarios",
                "rows": sensitivity["rows"],
            },
            "agent_results": {"schema_version": 1, "title": "Scientific-agent evaluation", **agent},
            "method_policy": {
                "schema_version": 1,
                "title": "Method policies and gates",
                "rows": [
                    {"policy": "ood_claim_status", "value": primary["claim_status"]},
                    {"policy": "low_n_groups", "value": sum(1 for row in ood_rows if row["ood"])},
                    {"policy": "ablation_missing_nonessential", "value": 1},
                    {"policy": "ablation_claim_blocks", "value": 0},
                    {"policy": "protected_results_accessed", "value": False},
                ],
            },
        }

    @staticmethod
    def _draft(validated: Mapping[str, Any], tables: Mapping[str, Any]) -> tuple[str, str]:
        release = validated["release"]
        agent = validated["agent"]
        comparisons = tables["ablation_results"]["rows"]
        primary = validated["primary"]
        sensitivity = validated["sensitivity"]["rows"]
        best = max(comparisons, key=lambda row: row["effect_mean"])
        average_effect = sum(row["effect_mean"] for row in comparisons) / len(comparisons)
        low_n = sum(1 for row in primary["rows"] if row["ood"])
        draft_0 = (
            "# Draft 0 method framing\n\n"
            "The method is framed as a bounded evidence workflow. "
            "Its release, uncertainty, ablation, and OOD policies are explicit before interpretation.\n"
        )
        manuscript = f"""# A bounded evidence workflow for multimodal scientific interface modeling

## Abstract

This method paper defines a reproducible workflow for scientific interface modeling. The development release contains {release["data_layers"]["silver_tables"]} Silver tables and {release["data_layers"]["gold_auto_rows"]} admitted Gold-auto rows. It selects the {release["model_layers"]["uncertainty"]} uncertainty policy and the {release["model_layers"]["multimodal"]} multimodal representation. Five paired module ablations yield a mean full-minus-ablated effect of {average_effect:.3f}. Six outcome-independent dimensions produce 12 OOD group records, including {low_n} low-n groups. The OOD gate narrows the applicability domain. The method reports protected results only through checksummed metadata.

## 1. Method boundary

The workflow separates data, model, robustness, and manuscript layers. T104 freezes analysis-only data and model artifacts with redistributable configuration cards. The release contains no protected test values. Negative controls report zero critical leakage.

Every downstream result names its input artifact and its status. A changed input requires a new release or a rejected resume. This rule prevents a later manuscript from silently mixing data, model, and robustness versions.

**Takeaway.** The method is a release contract before it is a model description. The contract fixes what can support a method claim.

## 2. Frozen data and model layers

The frozen data layer contains {release["data_layers"]["silver_tables"]} Silver tables and {release["data_layers"]["gold_auto_rows"]} Gold-auto rows. The model layer contains the {release["model_layers"]["uncertainty"]} uncertainty model and the {release["model_layers"]["multimodal"]} multimodal model. Six thresholds and four dependency entries are recorded in the release manifest.

The multimodal policy requires leakage control and missingness masks. The uncertainty policy abstains on two OOD cases in the upstream fixture. These policies are part of the method and are not post-hoc result filters.

## 3. Paired ablation design

We compare five essential modules under the same budget and frozen group splits. Each comparison contains four paired units and budget eight. The effect is the full metric minus the ablated metric. The mean effect across modules is {average_effect:.3f}.

The largest paired effect is {best["effect_mean"]:.3f} for the {best["module"]} module. Its calibration gain is {best["calibration_gain"]:.3f}. Its OOD RMSE gain is {best["ood_rmse_gain"]:.3f}. These values describe the fixture and do not establish independent causal effects.

One non-essential provider-backed raw-data ablation is interface-blocked. The missingness ledger records that block. The claim gate reports zero blocked essential claims.

**Takeaway.** The ablation design supports a bounded module comparison. It does not support a causal decomposition beyond the paired fixture contract.

## 4. Calibration and OOD handling

The method records calibration and OOD changes for every essential ablation. It keeps calibration gains separate from primary prediction metrics. This separation prevents a calibration improvement from being presented as a prediction improvement.

OOD groups use outcome-independent keys for study, lab, family, species, biofluid, and time. The primary suite contains 12 group records. Six groups are low-n and receive abstention flags. The claim status is `{primary["claim_status"]}`.

The largest-study exclusion, low-n exclusion, and evidence-grade-only scenarios produce {len(sensitivity)} sensitivity records. Their primary metrics are retained as scenario evidence rather than pooled into a single estimate.

**Takeaway.** Applicability is restricted to groups with sufficient support. Low-n and OOD records remain visible and are not silently pooled.

## 5. Agent evaluation as a method check

The upstream scientific-agent suite covers {agent["tasks"]} tasks and {agent["modes"]} modes. It selects `{agent["selected_mode"]}`. Completion, correctness, evidence, schema, safety, and reproducibility each equal 1.000 in the fixture. The failure taxonomy remains part of the evidence package.

Agent evaluation tests workflow execution and evidence handling. It does not establish model performance on live sources. Coordination cost and external-source behavior require a separate study.

## 6. Reproducibility and claim controls

The method stores schemas, fixtures, receipts, manifests, tables, and figure specifications. First generation and resume compare bytes. Checksum mutation and artifact tampering raise errors. The full project gate runs offline.

The claim matrix marks each statement as supported development scope, narrowed by OOD, or limitation required. The manuscript does not promote blocked modules, protected results, or unsupported causal language.

## 7. Limitations

The release is fixture-backed and development-scoped. Its data and model artifacts are analysis-only. The OOD groups are small, and the applicability claim is narrowed. The ablation comparison uses paired fixture units rather than a production campaign.

The agent suite does not test live-source behavior. The non-essential raw-data ablation remains interface-blocked. External citations and venue-specific formatting remain submission-stage work.

## 8. Conclusion

The method combines immutable release boundaries, explicit uncertainty, paired ablations, OOD abstention, and agent evidence. Its strongest result is a reproducible workflow with visible failure and applicability limits. Future releases may extend the evidence domain only after new inputs pass the same contract.

## Evidence references

The claim matrix maps method statements to the T104, T088, T099, and T100 artifacts and their SHA-256 values. The receipt records the exact input set and manuscript bytes.
"""
        return manuscript, draft_0

    def run(self, *, fixture: bool = True) -> PaperBSummary:
        """Generate all Paper B artifacts and reject any attempted overwrite."""
        if not fixture:
            raise PaperBError("--fixture is required for Paper B")
        fixture_data = self._fixture()
        loaded = self._inputs(fixture_data)
        validated = self._validate_inputs(loaded)
        tables = self._tables(validated)
        manuscript, draft_0 = self._draft(validated, tables)
        style = self._style_audit(manuscript)
        if style["status"] != "PASS":
            raise PaperBError(f"Paper B style audit failed: {style}")
        release = validated["release"]
        claims = [
            {
                "claim_id": "M1",
                "claim": "The development release separates data, model, robustness, and manuscript layers.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["release_manifest.json", "freeze_manifest.json"],
            },
            {
                "claim_id": "M2",
                "claim": "The method selects conservative conformal uncertainty and material protocol masked multimodal representation policies.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["release_manifest.json", "data_model_card.md"],
            },
            {
                "claim_id": "M3",
                "claim": "Five essential modules run under paired units, equal budgets, and frozen group splits.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["paired_effects.json", "claim_gate.json"],
            },
            {
                "claim_id": "M4",
                "claim": f"The largest observed paired effect is {max(row['effect_mean'] for row in tables['ablation_results']['rows']):.3f} in the fixture.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["paired_effects.json", "calibration_ood.json"],
            },
            {
                "claim_id": "M5",
                "claim": "Calibration gains and OOD RMSE gains are retained as separate evidence fields.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["calibration_ood.json"],
            },
            {
                "claim_id": "M6",
                "claim": "Outcome-independent OOD grouping narrows applicability and abstains on six low-n groups.",
                "status": "NARROWED_BY_OOD",
                "evidence": ["primary_metrics.json", "claim_gate.json", "sensitivity_report.json"],
            },
            {
                "claim_id": "M7",
                "claim": "The agent suite covers seven tasks and selects single-agent mode under the frozen fixture.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["T088 evidence report"],
            },
            {
                "claim_id": "M8",
                "claim": "The manuscript excludes protected results, unsupported causal language, and blocked module claims.",
                "status": "LIMITATION_REQUIRED",
                "evidence": ["data_model_card.md", "ablation claim gate", "OOD claim gate"],
            },
        ]
        table_manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "tables": [
                {
                    "table_id": "Table 1",
                    "path": "tables/release_boundary.json",
                    "purpose": "frozen data/model boundary",
                    "source_claim": "M1",
                },
                {
                    "table_id": "Table 2",
                    "path": "tables/ablation_results.json",
                    "purpose": "paired module comparisons",
                    "source_claim": "M3",
                },
                {
                    "table_id": "Table 3",
                    "path": "tables/ood_group_results.json",
                    "purpose": "outcome-independent OOD groups",
                    "source_claim": "M6",
                },
                {
                    "table_id": "Table 4",
                    "path": "tables/sensitivity_results.json",
                    "purpose": "OOD sensitivity scenarios",
                    "source_claim": "M6",
                },
                {
                    "table_id": "Table 5",
                    "path": "tables/agent_results.json",
                    "purpose": "agent method check",
                    "source_claim": "M7",
                },
                {
                    "table_id": "Table 6",
                    "path": "tables/method_policy.json",
                    "purpose": "claim and abstention policies",
                    "source_claim": "M8",
                },
            ],
        }
        figure_manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "render_status": "SPEC_ONLY",
            "figures": [
                {
                    "figure_id": "Figure 1",
                    "path": "figures/release_layers.md",
                    "type": "layered_architecture",
                    "source": "release_boundary.json",
                    "claim": "M1",
                },
                {
                    "figure_id": "Figure 2",
                    "path": "figures/ablation_effects.md",
                    "type": "paired_effect_plot",
                    "source": "ablation_results.json",
                    "claim": "M3",
                },
                {
                    "figure_id": "Figure 3",
                    "path": "figures/calibration_ood.md",
                    "type": "paired_metric_plot",
                    "source": "ablation_results.json",
                    "claim": "M5",
                },
                {
                    "figure_id": "Figure 4",
                    "path": "figures/ood_scope.md",
                    "type": "group_support_matrix",
                    "source": "ood_group_results.json",
                    "claim": "M6",
                },
                {
                    "figure_id": "Figure 5",
                    "path": "figures/agent_evaluation.md",
                    "type": "mode_quality_plot",
                    "source": "agent_results.json",
                    "claim": "M7",
                },
            ],
        }
        audit = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "status": style["status"],
            "rule_set": style["rule_set"],
            "violations_fixed": {"banned_terms": 0, "overlong_sentences": 0, "throat_clearing": 0},
            "observed": style,
        }
        payloads: dict[str, bytes] = {
            "paper_b.md": manuscript.encode("utf-8"),
            "draft_0_method.md": draft_0.encode("utf-8"),
            "claim_matrix.json": _canonical(
                {"schema_version": 1, **metadata_for(EvidenceClass.FIXTURE_TEST), "claims": claims}
            ),
            "table_manifest.json": _canonical(table_manifest),
            "figure_manifest.json": _canonical(figure_manifest),
            "style_audit.json": _canonical(audit),
        }
        for table_name, table_value in tables.items():
            payloads[f"tables/{table_name}.json"] = _canonical(
                {**metadata_for(EvidenceClass.FIXTURE_TEST), **table_value}
            )
        figure_specs = {
            "release_layers.md": "# Figure 1: Release layers\n\nShow data, model, robustness, and manuscript layers as separate lanes. Keep protected results outside the diagram.\n",
            "ablation_effects.md": "# Figure 2: Paired ablation effects\n\nPlot full-minus-ablated effects with paired-unit markers and equal-budget annotations.\n",
            "calibration_ood.md": "# Figure 3: Calibration and OOD evidence\n\nPlot calibration gains and OOD RMSE gains as separate panels. Do not merge their scales.\n",
            "ood_scope.md": "# Figure 4: OOD support matrix\n\nPlot group support, coverage, calibration error, selective risk, and abstention flags by dimension.\n",
            "agent_evaluation.md": "# Figure 5: Agent evaluation\n\nPlot fixture quality metrics by agent mode and retain the failure taxonomy in the caption.\n",
        }
        for figure_name, figure_text in figure_specs.items():
            payloads[f"figures/{figure_name}"] = figure_text.encode("utf-8")
        artifact_records: list[dict[str, Any]] = [
            {"path": name, "sha256": _sha256(payload), "bytes": len(payload)}
            for name, payload in sorted(payloads.items())
        ]
        manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "status": "VALID",
            "release_id": release["release_id"],
            "paper_id": "paper_b",
            "target_values_exposed": False,
            "evidence_inputs": len(fixture_data["inputs"]),
            "claims": len(claims),
            "tables": len(table_manifest["tables"]),
            "figures": len(figure_manifest["figures"]),
            "style_status": style["status"],
            "artifacts": artifact_records,
        }
        manifest_bytes = _canonical(manifest)
        payloads["paper_b_manifest.json"] = manifest_bytes
        receipt = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "status": "VALID",
            "paper_id": "paper_b",
            "release_id": release["release_id"],
            "target_values_exposed": False,
            "claim_count": len(claims),
            "table_count": len(table_manifest["tables"]),
            "figure_count": len(figure_manifest["figures"]),
            "style_passed": True,
            "manifest_sha256": _sha256(manifest_bytes),
            "resume_key": _sha256(manifest_bytes + payloads["paper_b.md"]),
            "evidence_inputs": len(fixture_data["inputs"]),
        }
        payloads["paper_b_receipt.json"] = _canonical(receipt)
        self.output_root.mkdir(parents=True, exist_ok=True)
        resumed = 0
        for name, payload in payloads.items():
            path = self.output_root / name
            if path.exists():
                if path.read_bytes() != payload:
                    raise PaperBError(f"immutable Paper B artifact differs: {name}")
                resumed = 1
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
        data_layers = _mapping(release["data_layers"], "data layers")
        model_layers = _mapping(release["model_layers"], "model layers")
        return PaperBSummary(
            release_id=release["release_id"],
            data_layers=len(data_layers),
            model_layers=len(model_layers),
            ablations=len(tables["ablation_results"]["rows"]),
            ood_rows=len(validated["primary"]["rows"]),
            claims=len(claims),
            tables=len(table_manifest["tables"]),
            figures=len(figure_manifest["figures"]),
            evidence_inputs=len(fixture_data["inputs"]),
            style_passed=True,
            resumed=resumed,
            receipt_path=self.output_root / "paper_b_receipt.json",
        )
