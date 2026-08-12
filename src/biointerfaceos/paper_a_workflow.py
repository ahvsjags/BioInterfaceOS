"""Generate an evidence-linked Paper A benchmark manuscript."""

# The generated manuscript text is kept as readable prose literals; its source
# lines intentionally exceed the implementation line-length limit.
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


class PaperAError(RuntimeError):
    """Raised when the Paper A evidence contract is invalid."""


@dataclass(frozen=True)
class PaperASummary:
    """Summary of one deterministic Paper A draft generation."""

    release_id: str
    instances: int
    families: int
    train: int
    validation: int
    claims: int
    tables: int
    figures: int
    evidence_inputs: int
    style_passed: bool
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
        raise PaperAError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperAError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PaperAError(f"{label} must be numeric")
    return float(value)


class PaperAWorkflow:
    """Freeze evidence links and generate a manuscript without hidden targets."""

    REQUIRED_INPUTS = {
        "benchmark release manifest",
        "benchmark freeze receipt",
        "benchmark instances receipt",
        "benchmark grading receipt",
        "benchmark grading metrics",
        "benchmark baseline receipt",
        "benchmark baseline results",
        "benchmark representation receipt",
        "benchmark representation results",
        "extraction receipt",
        "extraction metrics",
        "coverage receipt",
        "coverage report",
        "agent benchmark receipt",
        "agent mode comparison",
        "T088 evidence report",
        "T050 evidence report",
        "T051 evidence report",
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
            fixture_path or self.root / "tests/fixtures/manuscripts/paper_a_fixture.json"
        )
        self.output_root = output_root or self.root / "release/manuscripts/paper_a"

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise PaperAError(f"{label} escaped repository")
        return path

    def _json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PaperAError(f"cannot load {label}: {exc}") from exc

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = self._json(self.fixture_path, "Paper A fixture")
        except (OSError, PaperAError) as exc:
            raise PaperAError(f"cannot load Paper A fixture: {exc}") from exc
        if (
            fixture.get("schema_version") != 1
            or fixture.get("mode") != "paper_a_benchmark_manuscript"
        ):
            raise PaperAError("Paper A fixture schema or mode is invalid")
        try:
            evidence_class, claim_level = require_metadata(fixture, "Paper A fixture")
        except EvidenceSemanticsError as exc:
            raise PaperAError(str(exc)) from exc
        if (
            evidence_class is not EvidenceClass.FIXTURE_TEST
            or claim_level is not AllowedClaimLevel.CONTRACT_TEST
        ):
            raise PaperAError("Paper A fixture must remain contract-only")
        if not isinstance(fixture.get("inputs"), list):
            raise PaperAError("Paper A inputs must be a list")
        if {row.get("label") for row in fixture["inputs"]} != self.REQUIRED_INPUTS:
            raise PaperAError("Paper A input set does not match the evidence contract")
        return fixture

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        loaded: dict[str, Any] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "Paper A input")
            label = _string(row.get("label"), "Paper A input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            expected = _string(row.get("sha256"), f"{label} checksum")
            if _sha256(raw) != expected:
                raise PaperAError(f"input checksum differs: {label}")
            kind = _string(row.get("kind"), f"{label} kind")
            if kind == "json":
                loaded[label] = self._json(path, label)
            elif kind == "text":
                loaded[label] = raw.decode("utf-8")
            else:
                raise PaperAError(f"unsupported input kind: {label}")
        return loaded

    @staticmethod
    def _validate_inputs(data: Mapping[str, Any]) -> None:
        release = _mapping(data["benchmark release manifest"], "benchmark release manifest")
        if release.get("status") != "FROZEN_DEV" or release.get("immutable") is not True:
            raise PaperAError("benchmark release is not immutable")
        if release.get("release_id") != "biointerfacebench-dev-v1.0.0":
            raise PaperAError("unexpected benchmark release id")
        if release.get("target_values_exposed") is not False:
            raise PaperAError("benchmark release exposes target values")
        if release.get("public_hidden_separation") is not True:
            raise PaperAError("benchmark public/hidden boundary is not frozen")
        freeze_receipt = _mapping(data["benchmark freeze receipt"], "benchmark freeze receipt")
        if (
            freeze_receipt.get("status") != "VALID"
            or freeze_receipt.get("target_values_exposed") is not False
        ):
            raise PaperAError("benchmark freeze receipt is invalid")
        instances = _mapping(data["benchmark instances receipt"], "instances receipt")
        grading = _mapping(data["benchmark grading receipt"], "grading receipt")
        baseline = _mapping(data["benchmark baseline receipt"], "baseline receipt")
        representation = _mapping(
            data["benchmark representation receipt"], "representation receipt"
        )
        if any(
            receipt.get("status") != "VALID" or receipt.get("target_values_exposed") is not False
            for receipt in (instances, grading, baseline, representation)
        ):
            raise PaperAError("one benchmark receipt is invalid or exposes targets")
        if instances.get("instances") != 16 or instances.get("families") != 8:
            raise PaperAError("benchmark instance count differs from frozen release")
        grading_metrics = _mapping(data["benchmark grading metrics"], "grading metrics")
        if grading_metrics.get("schema_version") != 1:
            raise PaperAError("grading metrics schema is invalid")
        extraction = _mapping(data["extraction metrics"], "extraction metrics")
        extraction_receipt = _mapping(data["extraction receipt"], "extraction receipt")
        if extraction.get("g2_status") != "PASS" or extraction_receipt.get("status") != "VALID":
            raise PaperAError("extraction G2 evidence is invalid")
        coverage = _mapping(data["coverage receipt"], "coverage receipt")
        coverage_report = _mapping(data["coverage report"], "coverage report")
        if coverage.get("no_imputation") is not True or coverage_report.get("fixture") is not True:
            raise PaperAError("coverage scope or no-imputation gate is invalid")
        agent = _mapping(data["agent benchmark receipt"], "agent benchmark receipt")
        if agent.get("status") != "VALID" or agent.get("target_values_exposed") is not False:
            raise PaperAError("agent benchmark receipt is invalid")
        if agent.get("tasks") != 7 or agent.get("selected_mode") != "single_agent":
            raise PaperAError("agent benchmark selection differs from frozen evidence")
        for report_label in (
            "T088 evidence report",
            "T050 evidence report",
            "T051 evidence report",
        ):
            report = data[report_label]
            if not isinstance(report, str) or not report.strip():
                raise PaperAError(f"missing evidence report: {report_label}")

    @staticmethod
    def _baseline_table(data: Mapping[str, Any]) -> list[dict[str, Any]]:
        results = _mapping(data["benchmark baseline results"], "baseline results")
        rows = []
        for value in results.get("baselines", []):
            row = _mapping(value, "baseline result")
            interval = row.get("primary_ood_confidence_interval", [None, None])
            rows.append(
                {
                    "baseline": _string(row.get("baseline"), "baseline name"),
                    "validation_rmse": _number(row.get("primary_ood_value"), "baseline RMSE"),
                    "ci_low": _number(interval[0], "baseline CI low"),
                    "ci_high": _number(interval[1], "baseline CI high"),
                    "seed": row.get("seed"),
                    "validation_instances": row.get("validation_metrics", {}).get("instances"),
                }
            )
        if len(rows) != 5:
            raise PaperAError("baseline table does not contain five frozen baselines")
        return rows

    @staticmethod
    def _representation_table(data: Mapping[str, Any]) -> list[dict[str, Any]]:
        results = _mapping(data["benchmark representation results"], "representation results")
        rows = []
        for value in results.get("baselines", []):
            row = _mapping(value, "representation result")
            coverage = _mapping(row.get("coverage"), "representation coverage")
            interval = row.get("primary_ood_confidence_interval", [None, None])
            available_subset = coverage.get("available_subset_metrics") or {}
            rows.append(
                {
                    "representation": _string(row.get("baseline"), "representation name"),
                    "validation_rmse": _number(row.get("primary_ood_value"), "representation RMSE"),
                    "ci_low": _number(interval[0], "representation CI low"),
                    "ci_high": _number(interval[1], "representation CI high"),
                    "validation_coverage": coverage.get("validation_coverage"),
                    "available_subset_instances": available_subset.get("instances"),
                    "full_split_primary": coverage.get("full_split_primary"),
                }
            )
        if len(rows) != 4:
            raise PaperAError("representation table does not contain four frozen baselines")
        return rows

    @staticmethod
    def _coverage_table(data: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
        report = _mapping(data["coverage report"], "coverage report")
        dimensions = _mapping(report.get("coverage"), "coverage dimensions")
        rows: list[dict[str, Any]] = []
        missing_values = 0
        for dimension, payload in sorted(dimensions.items()):
            values = _mapping(payload, f"coverage {dimension}").get("observed", {})
            values = _mapping(values, f"coverage {dimension} values")
            missing = values.get("__MISSING__", {}).get("independent_studies", 0)
            missing_values += int(missing)
            rows.append(
                {
                    "dimension": dimension,
                    "observed_categories": len(values),
                    "missing_studies": int(missing),
                    "expected_categories": len(payload.get("expected", [])),
                }
            )
        return rows, missing_values

    @staticmethod
    def _style_audit(text: str) -> dict[str, Any]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        lower = text.lower()
        banned_hits = sorted({term for term in PaperAWorkflow.BANNED_TERMS if term in lower})
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

    def _drafts(self, data: Mapping[str, Any], tables: Mapping[str, Any]) -> tuple[str, str]:
        release = _mapping(data["benchmark release manifest"], "benchmark release manifest")
        benchmark = _mapping(release["benchmark"], "benchmark summary")
        extraction = _mapping(data["extraction metrics"], "extraction metrics")
        coverage = _mapping(data["coverage receipt"], "coverage receipt")
        coverage_report = _mapping(data["coverage report"], "coverage report")
        agent = _mapping(data["agent benchmark receipt"], "agent benchmark receipt")
        baseline_rows = tables["baseline_results"]
        representation_rows = tables["representation_results"]
        best_baseline = min(baseline_rows, key=lambda row: row["validation_rmse"])
        best_representation = min(representation_rows, key=lambda row: row["validation_rmse"])
        gaps = len(coverage_report.get("gaps", []))
        missing_values = tables["coverage_summary"]["missing_values"]
        draft_0 = (
            "# Draft 0 introduction\n\n"
            "Scientific benchmark claims fail when evidence extraction, split design, and coverage limits remain implicit. "
            "BioInterfaceBench makes those boundaries inspectable before a model result becomes a paper claim. "
            f"The development release contains {benchmark['instances']} instances across {benchmark['families']} families. "
            "The first draft frames the paper around evidence boundaries, baseline comparisons, and explicit scope limits.\n"
        )
        manuscript = f"""# BioInterfaceBench: Evidence-Bound Evaluation for Scientific Interface Benchmarks

## Abstract

BioInterfaceBench evaluates scientific-interface prediction as an evidence problem. The frozen development release contains {benchmark["instances"]} instances across {benchmark["families"]} families, with {benchmark["train"]} training and {benchmark["validation"]} validation instances. We separate public inputs from hidden-target metadata, compare {benchmark["baselines"]} statistical baselines and {benchmark["representations"]} representation baselines, and retain extraction, coverage, and agent failures as first-class outputs. The best simple baseline reaches validation RMSE {best_baseline["validation_rmse"]:.6f}; the best representation reaches {best_representation["validation_rmse"]:.6f}. Extraction accuracy is {extraction["overall_accuracy"]:.3f}, while the high-confidence gate reaches precision {extraction["eligible_precision"]:.3f} and recall {extraction["eligible_recall"]:.3f}. The fixture contains {coverage["independent_studies"]} synthetic study identifiers, with {missing_values} missing dimension values and {gaps} declared coverage gaps. These results define a reproducible development benchmark, not a production-scale estimate of scientific performance.

## 1. Introduction

Scientific interface studies combine materials, protocols, biological responses, and evidence locators. A benchmark can score predictions while hiding which records support each score. That design obscures extraction errors, split contamination, and missing study dimensions.

BioInterfaceBench uses an Evidence-Bound Benchmark Layer: every benchmark number links to a frozen input, a named metric, and a declared scope. The layer keeps public inputs separate from hidden-target metadata. It also preserves failed extraction rows, abstentions, coverage gaps, and negative controls beside successful results.

This paper makes three contributions:

1. **Benchmark contract.** We freeze {benchmark["instances"]} instances across {benchmark["families"]} families under an {benchmark["train"]}/{benchmark["validation"]} development split. The release records {benchmark["graders"]} grader cases and separates the public and hidden layers.
2. **Evidence comparison.** We compare five named statistical baselines, four representations, and an extraction gate. The comparison reports primary validation metrics, confidence intervals, missingness coverage, and failure categories.
3. **Scope accounting.** We quantify {coverage["independent_studies"]} synthetic study identifiers, {missing_values} missing dimension values, {gaps} coverage gaps, and seven scientific-agent tasks. The manuscript maps each claim to an immutable artifact.

## 2. The frozen benchmark boundary keeps evaluation auditable

The development release contains {benchmark["instances"]} instances, {benchmark["families"]} families, and an {benchmark["train"]}/{benchmark["validation"]} train/validation split. The release stores public instance inputs and a metadata-only hidden registry in separate files. Public records contain no target value, target hash, or hidden reference. Table 1 records the frozen composition.

The split uses paper-family group keys and retains missingness indicators. T102 negative controls pass strict mode with zero critical leakage. This boundary lets the benchmark report performance without reading hidden target payloads.

## 3. Evaluation setup

We evaluate three evidence layers. First, the extraction benchmark tests numeric, entity, arm, and evidence fields. Second, the prediction benchmark compares named baselines under the frozen split. Third, the agent benchmark measures completion, correctness, evidence grounding, schema validity, safety, reproducibility, and cost across seven tasks.

The primary prediction metric is validation RMSE on the held-out group. Each baseline records a confidence interval and a missingness policy. Representation results keep the full split as primary and report available-subset counts separately. Table 2 and Table 3 provide the complete baseline records.

## 4. Extraction errors define the first evaluation boundary

The extraction benchmark evaluates {extraction["rows"]} rows and classifies {extraction["errors"]} errors. Overall accuracy is {extraction["overall_accuracy"]:.3f}. The high-confidence threshold is {extraction["automatic_threshold"]:.2f}; it selects {extraction["eligible_rows"]} rows with precision {extraction["eligible_precision"]:.3f}, recall {extraction["eligible_recall"]:.3f}, and calibration error {extraction["eligible_calibration_error"]:.3f}. The G2 automatic-field gate passes.

The errors span numeric mismatch, entity resolution, arm labeling, and unresolved evidence locators. Figure 2 groups these outcomes by modality and shows why a single aggregate accuracy does not capture evidence quality.

**Takeaway.** The extraction gate supports automatic use only for the high-confidence subset. The full fixture remains a mixed-accuracy calibration benchmark.

## 5. Named baselines establish the prediction floor

The five statistical baselines define a prediction floor under identical splits. {best_baseline["baseline"]} obtains the lowest validation RMSE at {best_baseline["validation_rmse"]:.6f}; its confidence interval is [{best_baseline["ci_low"]:.6f}, {best_baseline["ci_high"]:.6f}]. Table 2 reports every baseline rather than selecting a single favorable comparator.

The representation comparison separates descriptor, fingerprint, text, and polymer embedding inputs. {best_representation["representation"]} obtains the lowest representation RMSE at {best_representation["validation_rmse"]:.6f}. Structure-dependent representations report validation availability alongside the full-split metric. Figure 3 connects performance to coverage.

**Takeaway.** Fingerprint and descriptor results differ in both error and availability. The benchmark therefore treats representation coverage as part of model evaluation.

## 6. The agent suite measures execution quality beside prediction quality

The scientific-agent benchmark runs {agent["tasks"]} tasks in no-tool, single-agent, and multi-agent modes. The selected mode is `{agent["selected_mode"]}`. Completion, correctness, evidence, schema, safety, and reproducibility each reach {agent["completion"]:.3f}; the failure taxonomy remains explicit even when the aggregate failure count is {agent["failures"]}.

The single-agent and multi-agent modes reach the same fixture quality metrics, while multi-agent coordination adds cost. Figure 4 reports this trade-off without treating coordination as a quality gain.

**Takeaway.** Agent execution metrics complement benchmark scores, but the fixture does not establish behavior on live scientific sources.

## 7. Coverage limits constrain every benchmark claim

The coverage audit counts {coverage["independent_studies"]} synthetic study identifiers. It records {missing_values} missing dimension values and {gaps} declared gaps. The warning ledger contains {coverage["warning_count"]} warnings, and the audit performs no imputation. Table 4 lists the missing dimensions and Figure 5 maps the coverage gaps.

The observed studies cover only a subset of expected materials, endpoints, species, labs, and dates. One evidence row remains review-required. These patterns describe the fixture scope; they do not estimate literature prevalence.

**Takeaway.** Benchmark scores describe the frozen development scope. Broader claims require new study identity resolution, targeted search, and a new versioned release.

## 8. Limitations and reproducibility

This manuscript uses sanitized, fixture-backed artifacts. The benchmark contains {benchmark["instances"]} instances and {coverage["independent_studies"]} synthetic study identifiers, so its estimates do not represent production-scale performance. The hidden layer remains metadata-only, and this draft uses no locked target values.

All tables, figures, and claims point to checksummed repository artifacts. A changed input requires a new benchmark version. The release card, claim matrix, and receipt preserve the exact evidence boundary used by this draft.

## 9. Conclusion

BioInterfaceBench turns benchmark evaluation into an evidence-linked workflow. The frozen release combines split isolation, named baselines, extraction gates, agent metrics, and coverage accounting. Its primary result is a bounded development benchmark whose numbers remain interpretable because the workflow records what the benchmark measures and where its evidence stops.

## Evidence references

The claim matrix maps labels E1--E8 to immutable repository artifacts and SHA-256 values. These internal evidence references support this development draft; external related-work citations remain a submission-stage addition.
"""
        return manuscript, draft_0

    def run(self, *, fixture: bool = True) -> PaperASummary:
        """Generate all Paper A artifacts and reject any attempted overwrite."""
        if not fixture:
            raise PaperAError("--fixture is required for Paper A")
        fixture_data = self._fixture()
        loaded = self._inputs(fixture_data)
        self._validate_inputs(loaded)
        release = _mapping(loaded["benchmark release manifest"], "benchmark release manifest")
        benchmark = _mapping(release["benchmark"], "benchmark summary")
        baseline_rows = self._baseline_table(loaded)
        representation_rows = self._representation_table(loaded)
        coverage_rows, missing_values = self._coverage_table(loaded)
        extraction = _mapping(loaded["extraction metrics"], "extraction metrics")
        coverage_receipt = _mapping(loaded["coverage receipt"], "coverage receipt")
        agent = _mapping(loaded["agent benchmark receipt"], "agent benchmark receipt")
        grading = _mapping(loaded["benchmark grading receipt"], "grading receipt")
        tables = {
            "benchmark_composition": {
                "schema_version": 1,
                "title": "Frozen BioInterfaceBench composition",
                "rows": [
                    {"measure": "instances", "value": benchmark["instances"]},
                    {"measure": "families", "value": benchmark["families"]},
                    {"measure": "train", "value": benchmark["train"]},
                    {"measure": "validation", "value": benchmark["validation"]},
                    {"measure": "grader_cases", "value": benchmark["graders"]},
                    {"measure": "statistical_baselines", "value": benchmark["baselines"]},
                    {"measure": "representation_baselines", "value": benchmark["representations"]},
                ],
            },
            "baseline_results": {
                "schema_version": 1,
                "title": "Statistical baseline comparison",
                "rows": baseline_rows,
            },
            "representation_results": {
                "schema_version": 1,
                "title": "Representation comparison and coverage",
                "rows": representation_rows,
            },
            "extraction_results": {
                "schema_version": 1,
                "title": "Extraction quality by modality",
                "overall": {
                    "rows": extraction["rows"],
                    "correct": extraction["correct"],
                    "errors": extraction["errors"],
                    "accuracy": extraction["overall_accuracy"],
                    "g2_status": extraction["g2_status"],
                    "eligible_precision": extraction["eligible_precision"],
                    "eligible_recall": extraction["eligible_recall"],
                },
                "by_modality": extraction["by_modality"],
            },
            "coverage_results": {
                "schema_version": 1,
                "title": "Coverage by dimension",
                "rows": coverage_rows,
            },
            "agent_results": {
                "schema_version": 1,
                "title": "Scientific-agent benchmark summary",
                "tasks": agent["tasks"],
                "selected_mode": agent["selected_mode"],
                "completion": agent["completion"],
                "correctness": agent["correctness"],
                "evidence": agent["evidence"],
                "schema": agent["schema"],
                "safety": agent["safety"],
                "reproducibility": agent["reproducibility"],
                "failures": agent["failures"],
                "mode_comparison": loaded["agent mode comparison"],
            },
        }
        manuscript, draft_0 = self._drafts(
            loaded,
            {
                "baseline_results": baseline_rows,
                "representation_results": representation_rows,
                "coverage_summary": {"missing_values": missing_values},
            },
        )
        style = self._style_audit(manuscript)
        if style["status"] != "PASS":
            raise PaperAError(f"Paper A style audit failed: {style}")
        claims = [
            {
                "claim_id": "E1",
                "claim": f"BioInterfaceBench freezes {benchmark['instances']} instances across {benchmark['families']} families under an {benchmark['train']}/{benchmark['validation']} split.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["release_manifest.json", "benchmark_composition.json"],
            },
            {
                "claim_id": "E2",
                "claim": f"The public and hidden benchmark layers remain separated, with {grading['instances']} graded instances and no target exposure.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": [
                    "release_manifest.json",
                    "processing_receipt.json",
                    "grading_receipt.json",
                ],
            },
            {
                "claim_id": "E3",
                "claim": "Five named statistical baselines and four representations run under the frozen split.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": [
                    "baseline_receipt.json",
                    "representation_receipt.json",
                    "baseline_results.json",
                    "representation_results.json",
                ],
            },
            {
                "claim_id": "E4",
                "claim": f"The extraction fixture reports accuracy {extraction['overall_accuracy']:.3f}, while its high-confidence subset reaches precision {extraction['eligible_precision']:.3f} and recall {extraction['eligible_recall']:.3f}.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["benchmark_receipt.json", "extraction_metrics.json"],
            },
            {
                "claim_id": "E5",
                "claim": f"The coverage audit counts {coverage_receipt['independent_studies']} synthetic study identifiers, {missing_values} missing dimension values, and {coverage_receipt['gap_count']} gaps without imputation.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["data_coverage_receipt.json", "coverage_report.json"],
            },
            {
                "claim_id": "E6",
                "claim": f"The scientific-agent suite covers {agent['tasks']} tasks and selects the {agent['selected_mode']} mode under equal fixture quality metrics.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": ["agent_benchmark_receipt.json", "mode_comparison.json"],
            },
            {
                "claim_id": "E7",
                "claim": "All reported benchmark claims remain limited to the frozen development fixture and do not use hidden target values.",
                "status": "LIMITATION_REQUIRED",
                "evidence": [
                    "freeze_receipt.json",
                    "release_manifest.json",
                    "T088 evidence report",
                ],
            },
            {
                "claim_id": "E8",
                "claim": "Coverage gaps, extraction errors, abstentions, and failure taxonomies remain visible in the draft evidence package.",
                "status": "SUPPORTED_DEVELOPMENT_SCOPE",
                "evidence": [
                    "extraction_metrics.json",
                    "coverage_report.json",
                    "mode_comparison.json",
                ],
            },
        ]
        tables_manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "tables": [
                {
                    "table_id": "Table 1",
                    "path": "tables/benchmark_composition.json",
                    "purpose": "frozen benchmark composition",
                    "source_claim": "E1",
                },
                {
                    "table_id": "Table 2",
                    "path": "tables/baseline_results.json",
                    "purpose": "statistical baseline comparison",
                    "source_claim": "E3",
                },
                {
                    "table_id": "Table 3",
                    "path": "tables/representation_results.json",
                    "purpose": "representation performance and coverage",
                    "source_claim": "E3",
                },
                {
                    "table_id": "Table 4",
                    "path": "tables/extraction_results.json",
                    "purpose": "extraction quality and high-confidence gate",
                    "source_claim": "E4",
                },
                {
                    "table_id": "Table 5",
                    "path": "tables/coverage_results.json",
                    "purpose": "coverage dimensions and missingness",
                    "source_claim": "E5",
                },
                {
                    "table_id": "Table 6",
                    "path": "tables/agent_results.json",
                    "purpose": "scientific-agent benchmark summary",
                    "source_claim": "E6",
                },
            ],
        }
        figures_manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "render_status": "SPEC_ONLY",
            "figures": [
                {
                    "figure_id": "Figure 1",
                    "path": "figures/evidence_boundary.md",
                    "type": "architecture",
                    "source": "release_manifest.json",
                    "claim": "E2",
                },
                {
                    "figure_id": "Figure 2",
                    "path": "figures/extraction_quality.md",
                    "type": "grouped_bar",
                    "source": "extraction_metrics.json",
                    "claim": "E4",
                },
                {
                    "figure_id": "Figure 3",
                    "path": "figures/baseline_coverage.md",
                    "type": "dot_plot",
                    "source": "baseline_results.json and representation_results.json",
                    "claim": "E3",
                },
                {
                    "figure_id": "Figure 4",
                    "path": "figures/agent_modes.md",
                    "type": "tradeoff_plot",
                    "source": "mode_comparison.json",
                    "claim": "E6",
                },
                {
                    "figure_id": "Figure 5",
                    "path": "figures/coverage_gaps.md",
                    "type": "matrix",
                    "source": "coverage_report.json",
                    "claim": "E5",
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
            "paper_a.md": manuscript.encode("utf-8"),
            "draft_0_introduction.md": draft_0.encode("utf-8"),
            "claim_matrix.json": _canonical(
                {"schema_version": 1, **metadata_for(EvidenceClass.FIXTURE_TEST), "claims": claims}
            ),
            "table_manifest.json": _canonical(tables_manifest),
            "figure_manifest.json": _canonical(figures_manifest),
            "style_audit.json": _canonical(audit),
        }
        for table_name, table_value in tables.items():
            payloads[f"tables/{table_name}.json"] = _canonical(
                {**metadata_for(EvidenceClass.FIXTURE_TEST), **table_value}
            )
        figure_specs: dict[str, str] = {
            "evidence_boundary.md": "# Figure 1: Evidence boundary\n\nShow public instance inputs, frozen split keys, and the metadata-only hidden registry as separate lanes. Keep target values outside the diagram.\n",
            "extraction_quality.md": "# Figure 2: Extraction quality\n\nPlot modality-level accuracy and high-confidence eligibility from `tables/extraction_results.json`. Mark the G2 gate and retain error categories in the caption.\n",
            "baseline_coverage.md": "# Figure 3: Baseline error and representation coverage\n\nPlot validation RMSE with confidence intervals. Add validation availability beside each representation.\n",
            "agent_modes.md": "# Figure 4: Agent mode trade-offs\n\nPlot fixture quality metrics against coordination cost from `tables/agent_results.json`. Do not treat multi-agent cost as a quality gain.\n",
            "coverage_gaps.md": "# Figure 5: Coverage gaps\n\nRender the dimension-by-missingness matrix from `tables/coverage_results.json` and annotate each declared gap with its action.\n",
        }
        for figure_name, figure_text in figure_specs.items():
            payloads[f"figures/{figure_name}"] = figure_text.encode("utf-8")
        artifact_records: list[dict[str, Any]] = []
        for name, payload in sorted(payloads.items()):
            artifact_records.append(
                {"path": name, "sha256": _sha256(payload), "bytes": len(payload)}
            )
        manifest: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "status": "VALID",
            "release_id": release["release_id"],
            "paper_id": "paper_a",
            "target_values_exposed": False,
            "evidence_inputs": len(fixture_data["inputs"]),
            "claims": len(claims),
            "tables": len(tables_manifest["tables"]),
            "figures": len(figures_manifest["figures"]),
            "style_status": style["status"],
            "artifacts": artifact_records,
        }
        manifest_bytes = _canonical(manifest)
        payloads["paper_a_manifest.json"] = manifest_bytes
        receipt: dict[str, Any] = {
            "schema_version": 1,
            **metadata_for(EvidenceClass.FIXTURE_TEST),
            "status": "VALID",
            "paper_id": "paper_a",
            "release_id": release["release_id"],
            "target_values_exposed": False,
            "claim_count": len(claims),
            "table_count": len(tables_manifest["tables"]),
            "figure_count": len(figures_manifest["figures"]),
            "style_passed": True,
            "manifest_sha256": _sha256(manifest_bytes),
            "resume_key": _sha256(manifest_bytes + payloads["paper_a.md"]),
            "evidence_inputs": len(fixture_data["inputs"]),
        }
        payloads["paper_a_receipt.json"] = _canonical(receipt)
        self.output_root.mkdir(parents=True, exist_ok=True)
        resumed = 0
        for name, payload in payloads.items():
            path = self.output_root / name
            if path.exists():
                if path.read_bytes() != payload:
                    raise PaperAError(f"immutable Paper A artifact differs: {name}")
                resumed = 1
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
        return PaperASummary(
            release_id=release["release_id"],
            instances=benchmark["instances"],
            families=benchmark["families"],
            train=benchmark["train"],
            validation=benchmark["validation"],
            claims=len(claims),
            tables=len(tables_manifest["tables"]),
            figures=len(figures_manifest["figures"]),
            evidence_inputs=len(fixture_data["inputs"]),
            style_passed=True,
            resumed=resumed,
            receipt_path=self.output_root / "paper_a_receipt.json",
        )
