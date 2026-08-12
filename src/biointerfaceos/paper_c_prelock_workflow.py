"""Freeze a development Paper C scientific-law manuscript before lockbox access."""

# Generated manuscript prose is kept readable in string literals.
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


class PaperCPrelockError(RuntimeError):
    """Raised when the Paper C pre-lock evidence contract is invalid."""


@dataclass(frozen=True)
class PaperCPrelockSummary:
    """Summary of one deterministic Paper C pre-lock generation."""

    candidate_count: int
    strong_candidates: int
    analyses: int
    predictions: int
    claims: int
    tables: int
    figures: int
    evidence_inputs: int
    style_passed: bool
    lockbox_accessed: bool
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
        raise PaperCPrelockError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperCPrelockError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PaperCPrelockError(f"{label} must be numeric")
    return float(value)


class PaperCPrelockWorkflow:
    """Freeze candidate laws and predictions without reading protected payloads."""

    REQUIRED_INPUTS = {
        "T090 functional-axis report",
        "T091 mediation report",
        "T092 cross-species report",
        "T093 symbolic-law report",
        "T094 protocol-effects report",
        "T095 counterfactual report",
        "T100 OOD report",
        "T101 selection report",
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
        self.fixture_path = (
            fixture_path or self.root / "tests/fixtures/manuscripts/paper_c_prelock_fixture.json"
        )
        self.output_root = output_root or self.root / "release/manuscripts/paper_c_prelock"

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise PaperCPrelockError(f"{label} escaped repository")
        return path

    def _json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PaperCPrelockError(f"cannot load {label}: {exc}") from exc

    def _fixture(self) -> dict[str, Any]:
        fixture = self._json(self.fixture_path, "Paper C pre-lock fixture")
        if (
            fixture.get("schema_version") != 1
            or fixture.get("mode") != "paper_c_scientific_law_prelock"
        ):
            raise PaperCPrelockError("Paper C fixture schema or mode is invalid")
        try:
            evidence_class, claim_level = require_metadata(fixture, "Paper C fixture")
        except EvidenceSemanticsError as exc:
            raise PaperCPrelockError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.FIXTURE_TEST
            or claim_level is not AllowedClaimLevel.CONTRACT_TEST
        ):
            raise PaperCPrelockError("Paper C fixture must remain contract-only")
        inputs = fixture.get("inputs")
        if (
            not isinstance(inputs, list)
            or {row.get("label") for row in inputs} != self.REQUIRED_INPUTS
        ):
            raise PaperCPrelockError("Paper C input set does not match the evidence contract")
        return fixture

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, str]:
        loaded: dict[str, str] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "Paper C input")
            label = _string(row.get("label"), "Paper C input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            if _sha256(raw) != _string(row.get("sha256"), f"{label} checksum"):
                raise PaperCPrelockError(f"input checksum differs: {label}")
            if _string(row.get("kind"), f"{label} kind") != "text":
                raise PaperCPrelockError(f"Paper C input must be text: {label}")
            loaded[label] = raw.decode("utf-8")
        return loaded

    @staticmethod
    def _tokens(text: str, prefix: str) -> dict[str, str]:
        line = next((line for line in text.splitlines() if line.startswith(prefix)), None)
        if line is None:
            raise PaperCPrelockError(f"missing result line: {prefix}")
        return {key: value for key, value in re.findall(r"([a-z_]+)=([^\s]+)", line)}

    @classmethod
    def _validate(cls, data: Mapping[str, str]) -> dict[str, Any]:
        functional = cls._tokens(data["T090 functional-axis report"], "FUNCTIONAL_AXES_VALID")
        if (
            functional.get("samples") != "4"
            or functional.get("modules") != "2"
            or functional.get("candidate_axes") != "2"
            or functional.get("selected_model") != "log_ratio"
            or functional.get("lockbox_clean") != "true"
        ):
            raise PaperCPrelockError("T090 functional-axis evidence is invalid")
        mediation = cls._tokens(data["T091 mediation report"], "MEDIATION_VALID")
        if (
            mediation.get("rows") != "12"
            or mediation.get("estimands") != "4"
            or mediation.get("alternative_mediators") != "2"
            or mediation.get("causal_claim_permitted") != "false"
            or mediation.get("language_status") != "ASSOCIATION_ONLY"
        ):
            raise PaperCPrelockError("T091 mediation evidence is invalid")
        transfer = cls._tokens(data["T092 cross-species report"], "CROSS_SPECIES_VALID")
        if (
            transfer.get("rows") != "10"
            or transfer.get("methods") != "4"
            or transfer.get("abstentions") != "2"
            or transfer.get("selected_method") != "optimal_transport"
        ):
            raise PaperCPrelockError("T092 transfer evidence is invalid")
        symbolic = cls._tokens(data["T093 symbolic-law report"], "SYMBOLIC_LAWS_VALID")
        if (
            symbolic.get("candidates") != "4"
            or symbolic.get("unit_valid") != "3"
            or symbolic.get("rejected") != "1"
            or symbolic.get("nested_folds") != "4"
            or symbolic.get("bootstrap_stability") != "1.000000"
            or symbolic.get("ood_passed") != "true"
            or symbolic.get("fallback") != "false"
        ):
            raise PaperCPrelockError("T093 symbolic-law evidence is invalid")
        protocol = cls._tokens(data["T094 protocol-effects report"], "PROTOCOL_EFFECTS_VALID")
        if (
            protocol.get("rows") != "6"
            or protocol.get("variables") != "4"
            or protocol.get("reversals_detected") != "9"
            or protocol.get("counterexamples") != "2"
            or protocol.get("universal_reversal_permitted") != "false"
            or protocol.get("language_status") != "PROTOCOL_DEPENDENT_BOUNDARY"
        ):
            raise PaperCPrelockError("T094 protocol evidence is invalid")
        counterfactual = cls._tokens(data["T095 counterfactual report"], "COUNTERFACTUALS_VALID")
        if (
            counterfactual.get("rows") != "5"
            or counterfactual.get("interventions") != "2"
            or counterfactual.get("supported") != "2"
            or counterfactual.get("abstentions") != "3"
            or counterfactual.get("rank_stability") != "1.000000"
            or counterfactual.get("unresolved") != "1"
        ):
            raise PaperCPrelockError("T095 counterfactual evidence is invalid")
        ood = cls._tokens(data["T100 OOD report"], "OOD_VALID")
        if (
            ood.get("dimensions") != "6"
            or ood.get("groups") != "12"
            or ood.get("low_n_groups") != "6"
            or ood.get("claim_status") != "NARROWED_BY_OOD"
        ):
            raise PaperCPrelockError("T100 OOD evidence is invalid")
        selection = cls._tokens(data["T101 selection report"], "BIAS_VALID")
        if (
            selection.get("rows") != "8"
            or selection.get("models") != "4"
            or selection.get("missing_rows") != "3"
            or selection.get("model_disagreement") != "0.300000"
            or selection.get("claim_status") != "DOWNGRADED_SELECTION_SENSITIVE"
        ):
            raise PaperCPrelockError("T101 selection evidence is invalid")
        expression_match = re.search(
            r"selected_expression=(.+?) fallback=", data["T093 symbolic-law report"]
        )
        if expression_match is None:
            raise PaperCPrelockError("T093 selected expression is missing")
        return {
            "functional": functional,
            "mediation": mediation,
            "transfer": transfer,
            "symbolic": symbolic,
            "protocol": protocol,
            "counterfactual": counterfactual,
            "ood": ood,
            "selection": selection,
            "expression": expression_match.group(1).strip(),
        }

    @staticmethod
    def _style_audit(text: str) -> dict[str, Any]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        lower = text.lower()
        banned_hits = sorted({term for term in PaperCPrelockWorkflow.BANNED_TERMS if term in lower})
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
    def _candidate_cards(metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "candidate_id": "C1",
                "name": "functional-axis association",
                "support": "HIGH_DEVELOPMENT_SUPPORT",
                "evidence": "log_ratio selected; bootstrap stability 0.93; leave-study stability 0.90; random control 0.22",
                "allowed_wording": "stable development association",
                "blocked_wording": ["causes", "mediates", "universal law"],
                "abstain_if": "functional axes are unavailable or the evaluated group is OOD",
            },
            {
                "candidate_id": "C2",
                "name": "unit-aware symbolic candidate",
                "support": "HIGH_DEVELOPMENT_SUPPORT",
                "evidence": f"{metrics['symbolic']['unit_valid']} unit-valid candidates; nested folds {metrics['symbolic']['nested_folds']}; bootstrap stability {metrics['symbolic']['bootstrap_stability']}; OOD passed",
                "expression": metrics["expression"],
                "allowed_wording": "bounded symbolic candidate",
                "blocked_wording": ["universal law", "causal mechanism"],
                "abstain_if": "units fail, expression support is OOD, or stability falls below the frozen gate",
            },
            {
                "candidate_id": "C3",
                "name": "protocol-dependent boundary effect",
                "support": "BOUNDED_DEVELOPMENT_SUPPORT",
                "evidence": "raw effect 0.076667; adjusted effect -0.045000; 9 reversal detections; 2 counterexamples",
                "allowed_wording": "protocol-dependent boundary effect",
                "blocked_wording": ["universal reversal", "causal correction"],
                "abstain_if": "protocol variables or comparable-study strata are unavailable",
            },
            {
                "candidate_id": "C4",
                "name": "overlap-bounded transfer",
                "support": "BOUNDED_DEVELOPMENT_SUPPORT",
                "evidence": "optimal_transport selected; 2 supported held-out cases; 2 unmatched cases abstained",
                "allowed_wording": "overlap-bounded transfer hypothesis",
                "blocked_wording": ["broad cross-species generalization", "universal transfer"],
                "abstain_if": "material overlap or leave-material support fails",
            },
            {
                "candidate_id": "C5",
                "name": "supported counterfactual ranking",
                "support": "EXPLORATORY_ONLY",
                "evidence": "2 interventions scored; 3 abstentions; rank stability 1.0; 1 contradiction unresolved",
                "allowed_wording": "model-based ranking hypothesis",
                "blocked_wording": ["causal intervention", "universal ranking"],
                "abstain_if": "positivity, OOD, or model agreement fails",
            },
        ]

    @staticmethod
    def _analysis_specs() -> list[dict[str, Any]]:
        return [
            {
                "analysis_id": "A1",
                "candidate_id": "C1",
                "analysis": "log-ratio functional-axis association",
                "inputs": ["T090"],
                "primary_metric": "bootstrap and leave-study stability",
                "lockbox_rule": "recompute with frozen axis definition; abstain without axis support",
            },
            {
                "analysis_id": "A2",
                "candidate_id": "C2",
                "analysis": "unit-aware symbolic expression evaluation",
                "inputs": ["T093"],
                "primary_metric": "unit validity, nested study-CV, expression stability, OOD RMSE",
                "lockbox_rule": "evaluate the frozen expression; do not refit the selection rule",
            },
            {
                "analysis_id": "A3",
                "candidate_id": "C3",
                "analysis": "protocol-adjusted boundary comparison",
                "inputs": ["T094"],
                "primary_metric": "raw versus adjusted effect and reversal tests",
                "lockbox_rule": "repeat predefined protocol strata; retain counterexamples",
            },
            {
                "analysis_id": "A4",
                "candidate_id": "C4",
                "analysis": "leave-material transfer validation",
                "inputs": ["T092"],
                "primary_metric": "held-out RMSE, overlap, calibration, abstention",
                "lockbox_rule": "score only supported overlap; preserve unmatched exclusions",
            },
            {
                "analysis_id": "A5",
                "candidate_id": "C5",
                "analysis": "supported counterfactual ranking",
                "inputs": ["T095"],
                "primary_metric": "rank stability and contradiction status",
                "lockbox_rule": "score supported interventions only; no causal interpretation",
            },
        ]

    @staticmethod
    def _draft(metrics: Mapping[str, Any], cards: list[dict[str, Any]]) -> tuple[str, str]:
        expression = metrics["expression"]
        draft_0 = (
            "# Draft 0 scientific-law framing\n\n"
            "This pre-lock package freezes bounded development candidates and exact analyses. "
            "It records future predictions without reading protected evaluation payloads.\n"
        )
        manuscript = f"""# Development candidates for scientific interface laws: a pre-lock specification

## Abstract

This pre-lock manuscript defines five development candidates for scientific interface analysis. The candidates cover functional-axis association, unit-aware symbolic structure, protocol-dependent boundaries, overlap-bounded transfer, and supported model-based ranking. The strongest development support comes from the functional-axis and symbolic candidates. All candidates retain abstention rules. The package freezes analyses, plots, allowed wording, and predictions before protected evaluation.

## 1. Pre-lock scope

The manuscript separates development discovery from future evaluation. It uses eight checksum-pinned reports from T090 through T101. It does not view protected payloads. It records predicted outcomes as predictions, not results.

T100 narrows the applicability domain because six low-n groups are present. T101 downgrades claims because four selection models disagree by 0.300000. These boundaries apply to every candidate below.

**Takeaway.** The package freezes what can be tested later. It does not convert development patterns into confirmed laws.

## 2. Candidate C1: functional-axis association

T090 selected the `log_ratio` model from three alternatives. The discovery used four samples and two functional modules. Bootstrap stability was 0.930000. Leave-study stability was 0.900000. The random-module control was 0.220000.

The allowed wording is stable development association. The package blocks causal and universal-law wording. Future evaluation must recompute the frozen axis. It must abstain when axis support is unavailable or OOD.

## 3. Candidate C2: unit-aware symbolic structure

T093 evaluated four symbolic candidates. Three candidates passed unit checks. One candidate was rejected for dimensional inconsistency. Nested study-CV used four outer folds. Expression bootstrap stability was 1.000000. The selected expression is `{expression}`.

The allowed wording is bounded symbolic candidate. The package freezes the expression and selection rule. Future evaluation must not refit the rule on protected data. It must abstain when units, support, or stability fail.

**Takeaway.** C2 is a testable development candidate. It is not a universal scientific law.

## 4. Candidate C3: protocol-dependent boundary effect

T094 compared raw and protocol-adjusted effects across six studies. The raw effect was 0.076667. The adjusted effect was -0.045000. Nine reversal detections were retained. Two counterexamples remained in the report.

The allowed wording is protocol-dependent boundary effect. The package blocks universal reversal and causal correction. Future evaluation must use the four predefined protocol variables. It must retain counterexamples.

## 5. Candidate C4: overlap-bounded transfer

T092 compared four transfer methods across two strata. `optimal_transport` was selected. Two held-out cases were scored. Two unmatched cases were abstained. Material overlap and leave-material validation remain required.

The allowed wording is overlap-bounded transfer hypothesis. The package blocks broad generalization. Future evaluation must preserve unmatched exclusions and report calibration.

## 6. Candidate C5: supported counterfactual ranking

T095 froze two intervention families and compared two model families. Two interventions were scored. Three cases were abstained. Rank stability was 1.000000 on the supported pair. Three contradiction edges were retained. One edge remains unresolved.

The allowed wording is model-based ranking hypothesis. The package blocks causal intervention and universal ranking wording. Future evaluation must check positivity, OOD support, and model agreement before scoring.

## 7. Cross-candidate gates

T091 reports association only. Its causal claim gate is false. T100 narrows OOD applicability. T101 reports selection sensitivity. These gates prevent stronger wording from entering the pre-lock package.

Every candidate has a primary analysis, a plot definition, an abstention rule, and a protected-evaluation prediction. The prediction table marks every outcome as pending. No protected result is included.

**Takeaway.** The pre-lock package is complete only when candidate strength and failure boundaries travel together.

## 8. Limitations

The candidates are fixture-backed development discoveries. They do not establish universal biological laws. The mediation chain remains association-only. Transfer and counterfactual candidates have explicit abstentions. OOD and selection sensitivity narrow applicability.

The package does not include protected payloads. It does not include post-lockbox interpretations. New candidates require a new preregistration and a new freeze candidate.

## Evidence references

The claim matrix links C1--C5 to T090, T091, T092, T093, T094, T095, T100, and T101. The analysis registry records the exact tests and allowed outputs. The receipt records the byte-stable pre-lock package.
"""
        return manuscript, draft_0

    def run(self, *, fixture: bool = True) -> PaperCPrelockSummary:
        """Generate the pre-lock package and reject any attempted overwrite."""
        if not fixture:
            raise PaperCPrelockError("--fixture is required for Paper C pre-lock")
        fixture_data = self._fixture()
        loaded = self._inputs(fixture_data)
        metrics = self._validate(loaded)
        cards = self._candidate_cards(metrics)
        analyses = self._analysis_specs()
        manuscript, draft_0 = self._draft(metrics, cards)
        style = self._style_audit(manuscript)
        if style["status"] != "PASS":
            raise PaperCPrelockError(f"Paper C style audit failed: {style}")
        predictions = [
            {
                "prediction_id": "P1",
                "candidate_id": "C1",
                "expected": "association direction remains within the frozen development envelope",
                "status": "PREDICTED_BEFORE_LOCKBOX",
                "abstain_if": cards[0]["abstain_if"],
            },
            {
                "prediction_id": "P2",
                "candidate_id": "C2",
                "expected": "the frozen expression remains unit-valid on supported cases",
                "status": "PREDICTED_BEFORE_LOCKBOX",
                "abstain_if": cards[1]["abstain_if"],
            },
            {
                "prediction_id": "P3",
                "candidate_id": "C3",
                "expected": "protocol adjustment remains boundary-dependent rather than universal",
                "status": "PREDICTED_BEFORE_LOCKBOX",
                "abstain_if": cards[2]["abstain_if"],
            },
            {
                "prediction_id": "P4",
                "candidate_id": "C4",
                "expected": "transfer is supported only where material overlap passes",
                "status": "PREDICTED_BEFORE_LOCKBOX",
                "abstain_if": cards[3]["abstain_if"],
            },
            {
                "prediction_id": "P5",
                "candidate_id": "C5",
                "expected": "supported rankings remain stable only after positivity and model-agreement checks",
                "status": "PREDICTED_BEFORE_LOCKBOX",
                "abstain_if": cards[4]["abstain_if"],
            },
        ]
        allowed = {
            "schema_version": 1,
            "allowed": [card["allowed_wording"] for card in cards],
            "blocked": sorted({term for card in cards for term in card["blocked_wording"]}),
            "global_rules": [
                "association-only wording for mediation",
                "narrow applicability under OOD and selection sensitivity",
                "no lockbox result before evaluator authorization",
            ],
        }
        claims = [
            {
                "claim_id": "C1",
                "claim": "The log-ratio functional-axis association is stable in the development fixture.",
                "status": "DEVELOPMENT_SUPPORTED",
                "evidence": ["T090 functional-axis report"],
            },
            {
                "claim_id": "C2",
                "claim": f"The unit-aware symbolic candidate is {metrics['expression']}.",
                "status": "DEVELOPMENT_SUPPORTED",
                "evidence": ["T093 symbolic-law report"],
            },
            {
                "claim_id": "C3",
                "claim": "Protocol adjustment defines a boundary effect rather than a universal reversal.",
                "status": "BOUNDED_BY_COUNTEREXAMPLES",
                "evidence": ["T094 protocol-effects report"],
            },
            {
                "claim_id": "C4",
                "claim": "Transfer support is bounded by material overlap and leave-material validation.",
                "status": "BOUNDED_BY_ABSTENTION",
                "evidence": ["T092 cross-species report"],
            },
            {
                "claim_id": "C5",
                "claim": "Counterfactual ranking remains a model-based hypothesis with unresolved contradictions.",
                "status": "EXPLORATORY_ONLY",
                "evidence": ["T095 counterfactual report"],
            },
            {
                "claim_id": "C6",
                "claim": "Mediation wording remains association-only because causal identification gates fail.",
                "status": "LANGUAGE_GATE",
                "evidence": ["T091 mediation report"],
            },
            {
                "claim_id": "C7",
                "claim": "OOD and selection sensitivity narrow every future applicability statement.",
                "status": "LANGUAGE_GATE",
                "evidence": ["T100 OOD report", "T101 selection report"],
            },
            {
                "claim_id": "C8",
                "claim": "All lockbox outcomes remain predictions until evaluator authorization.",
                "status": "PRELOCK_ONLY",
                "evidence": ["prediction_table.json", "allowed_wording.json"],
            },
        ]
        tables = {
            "candidate_support": {
                "schema_version": 1,
                "title": "Candidate-law support cards",
                "rows": cards,
            },
            "predictions": {
                "schema_version": 1,
                "title": "Predicted lockbox outcomes",
                "rows": predictions,
            },
            "analysis_registry": {
                "schema_version": 1,
                "title": "Frozen analysis registry",
                "rows": analyses,
            },
            "abstention_boundaries": {
                "schema_version": 1,
                "title": "Abstention boundaries",
                "rows": [
                    {"candidate_id": card["candidate_id"], "abstain_if": card["abstain_if"]}
                    for card in cards
                ],
            },
            "selection_ood_limits": {
                "schema_version": 1,
                "title": "Selection and OOD limits",
                "rows": [
                    {
                        "gate": "OOD",
                        "status": metrics["ood"]["claim_status"],
                        "low_n_groups": int(metrics["ood"]["low_n_groups"]),
                    },
                    {
                        "gate": "selection",
                        "status": metrics["selection"]["claim_status"],
                        "model_disagreement": float(metrics["selection"]["model_disagreement"]),
                    },
                ],
            },
            "evidence_inputs": {
                "schema_version": 1,
                "title": "Checksum-pinned evidence inputs",
                "rows": [
                    {"label": label, "path": row["path"], "sha256": row["sha256"]}
                    for label, row in ((item["label"], item) for item in fixture_data["inputs"])
                ],
            },
        }
        table_manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "tables": [
                {
                    "table_id": f"Table {index}",
                    "path": f"tables/{name}.json",
                    "purpose": value["title"],
                    "source_claim": f"C{index}",
                }
                for index, (name, value) in enumerate(tables.items(), 1)
            ],
        }
        figure_manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "render_status": "SPEC_ONLY",
            "figures": [
                {
                    "figure_id": "Figure 1",
                    "path": "figures/candidate_law_map.md",
                    "type": "candidate_map",
                    "source": "candidate_support.json",
                    "claim": "C1",
                },
                {
                    "figure_id": "Figure 2",
                    "path": "figures/symbolic_expression.md",
                    "type": "expression_panel",
                    "source": "analysis_registry.json",
                    "claim": "C2",
                },
                {
                    "figure_id": "Figure 3",
                    "path": "figures/protocol_boundaries.md",
                    "type": "paired_effect_panel",
                    "source": "candidate_support.json",
                    "claim": "C3",
                },
                {
                    "figure_id": "Figure 4",
                    "path": "figures/transfer_abstention.md",
                    "type": "overlap_matrix",
                    "source": "abstention_boundaries.json",
                    "claim": "C4",
                },
                {
                    "figure_id": "Figure 5",
                    "path": "figures/prelock_predictions.md",
                    "type": "prediction_timeline",
                    "source": "predictions.json",
                    "claim": "C8",
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
            "paper_c_prelock.md": manuscript.encode("utf-8"),
            "draft_0_laws.md": draft_0.encode("utf-8"),
            "candidate_cards.json": _canonical(
                {
                    "schema_version": 1,
                    **metadata_for(EvidenceClass.FIXTURE_TEST),
                    "candidates": cards,
                }
            ),
            "prediction_table.json": _canonical(
                {
                    "schema_version": 1,
                    **metadata_for(EvidenceClass.FIXTURE_TEST),
                    "predictions": predictions,
                    "protected_results_included": False,
                }
            ),
            "analysis_specs.json": _canonical(
                {
                    "schema_version": 1,
                    **metadata_for(EvidenceClass.FIXTURE_TEST),
                    "analyses": analyses,
                }
            ),
            "allowed_wording.json": _canonical(
                {**metadata_for(EvidenceClass.FIXTURE_TEST), **allowed}
            ),
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
            "candidate_law_map.md": "# Figure 1: Candidate-law map\n\nMap support strength, evidence links, and blocked wording for C1--C5.\n",
            "symbolic_expression.md": "# Figure 2: Symbolic expression\n\nShow the frozen expression, unit gate, nested study-CV, and OOD rule.\n",
            "protocol_boundaries.md": "# Figure 3: Protocol boundaries\n\nPlot raw and adjusted effects with reversal tests and retained counterexamples.\n",
            "transfer_abstention.md": "# Figure 4: Transfer support\n\nShow material overlap, held-out support, calibration, and abstention regions.\n",
            "prelock_predictions.md": "# Figure 5: Pre-lock predictions\n\nShow prediction status before evaluator authorization. Do not plot protected outcomes.\n",
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
            "paper_id": "paper_c_prelock",
            "target_values_exposed": False,
            "lockbox_accessed": False,
            "predictions_frozen": True,
            "evidence_inputs": len(fixture_data["inputs"]),
            "candidates": len(cards),
            "strong_candidates": sum(
                card["support"] == "HIGH_DEVELOPMENT_SUPPORT" for card in cards
            ),
            "analyses": len(analyses),
            "predictions": len(predictions),
            "claims": len(claims),
            "tables": len(table_manifest["tables"]),
            "figures": len(figure_manifest["figures"]),
            "style_status": style["status"],
            "artifacts": artifact_records,
        }
        manifest_bytes = _canonical(manifest)
        payloads["paper_c_prelock_manifest.json"] = manifest_bytes
        receipt = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "status": "VALID",
            "paper_id": "paper_c_prelock",
            "target_values_exposed": False,
            "lockbox_accessed": False,
            "predictions_frozen": True,
            "candidate_count": len(cards),
            "analysis_count": len(analyses),
            "prediction_count": len(predictions),
            "claim_count": len(claims),
            "manifest_sha256": _sha256(manifest_bytes),
            "resume_key": _sha256(manifest_bytes + payloads["paper_c_prelock.md"]),
            "evidence_inputs": len(fixture_data["inputs"]),
        }
        payloads["paper_c_prelock_receipt.json"] = _canonical(receipt)
        self.output_root.mkdir(parents=True, exist_ok=True)
        resumed = 0
        for name, payload in payloads.items():
            path = self.output_root / name
            if path.exists():
                if path.read_bytes() != payload:
                    raise PaperCPrelockError(f"immutable Paper C artifact differs: {name}")
                resumed = 1
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
        return PaperCPrelockSummary(
            candidate_count=len(cards),
            strong_candidates=sum(card["support"] == "HIGH_DEVELOPMENT_SUPPORT" for card in cards),
            analyses=len(analyses),
            predictions=len(predictions),
            claims=len(claims),
            tables=len(table_manifest["tables"]),
            figures=len(figure_manifest["figures"]),
            evidence_inputs=len(fixture_data["inputs"]),
            style_passed=True,
            lockbox_accessed=False,
            resumed=resumed,
            receipt_path=self.output_root / "paper_c_prelock_receipt.json",
        )
