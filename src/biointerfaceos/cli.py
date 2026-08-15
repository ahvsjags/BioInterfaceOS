"""Standard-library command-line interface for the BioInterfaceOS foundation."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from biointerfaceos import __version__

FUTURE_COMMANDS: tuple[str, ...] = ()

REQUIRED_FILES = (
    "AGENTS.md",
    "GOAL.md",
    "PLANS.md",
    "PROJECT_STATE.yaml",
    "TASKS.tsv",
    "pyproject.toml",
    "uv.lock",
)

SKELETON_DIRECTORIES = (
    "agents",
    "benchmarks",
    "config",
    "containers",
    "data",
    "docs",
    "experiments",
    "models",
    "registry",
    "release",
    "reports",
    "schemas",
    "scripts",
    "slurm",
    "src",
    "tests",
    "workflows",
)


@dataclass(frozen=True)
class Check:
    """One deterministic doctor result."""

    status: str
    name: str
    detail: str
    mandatory: bool = False


def find_repository_root(start: Path | None = None) -> Path | None:
    """Find the nearest repository root using foundation marker files."""
    origin = (start or Path.cwd()).resolve()
    candidates = (origin, *origin.parents)
    for candidate in candidates:
        if (candidate / "AGENTS.md").is_file() and (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def foundation_checks(root: Path | None) -> list[Check]:
    """Return foundation checks without mutating the repository."""
    checks = [
        Check(
            "PASS" if sys.version_info[:2] == (3, 11) else "FAIL",
            "python",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            mandatory=True,
        )
    ]
    if root is None:
        checks.append(Check("FAIL", "repository", "repository root not found", mandatory=True))
    else:
        checks.append(Check("PASS", "repository", str(root), mandatory=True))
        for relative in REQUIRED_FILES:
            exists = (root / relative).is_file()
            checks.append(
                Check(
                    "PASS" if exists else "FAIL",
                    f"file:{relative}",
                    "present" if exists else "missing",
                    mandatory=True,
                )
            )
        missing_dirs = [name for name in SKELETON_DIRECTORIES if not (root / name).is_dir()]
        checks.append(
            Check(
                "PASS" if not missing_dirs else "FAIL",
                "skeleton",
                "17 top-level directories present" if not missing_dirs else f"missing: {', '.join(missing_dirs)}",
                mandatory=True,
            )
        )

    package_spec = importlib.util.find_spec("biointerfaceos")
    checks.append(
        Check(
            "PASS" if package_spec is not None and bool(__version__) else "FAIL",
            "package-import",
            f"biointerfaceos {__version__}" if package_spec is not None else "not importable",
            mandatory=True,
        )
    )
    for tool in ("pytest", "ruff", "mypy"):
        available = importlib.util.find_spec(tool) is not None
        checks.append(
            Check(
                "PASS" if available else "WARN",
                f"optional:{tool}",
                "available" if available else "not installed",
            )
        )
    for command in FUTURE_COMMANDS:
        checks.append(Check("NOT_IMPLEMENTED", f"command:{command}", "future task"))
    return checks


def doctor(strict: bool) -> int:
    """Print deterministic foundation diagnostics and return their status."""
    checks = foundation_checks(find_repository_root())
    for check in checks:
        print(f"{check.status} {check.name}: {check.detail}")
    failures = sum(check.mandatory and check.status != "PASS" for check in checks)
    mode = "strict" if strict else "standard"
    print(f"SUMMARY mode={mode} mandatory_failures={failures}")
    return 1 if failures else 0


def not_implemented(command: str) -> int:
    """Fail explicitly for command families owned by future tasks."""
    print(f"NOT_IMPLEMENTED: '{command}' is reserved for a future task.", file=sys.stderr)
    return 2


def build_parser(prog: str = "biointerfaceos") -> argparse.ArgumentParser:
    """Build the public argument parser."""
    parser = argparse.ArgumentParser(prog=prog, description="BioInterfaceOS command line")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser("doctor", help="check foundation prerequisites")
    doctor_parser.add_argument("--strict", action="store_true", help="enforce mandatory checks")

    state_parser = subparsers.add_parser("state", help="validate and inspect project state")
    state_subparsers = state_parser.add_subparsers(dest="state_command")
    state_subparsers.add_parser("validate", help="validate PROJECT_STATE.yaml and TASKS.tsv")
    state_subparsers.add_parser("next", help="print the next dependency-satisfied READY task")
    project_parser = subparsers.add_parser("project", help="run final project acceptance and public release")
    project_subparsers = project_parser.add_subparsers(dest="project_command")
    accept_parser = project_subparsers.add_parser("accept", help="run G0-G10 final acceptance gates")
    accept_parser.add_argument("--strict", action="store_true")
    accept_r2_parser = project_subparsers.add_parser(
        "accept-r2", help="audit the R2 external reproduction and editorial acceptance path"
    )
    accept_r2_parser.add_argument("--strict", action="store_true")
    remediation_r2_parser = project_subparsers.add_parser(
        "audit-r2-remediation",
        help="audit the current evidence disposition for every R2 reviewer finding",
    )
    remediation_r2_parser.add_argument("--strict", action="store_true")
    external_handoff_r2_parser = project_subparsers.add_parser(
        "audit-r2-external-handoff",
        help="audit the R2 external source and independent-evaluation handoff package",
    )
    external_handoff_r2_parser.add_argument("--strict", action="store_true")
    external_gate_path_r2_parser = project_subparsers.add_parser(
        "audit-r2-external-gate-path",
        help="audit the ordered R2 external source, evaluator and editorial gate path",
    )
    external_gate_path_r2_parser.add_argument("--strict", action="store_true")

    schema_parser = subparsers.add_parser("schema", help="validate versioned schemas")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command")
    schema_subparsers.add_parser("validate-all", help="validate all schemas and fixtures")

    storage_parser = subparsers.add_parser("storage", help="audit repository storage")
    storage_subparsers = storage_parser.add_subparsers(dest="storage_command")
    storage_audit_parser = storage_subparsers.add_parser("audit", help="audit storage usage")
    storage_audit_parser.add_argument("--strict", action="store_true", help="fail over budget")

    source_parser = subparsers.add_parser("source", help="validate source registries")
    source_subparsers = source_parser.add_subparsers(dest="source_command")
    manifest_parser = source_subparsers.add_parser("manifest", help="validate source manifest")
    manifest_subparsers = manifest_parser.add_subparsers(dest="manifest_command")
    manifest_subparsers.add_parser("validate", help="validate the Parquet source manifest")
    policy_parser = source_subparsers.add_parser("policy", help="run source policy checks")
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command")
    policy_subparsers.add_parser("self-test", help="run offline policy fixtures")
    source_subparsers.add_parser("audit-specialized", help="validate specialized nanodatabase admission decisions")
    assets_parser = subparsers.add_parser("assets", help="verify content-addressed assets")
    assets_subparsers = assets_parser.add_subparsers(dest="assets_command")
    assets_subparsers.add_parser("verify", help="verify CAS blobs and provenance index")
    catalog_parser = subparsers.add_parser("catalog", help="build and check analytical catalog")
    catalog_subparsers = catalog_parser.add_subparsers(dest="catalog_command")
    catalog_subparsers.add_parser("build", help="rebuild Parquet-backed DuckDB views")
    catalog_subparsers.add_parser("check", help="check catalog metadata and views")
    release_parser = subparsers.add_parser("release", help="freeze and verify releases")
    release_subparsers = release_parser.add_subparsers(dest="release_command")
    freeze_parser = release_subparsers.add_parser("freeze", help="create an immutable release")
    freeze_parser.add_argument("--fixture", action="store_true", help="freeze the fixture namespace")
    freeze_dev_parser = release_subparsers.add_parser(
        "freeze-dev", help="freeze the development data and model release"
    )
    freeze_dev_parser.add_argument("--fixture", action="store_true", help="freeze the sanitized development release")
    freeze_prelock_parser = release_subparsers.add_parser(
        "freeze-prelock", help="freeze the signed internal release before lockbox access"
    )
    freeze_prelock_parser.add_argument(
        "--strict", action="store_true", help="require a clean working tree before freezing"
    )
    release_subparsers.add_parser("verify-prelock", help="verify the signed internal pre-lock release")
    public_audit_parser = release_subparsers.add_parser(
        "audit-public", help="audit licensing, asset inventory, and public-release boundaries"
    )
    public_audit_parser.add_argument("--strict", action="store_true")
    verify_parser = release_subparsers.add_parser("verify", help="verify an immutable release")
    verify_parser.add_argument("--fixture", action="store_true", help="verify the fixture namespace")
    verify_parser.add_argument("--release-id", default=None, help="specific release identifier")
    verify_parser.add_argument("release_kind", nargs="?", choices=("bronze",), default=None)
    lockbox_parser = subparsers.add_parser("lockbox", help="test lockbox firewall")
    lockbox_subparsers = lockbox_parser.add_subparsers(dest="lockbox_command")
    lockbox_subparsers.add_parser("self-test", help="run offline firewall and scanner tests")
    evaluate_parser = lockbox_subparsers.add_parser("evaluate", help="run the evaluator-only one-shot lockbox protocol")
    evaluate_parser.add_argument("--release", required=True, choices=("FROZEN_DEV",))
    evaluate_parser.add_argument("--once", action="store_true")
    independent_evaluate_parser = lockbox_subparsers.add_parser(
        "evaluate-independent",
        help="audit T124 readiness for an external protected-data evaluator",
    )
    independent_evaluate_parser.add_argument("--strict", action="store_true")
    audit_results_parser = lockbox_subparsers.add_parser(
        "audit-results", help="audit sealed lockbox results against the frozen claim package"
    )
    audit_results_parser.add_argument("--strict", action="store_true")
    publication_parser = subparsers.add_parser("publication", help="generate final publication figures and tables")
    publication_subparsers = publication_parser.add_subparsers(dest="publication_command")
    render_parser = publication_subparsers.add_parser("render", help="render the frozen publication package")
    render_parser.add_argument("--strict", action="store_true")
    render_r2_parser = publication_subparsers.add_parser(
        "render-r2", help="render field-mapped, protocol-only R2 figures"
    )
    render_r2_parser.add_argument("--strict", action="store_true")
    verify_r2_parser = publication_subparsers.add_parser("verify-r2", help="verify the immutable R2 figure QA receipt")
    verify_r2_parser.add_argument("--strict", action="store_true")
    reproduce_parser = subparsers.add_parser("reproduce", help="rebuild and verify named reproducibility packages")
    reproduce_subparsers = reproduce_parser.add_subparsers(dest="reproduce_command")
    reproduce_release_parser = reproduce_subparsers.add_parser(
        "release", help="rebuild the R2 public software-replay release"
    )
    reproduce_release_parser.add_argument("--strict", action="store_true")
    clean_reproduce_parser = subparsers.add_parser(
        "reproduce-clean", help="build and verify the network-free clean-room package"
    )
    clean_reproduce_parser.add_argument("--strict", action="store_true")
    agent_parser = subparsers.add_parser("agent", help="run typed multi-agent runtime checks")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command")
    agent_subparsers.add_parser("self-test", help="run offline runtime contract self-test")
    agent_eval_parser = agent_subparsers.add_parser("eval", help="evaluate typed agents on deterministic fixtures")
    agent_eval_subparsers = agent_eval_parser.add_subparsers(dest="agent_eval_command")
    agent_eval_subparsers.add_parser("source-license", help="evaluate SourceScout and LicenseGate")
    agent_eval_subparsers.add_parser("extraction", help="evaluate the multimodal ExtractionAgent")
    agent_eval_subparsers.add_parser("audit", help="evaluate Resolution and EvidenceAuditor")
    agent_eval_subparsers.add_parser("hypothesis", help="evaluate exploratory Mechanism and hypothesis agents")
    agent_eval_subparsers.add_parser("modeling", help="evaluate ModelBuilder and Statistician agents")
    agent_eval_subparsers.add_parser("reproducibility", help="evaluate reproducibility and disabled Lockbox agents")
    redteam_parser = agent_subparsers.add_parser("red-team", help="run the mandatory RedTeam attack suite")
    redteam_parser.add_argument("--all", action="store_true", help="run all mandatory attacks")
    ontology_parser = subparsers.add_parser("ontology", help="resolve public ontology mappings")
    ontology_subparsers = ontology_parser.add_subparsers(dest="ontology_command")
    ontology_sync_parser = ontology_subparsers.add_parser("sync", help="plan a bounded ontology metadata sync")
    ontology_sync_parser.add_argument("--dry-run", action="store_true", help="do not contact official endpoints")
    repository_parser = subparsers.add_parser("repository", help="inspect public repository metadata")
    repository_subparsers = repository_parser.add_subparsers(dest="repository_command")
    repository_sync_parser = repository_subparsers.add_parser("sync", help="plan a bounded repository metadata sync")
    repository_sync_parser.add_argument("--dry-run", action="store_true", help="do not contact public providers")
    search_parser = subparsers.add_parser("search", help="validate and run discovery searches")
    search_subparsers = search_parser.add_subparsers(dest="search_command")
    search_subparsers.add_parser("validate-queries", help="validate the versioned query matrix and date firewall")
    search_run_parser = search_subparsers.add_parser("run", help="run a fixture-backed bounded seed search")
    search_run_parser.add_argument("--scope", choices=("development", "validation"), default="development")
    search_expand_parser = search_subparsers.add_parser(
        "expand", help="expand fixture-backed citation and linked-resource edges"
    )
    search_expand_parser.add_argument("--depth", type=int, choices=(1, 2), default=2)
    search_expand_parser.add_argument("--scope", choices=("development", "validation"), default="development")
    search_subparsers.add_parser("saturation", help="compute fixture-backed search saturation and coverage gaps")

    extract_parser = subparsers.add_parser("extract", help="extract structured experiment semantics")
    extract_subparsers = extract_parser.add_subparsers(dest="extract_command")
    extract_tables_parser = extract_subparsers.add_parser("tables", help="map fixture tables to experiment semantics")
    extract_tables_parser.add_argument("--fixture", action="store_true", help="use the sanitized local table fixture")
    extract_figures_parser = extract_subparsers.add_parser(
        "figures", help="detect figure panels, axes, legends, and curve candidates"
    )
    extract_figures_parser.add_argument("--fixture", action="store_true", help="use the sanitized local figure fixture")
    extract_figures_parser.add_argument(
        "--digitize",
        action="store_true",
        help="also calibrate eligible curve, bar, and scatter candidates",
    )
    extract_experiment_parser = extract_subparsers.add_parser(
        "experiment", help="run deterministic and local/mock experiment extraction"
    )
    extract_experiment_parser.add_argument("--fixture", action="store_true", help="use the sanitized dual-path fixture")
    extract_experiment_parser.add_argument(
        "--dual", action="store_true", help="run both deterministic and local/mock paths"
    )

    evidence_parser = subparsers.add_parser("evidence", help="resolve and reverse-trace evidence locators")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_trace_parser = evidence_subparsers.add_parser(
        "trace", help="resolve fixture assertions and build a conflict graph"
    )
    evidence_trace_parser.add_argument("--fixture", action="store_true", help="use the sanitized evidence fixture")
    evidence_trace_parser.add_argument("--locator", default=None, help="optionally print reverse-trace match count")

    normalize_parser = subparsers.add_parser("normalize", help="normalize units and uncertainty")
    normalize_subparsers = normalize_parser.add_subparsers(dest="normalize_command")
    normalize_units_parser = normalize_subparsers.add_parser(
        "units", help="normalize fixture quantities through the unit registry"
    )
    normalize_units_parser.add_argument("--fixture", action="store_true", help="use the sanitized unit fixture")

    qc_parser = subparsers.add_parser("qc", help="run physical and statistical quality checks")
    qc_subparsers = qc_parser.add_subparsers(dest="qc_command")
    qc_records_parser = qc_subparsers.add_parser(
        "records", help="check fixture records for physical and statistical plausibility"
    )
    qc_records_parser.add_argument("--fixture", action="store_true", help="use the sanitized local QC fixture")
    qc_records_parser.add_argument("--strict", action="store_true", help="run the strict QC profile")

    data_parser = subparsers.add_parser("data", help="policy-gated data operations")
    data_subparsers = data_parser.add_subparsers(dest="data_command")
    data_fetch_parser = data_subparsers.add_parser(
        "fetch", help="fetch fixture assets through the policy and CAS gates"
    )
    data_fetch_parser.add_argument("--fixture", action="store_true", help="use the sanitized local fixture queue")
    data_bronze_parser = data_subparsers.add_parser("build-bronze", help="build an immutable fixture Bronze release")
    data_bronze_parser.add_argument("--fixture", action="store_true", help="use the sanitized Bronze fixture")
    data_silver_parser = data_subparsers.add_parser("build-silver", help="build an immutable fixture Silver release")
    data_silver_parser.add_argument("--fixture", action="store_true", help="use the sanitized Silver fixture")
    data_gold_parser = data_subparsers.add_parser("build-gold-auto", help="build an audited fixture Gold-auto subset")
    data_gold_parser.add_argument("--fixture", action="store_true", help="use the sanitized Gold-auto fixture")
    data_provenance_parser = data_subparsers.add_parser(
        "audit-provenance", help="audit real open observations against their raw source cells"
    )
    data_provenance_parser.add_argument(
        "--strict", action="store_true", help="require row-level real-source provenance"
    )
    data_fulltext_multicore_parser = data_subparsers.add_parser(
        "audit-fulltext-multicore",
        help="audit a CC-BY full-text multi-core technical benchmark with source-to-cell mapping",
    )
    data_fulltext_multicore_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the downloaded Europe PMC supplementary package and extraction",
    )
    data_fulltext_multicore_parser.add_argument("--strict", action="store_true")
    data_fulltext_gold_parser = data_subparsers.add_parser(
        "audit-fulltext-gold-source",
        help="audit CC-BY human-plasma gold-nanoparticle tables with source-to-cell mapping",
    )
    data_fulltext_gold_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the downloaded Europe PMC PMC7788026 supplementary package",
    )
    data_fulltext_gold_parser.add_argument("--strict", action="store_true")
    data_pxd017052_source_cell_parser = data_subparsers.add_parser(
        "audit-pxd017052-source-cells",
        help="audit PXD017052 CC-BY LFQ cells against its explicit unit-to-particle map",
    )
    data_pxd017052_source_cell_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the downloaded PXD017052 publisher attachments",
    )
    data_pxd017052_source_cell_parser.add_argument("--strict", action="store_true")
    data_r3_uniprot_mapping_parser = data_subparsers.add_parser(
        "map-r3-uniprot-human",
        help="resolve R3 source-native identifiers to uniquely mapped human UniProt accessions",
    )
    data_r3_uniprot_mapping_parser.add_argument(
        "--mapping-root",
        type=Path,
        required=True,
        help="directory where UniProt query and source-cell mapping artifacts will be written",
    )
    data_r3_uniprot_mapping_parser.add_argument("--strict", action="store_true")
    data_r3_common_rank_target_parser = data_subparsers.add_parser(
        "admit-r3-common-rank-target",
        help="build a source-local rank target ledger across the three R3 human-plasma studies",
    )
    data_r3_common_rank_target_parser.add_argument(
        "--output-data-root",
        type=Path,
        required=True,
        help="directory where the row-level common-target ledger will be written",
    )
    data_r3_common_rank_target_parser.add_argument("--strict", action="store_true")
    data_r3_uniprot_sequence_parser = data_subparsers.add_parser(
        "build-r3-uniprot-sequence-features",
        help="build release-fixed UniProt sequence descriptors for the R3 common target",
    )
    data_r3_uniprot_sequence_parser.add_argument(
        "--feature-root",
        type=Path,
        required=True,
        help="directory where exact UniProt FASTA responses and feature table will be written",
    )
    data_r3_uniprot_sequence_parser.add_argument("--strict", action="store_true")
    data_r3_analysis_protocol_parser = data_subparsers.add_parser(
        "freeze-r3-analysis-protocol",
        help="freeze R3 common-target study-held-out partitions and model-selection rules",
    )
    data_r3_analysis_protocol_parser.add_argument(
        "--output-data-root",
        type=Path,
        required=True,
        help="directory containing the immutable row-level R3 common-target ledger",
    )
    data_r3_analysis_protocol_parser.add_argument("--strict", action="store_true")
    data_r3_model_evaluation_parser = data_subparsers.add_parser(
        "evaluate-r3-common-rank-models",
        help="execute the frozen R3 study-held-out sequence-only benchmark",
    )
    data_r3_model_evaluation_parser.add_argument(
        "--output-data-root",
        type=Path,
        required=True,
        help="registry-fixed data/raw directory containing the immutable R3 target ledger",
    )
    data_r3_model_evaluation_parser.add_argument(
        "--feature-root",
        type=Path,
        required=True,
        help="registry-fixed directory containing the exact UniProt feature table",
    )
    data_r3_model_evaluation_parser.add_argument("--strict", action="store_true")
    data_r3_silver_source_parser = data_subparsers.add_parser(
        "audit-r3-silver-plasma-source",
        help="audit the CC-BY silver-nanoparticle human-plasma LFQ source at cell level",
    )
    data_r3_silver_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the downloaded PMC6592156 supplementary package and extraction",
    )
    data_r3_silver_source_parser.add_argument(
        "--output-root",
        type=Path,
        help="optional fresh output directory for an external source-audit receipt",
    )
    data_r3_silver_source_parser.add_argument("--strict", action="store_true")
    data_r4_edinburgh_source_parser = data_subparsers.add_parser(
        "audit-r4-edinburgh-clinical-source",
        help="audit a CC-BY clinical human-plasma nanoparticle-enrichment source without merging it into R3",
    )
    data_r4_edinburgh_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified Edinburgh DataShare source assets",
    )
    data_r4_edinburgh_source_parser.add_argument("--strict", action="store_true")
    data_r4_small_molecule_source_parser = data_subparsers.add_parser(
        "audit-r4-small-molecule-corona-source",
        help="audit the CC-BY PMC11544298 human-plasma corona source for a separately frozen R4 protocol",
    )
    data_r4_small_molecule_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PMC11544298 package and extracted workbooks",
    )
    data_r4_small_molecule_source_parser.add_argument("--strict", action="store_true")
    data_r4_pmc13106918_source_parser = data_subparsers.add_parser(
        "audit-r4-pmc13106918-source",
        help="audit the license-resolved PMC13106918 technical corona source",
    )
    data_r4_pmc13106918_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PMC13106918 package and extracted MaxQuant files",
    )
    data_r4_pmc13106918_source_parser.add_argument("--strict", action="store_true")
    data_r4_pmc13106918_verify_parser = data_subparsers.add_parser(
        "verify-r4-pmc13106918-source",
        help="verify the frozen PMC13106918 technical source audit receipt",
    )
    data_r4_pmc13106918_verify_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PMC13106918 package and extracted MaxQuant files",
    )
    data_r4_pmc13106918_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pxd068107_source_parser = data_subparsers.add_parser(
        "audit-r4-pxd068107-source",
        help="audit the CC0 paper-attached PXD068107 technical source",
    )
    data_r4_pxd068107_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PXD068107 BioStudies source workbooks",
    )
    data_r4_pxd068107_source_parser.add_argument("--strict", action="store_true")
    data_r4_pxd068107_verify_parser = data_subparsers.add_parser(
        "verify-r4-pxd068107-source",
        help="verify the frozen PXD068107 source audit receipt",
    )
    data_r4_pxd068107_verify_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PXD068107 BioStudies source workbooks",
    )
    data_r4_pxd068107_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pmc3252235_source_parser = data_subparsers.add_parser(
        "audit-r4-pmc3252235-source",
        help="audit and preserve the negative decision for the PNNL full-text human-plasma source",
    )
    data_r4_pmc3252235_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PMC3252235 supplementary XLS",
    )
    data_r4_pmc3252235_source_parser.add_argument("--strict", action="store_true")
    data_r4_pmc3252235_verify_parser = data_subparsers.add_parser(
        "verify-r4-pmc3252235-source",
        help="verify the frozen PMC3252235 negative source-screen receipt",
    )
    data_r4_pmc3252235_verify_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PMC3252235 supplementary XLS",
    )
    data_r4_pmc3252235_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pxd064962_source_parser = data_subparsers.add_parser(
        "audit-r4-pxd064962-source",
        help="audit the CC0 PXD064962 low-coverage source for secondary sensitivity work",
    )
    data_r4_pxd064962_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PXD064962 proteinGroups and summary files",
    )
    data_r4_pxd064962_source_parser.add_argument("--strict", action="store_true")
    data_r4_pxd064962_verify_parser = data_subparsers.add_parser(
        "verify-r4-pxd064962-source",
        help="verify the frozen PXD064962 source audit receipt",
    )
    data_r4_pxd064962_verify_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PXD064962 proteinGroups and summary files",
    )
    data_r4_pxd064962_verify_parser.add_argument("--strict", action="store_true")
    data_r4_manchester_source_parser = data_subparsers.add_parser(
        "audit-r4-manchester-nanoomic-source",
        help="audit the independent Manchester longitudinal nano-omics source for analysis-only OOD",
    )
    data_r4_manchester_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified author-repository matrices",
    )
    data_r4_manchester_source_parser.add_argument("--strict", action="store_true")
    data_r4_manchester_verify_parser = data_subparsers.add_parser(
        "verify-r4-manchester-nanoomic-source",
        help="verify the Manchester analysis-only source audit receipt",
    )
    data_r4_manchester_verify_parser.add_argument(
        "--assets-root", type=Path, required=True, help="fixed author-repository matrix root"
    )
    data_r4_manchester_verify_parser.add_argument("--strict", action="store_true")
    data_r4_manchester_ood_parser = data_subparsers.add_parser(
        "evaluate-r4-manchester-nanoomic-ood",
        help="execute frozen exploratory OOD on the Manchester longitudinal matrix",
    )
    data_r4_manchester_ood_parser.add_argument("--strict", action="store_true")
    data_r4_manchester_ood_verify_parser = data_subparsers.add_parser(
        "verify-r4-manchester-nanoomic-ood",
        help="verify the Manchester OOD receipt",
    )
    data_r4_manchester_ood_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pxd017052_nsclc_source_parser = data_subparsers.add_parser(
        "audit-r4-pxd017052-nsclc-source",
        help="audit the paper-attached 141-subject PXD017052 NSCLC corona matrix",
    )
    data_r4_pxd017052_nsclc_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified Supplementary Data 5 workbook",
    )
    data_r4_pxd017052_nsclc_source_parser.add_argument("--strict", action="store_true")
    data_r4_pxd017052_nsclc_verify_parser = data_subparsers.add_parser(
        "verify-r4-pxd017052-nsclc-source",
        help="verify the frozen 141-subject PXD017052 NSCLC source receipt",
    )
    data_r4_pxd017052_nsclc_verify_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified Supplementary Data 5 workbook",
    )
    data_r4_pxd017052_nsclc_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pxd017052_nsclc_ood_parser = data_subparsers.add_parser(
        "evaluate-r4-pxd017052-nsclc-biological-ood",
        help="run the frozen exploratory OOD analysis on the 141-subject cohort",
    )
    data_r4_pxd017052_nsclc_ood_parser.add_argument("--strict", action="store_true")
    data_r4_pxd017052_nsclc_ood_verify_parser = data_subparsers.add_parser(
        "verify-r4-pxd017052-nsclc-biological-ood",
        help="verify the frozen 141-subject biological OOD receipt",
    )
    data_r4_pxd017052_nsclc_ood_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pmc13106918_ood_parser = data_subparsers.add_parser(
        "evaluate-r4-pmc13106918-technical-ood",
        help="run the frozen author-run technical OOD analysis for PMC13106918",
    )
    data_r4_pmc13106918_ood_parser.add_argument("--strict", action="store_true")
    data_r4_pmc13106918_ood_verify_parser = data_subparsers.add_parser(
        "verify-r4-pmc13106918-technical-ood",
        help="verify the frozen PMC13106918 technical OOD receipt",
    )
    data_r4_pmc13106918_ood_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pxd068107_ood_parser = data_subparsers.add_parser(
        "evaluate-r4-pxd068107-technical-ood",
        help="run the frozen author-run technical OOD analysis for PXD068107",
    )
    data_r4_pxd068107_ood_parser.add_argument("--strict", action="store_true")
    data_r4_pxd068107_ood_verify_parser = data_subparsers.add_parser(
        "verify-r4-pxd068107-technical-ood",
        help="verify the frozen PXD068107 technical OOD receipt",
    )
    data_r4_pxd068107_ood_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pmc10257194_source_parser = data_subparsers.add_parser(
        "audit-r4-pmc10257194-paper-source",
        help="audit the analysis-only PMC10257194 paper-attached NaY-PPC cohort",
    )
    data_r4_pmc10257194_source_parser.add_argument("--strict", action="store_true")
    data_r4_pmc10257194_source_verify_parser = data_subparsers.add_parser(
        "verify-r4-pmc10257194-paper-source",
        help="verify the PMC10257194 paper-source audit receipt",
    )
    data_r4_pmc10257194_source_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pmc10257194_ood_parser = data_subparsers.add_parser(
        "evaluate-r4-pmc10257194-paper-ood",
        help="execute frozen exploratory OOD on the 45-subject PMC10257194 paper cohort",
    )
    data_r4_pmc10257194_ood_parser.add_argument("--strict", action="store_true")
    data_r4_pmc10257194_ood_verify_parser = data_subparsers.add_parser(
        "verify-r4-pmc10257194-paper-ood",
        help="verify the PMC10257194 paper OOD receipt",
    )
    data_r4_pmc10257194_ood_verify_parser.add_argument("--strict", action="store_true")
    data_r4_three_lab_parser = data_subparsers.add_parser(
        "audit-r4-three-lab-common-target",
        help="verify the three independent CC-BY laboratory common-target admission",
    )
    data_r4_three_lab_parser.add_argument("--strict", action="store_true")
    data_r4_three_lab_verify_parser = data_subparsers.add_parser(
        "verify-r4-three-lab-common-target",
        help="verify the frozen three-laboratory common-target receipt",
    )
    data_r4_three_lab_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t192_parser = data_subparsers.add_parser(
        "audit-r4-t192-three-lab-common-target",
        help="audit the frozen redistributable Edinburgh-Dalian-UCD common target",
    )
    data_r4_t192_parser.add_argument("--strict", action="store_true")
    data_r4_t192_verify_parser = data_subparsers.add_parser(
        "verify-r4-t192-three-lab-common-target",
        help="verify the frozen T192 three-laboratory common-target receipt",
    )
    data_r4_t192_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t249_parser = data_subparsers.add_parser(
        "audit-r4-t249-four-lab-common-target",
        help="audit the four-source paper-derived common target",
    )
    data_r4_t249_parser.add_argument("--strict", action="store_true")
    data_r4_t249_verify_parser = data_subparsers.add_parser(
        "verify-r4-t249-four-lab-common-target",
        help="verify the frozen T249 four-source common-target receipt",
    )
    data_r4_t249_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t258_parser = data_subparsers.add_parser(
        "audit-r4-t258-source-unit-endpoint-license",
        help="audit source-unit semantics, endpoint compatibility and reuse licenses",
    )
    data_r4_t258_parser.add_argument("--strict", action="store_true")
    data_r4_t258_verify_parser = data_subparsers.add_parser(
        "verify-r4-t258-source-unit-endpoint-license",
        help="verify the frozen T258 source-unit and endpoint audit receipt",
    )
    data_r4_t258_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t250_parser = data_subparsers.add_parser(
        "evaluate-r4-t250-four-lab-common-target",
        help="execute the frozen four-source paper-data common-target analysis",
    )
    data_r4_t250_parser.add_argument("--strict", action="store_true")
    data_r4_t250_verify_parser = data_subparsers.add_parser(
        "verify-r4-t250-four-lab-common-target",
        help="verify the frozen T250 four-source execution receipt",
    )
    data_r4_t250_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t265_parser = data_subparsers.add_parser(
        "evaluate-r4-t265-biological-common-target",
        help="execute the frozen three-cohort biological common-target analysis",
    )
    data_r4_t265_parser.add_argument("--strict", action="store_true")
    data_r4_t265_verify_parser = data_subparsers.add_parser(
        "verify-r4-t265-biological-common-target",
        help="verify the frozen T265 biological common-target execution receipt",
    )
    data_r4_t265_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t273_parser = data_subparsers.add_parser(
        "evaluate-r4-t273-biological-unit-primary",
        help="execute the biological-unit-primary T273 reanalysis with grouped nested selection",
    )
    data_r4_t273_parser.add_argument("--strict", action="store_true")
    data_r4_t273_verify_parser = data_subparsers.add_parser(
        "verify-r4-t273-biological-unit-primary",
        help="verify the T273 biological-unit-primary execution receipt",
    )
    data_r4_t273_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t193_parser = data_subparsers.add_parser(
        "evaluate-r4-t193-three-lab-prefrozen-target",
        help="execute the frozen T193 study-held-out analysis on the pre-T192 R3 target universe",
    )
    data_r4_t193_parser.add_argument("--strict", action="store_true")
    data_r4_t193_verify_parser = data_subparsers.add_parser(
        "verify-r4-t193-three-lab-prefrozen-target",
        help="verify the frozen T193 three-source execution receipt",
    )
    data_r4_t193_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t194_parser = data_subparsers.add_parser(
        "evaluate-r4-t194-fulltext-core-facility",
        help="execute the frozen full-text PMC9633814 core-facility portability analysis",
    )
    data_r4_t194_parser.add_argument("--strict", action="store_true")
    data_r4_t194_verify_parser = data_subparsers.add_parser(
        "verify-r4-t194-fulltext-core-facility",
        help="verify the frozen T194 full-text core-facility execution receipt",
    )
    data_r4_t194_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t195_parser = data_subparsers.add_parser(
        "evaluate-r4-t195-three-lab-common-target",
        help="execute the frozen strict-common-target three-laboratory sensitivity analysis",
    )
    data_r4_t195_parser.add_argument("--strict", action="store_true")
    data_r4_t195_verify_parser = data_subparsers.add_parser(
        "verify-r4-t195-three-lab-common-target",
        help="verify the frozen T195 strict-common-target execution receipt",
    )
    data_r4_t195_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t282_parser = data_subparsers.add_parser(
        "evaluate-r4-t282-t195-replicate-aware-refit",
        help="execute the T195 primary route after pre-model technical-replicate collapse",
    )
    data_r4_t282_parser.add_argument("--strict", action="store_true")
    data_r4_t282_verify_parser = data_subparsers.add_parser(
        "verify-r4-t282-t195-replicate-aware-refit",
        help="verify the T282 replicate-aware T195 primary-route receipt",
    )
    data_r4_t282_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t197_parser = data_subparsers.add_parser(
        "evaluate-r4-t197-source-availability",
        help="execute the source-availability-aware outer-fold target sensitivity",
    )
    data_r4_t197_parser.add_argument("--strict", action="store_true")
    data_r4_t197_verify_parser = data_subparsers.add_parser(
        "verify-r4-t197-source-availability",
        help="verify the T197 source-availability-aware execution receipt",
    )
    data_r4_t197_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t238_parser = data_subparsers.add_parser(
        "evaluate-r4-t238-four-source-availability",
        help="execute four-source development-only target-membership sensitivity",
    )
    data_r4_t238_parser.add_argument("--strict", action="store_true")
    data_r4_t238_verify_parser = data_subparsers.add_parser(
        "verify-r4-t238-four-source-availability",
        help="verify the T238 four-source availability receipt",
    )
    data_r4_t238_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t255_parser = data_subparsers.add_parser(
        "evaluate-r4-t255-cluster-uncertainty",
        help="execute the frozen T255 measurement-batch uncertainty extension",
    )
    data_r4_t255_parser.add_argument("--strict", action="store_true")
    data_r4_t255_verify_parser = data_subparsers.add_parser(
        "verify-r4-t255-cluster-uncertainty",
        help="verify the frozen T255 cluster-uncertainty receipt",
    )
    data_r4_t255_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t198_parser = data_subparsers.add_parser(
        "evaluate-r4-t198-paper-cohort-missingness",
        help="execute the paper-cohort threshold and missingness sensitivity",
    )
    data_r4_t198_parser.add_argument("--strict", action="store_true")
    data_r4_t198_verify_parser = data_subparsers.add_parser(
        "verify-r4-t198-paper-cohort-missingness",
        help="verify the T198 paper-cohort missingness receipt",
    )
    data_r4_t198_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t200_parser = data_subparsers.add_parser(
        "evaluate-r4-t200-statistical-closure",
        help="execute the T197/T198 statistical-contract closure and stratified missingness audit",
    )
    data_r4_t200_parser.add_argument("--strict", action="store_true")
    data_r4_t200_verify_parser = data_subparsers.add_parser(
        "verify-r4-t200-statistical-closure",
        help="verify the T200 statistical-closure receipt",
    )
    data_r4_t200_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t217_parser = data_subparsers.add_parser(
        "evaluate-r4-t217-statistical-amendment",
        help="freeze and audit the project-wide statistical role hierarchy for paper-derived routes",
    )
    data_r4_t217_parser.add_argument("--strict", action="store_true")
    data_r4_t217_verify_parser = data_subparsers.add_parser(
        "verify-r4-t217-statistical-amendment",
        help="verify the T217 statistical-amendment receipt",
    )
    data_r4_t217_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t222_parser = data_subparsers.add_parser(
        "audit-r4-t222-paper-data-fallback",
        help="audit frozen full-text, supplementary-table and public-accession data routes",
    )
    data_r4_t222_parser.add_argument("--strict", action="store_true")
    data_r4_t222_verify_parser = data_subparsers.add_parser(
        "verify-r4-t222-paper-data-fallback",
        help="verify the T222 published-paper data fallback receipt",
    )
    data_r4_t222_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t214_parser = data_subparsers.add_parser(
        "evaluate-r4-t214-source-heterogeneity",
        help="audit source- and study-level heterogeneity without refitting frozen models",
    )
    data_r4_t214_parser.add_argument("--strict", action="store_true")
    data_r4_t214_verify_parser = data_subparsers.add_parser(
        "verify-r4-t214-source-heterogeneity",
        help="verify the T214 source-heterogeneity audit receipt",
    )
    data_r4_t214_verify_parser.add_argument("--strict", action="store_true")
    data_r4_t284_parser = data_subparsers.add_parser(
        "evaluate-r4-t284-paper-ood-synthesis",
        help="summarize frozen paper-derived OOD effects without cross-route pooling",
    )
    data_r4_t284_parser.add_argument("--strict", action="store_true")
    data_r4_t284_verify_parser = data_subparsers.add_parser(
        "verify-r4-t284-paper-ood-synthesis",
        help="verify the T284 paper-OOD synthesis receipt",
    )
    data_r4_t284_verify_parser.add_argument("--strict", action="store_true")
    data_r4_dalian_source_parser = data_subparsers.add_parser(
        "audit-r4-dalian-plasma-corona-source",
        help="audit the CC0 PXD060795 human-plasma corona workbook for R4 small-n sensitivity work",
    )
    data_r4_dalian_source_parser.add_argument(
        "--assets-root",
        type=Path,
        required=True,
        help="directory containing the byte-verified PXD060795 result workbook",
    )
    data_r4_dalian_source_parser.add_argument("--strict", action="store_true")
    data_r4_dalian_sensitivity_parser = data_subparsers.add_parser(
        "evaluate-r4-dalian-plasma-corona-sensitivity",
        help="execute the frozen small-n PXD060795 sensitivity analysis",
    )
    data_r4_dalian_sensitivity_parser.add_argument("--strict", action="store_true")
    data_r4_pxd064962_sensitivity_parser = data_subparsers.add_parser(
        "evaluate-r4-pxd064962-low-coverage-sensitivity",
        help="execute the frozen PXD064962 low-coverage sensitivity analysis",
    )
    data_r4_pxd064962_sensitivity_parser.add_argument("--strict", action="store_true")
    data_r4_pxd064962_sensitivity_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="optional repository-relative output directory for an independent rerun",
    )
    data_r4_pxd064962_sensitivity_verify_parser = data_subparsers.add_parser(
        "verify-r4-pxd064962-low-coverage-sensitivity",
        help="verify the frozen PXD064962 low-coverage sensitivity receipt",
    )
    data_r4_pxd064962_sensitivity_verify_parser.add_argument("--strict", action="store_true")
    data_r4_pxd064962_sensitivity_verify_parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="optional repository-relative output directory to verify",
    )
    data_r4_small_molecule_ood_parser = data_subparsers.add_parser(
        "evaluate-r4-small-molecule-corona-ood",
        help="run the frozen author-run public OOD evaluation on the separate PMC11544298 candidate",
    )
    data_r4_small_molecule_ood_parser.add_argument(
        "--source-assets-root",
        type=Path,
        default=Path("data/raw/r4_candidate_pmc11544298"),
        help="directory containing the byte-verified R4 source assets",
    )
    data_r4_small_molecule_ood_parser.add_argument("--strict", action="store_true")
    data_r4_effective_n_parser = data_subparsers.add_parser(
        "audit-r4-ood-effective-n",
        help="audit R4 OOD effective sampling units and missingness without changing the primary endpoint",
    )
    data_r4_effective_n_parser.add_argument("--strict", action="store_true")
    data_r4_effective_n_verify_parser = data_subparsers.add_parser(
        "verify-r4-ood-effective-n",
        help="verify the frozen R4 effective-n and missingness audit receipt",
    )
    data_r4_effective_n_verify_parser.add_argument("--strict", action="store_true")
    data_r4_cluster_parser = data_subparsers.add_parser(
        "audit-r4-ood-cluster-sensitivity",
        help="audit R4 OOD biological-unit cluster sensitivity and paired ablation",
    )
    data_r4_cluster_parser.add_argument("--strict", action="store_true")
    data_r4_cluster_verify_parser = data_subparsers.add_parser(
        "verify-r4-ood-cluster-sensitivity",
        help="verify the frozen R4 OOD cluster sensitivity receipt",
    )
    data_r4_cluster_verify_parser.add_argument("--strict", action="store_true")
    data_r3_silver_ood_parser = data_subparsers.add_parser(
        "evaluate-r3-silver-external-ood",
        help="run the frozen author-run external-laboratory OOD evaluation on the silver source",
    )
    data_r3_silver_ood_parser.add_argument(
        "--output-data-root", type=Path, required=True, help="registry-fixed data/raw directory"
    )
    data_r3_silver_ood_parser.add_argument(
        "--feature-root",
        type=Path,
        required=True,
        help="registry-fixed R3 sequence-feature directory",
    )
    data_r3_silver_ood_parser.add_argument(
        "--silver-assets-root",
        type=Path,
        required=True,
        help="registry-fixed silver-source asset directory",
    )
    data_r3_silver_ood_parser.add_argument(
        "--output-root",
        type=Path,
        help="optional fresh output directory for an external OOD receipt",
    )
    data_r3_silver_ood_parser.add_argument("--strict", action="store_true")
    data_external_intake_parser = data_subparsers.add_parser(
        "preflight-external-source-intake",
        help="verify an externally supplied source package without admitting a target",
    )
    data_external_intake_parser.add_argument(
        "--manifest", type=Path, required=True, help="external contributor manifest JSON"
    )
    data_external_intake_parser.add_argument(
        "--assets-root", type=Path, required=True, help="root containing contributor source assets"
    )
    data_external_intake_parser.add_argument("--strict", action="store_true")
    data_external_verification_parser = data_subparsers.add_parser(
        "preflight-external-verification",
        help=("verify external evaluation, reproduction and editorial receipts without accepting them"),
    )
    data_external_verification_parser.add_argument(
        "--bundle", type=Path, required=True, help="external verification bundle JSON"
    )
    data_external_verification_parser.add_argument(
        "--documents-root", type=Path, required=True, help="root containing external receipt files"
    )
    data_external_verification_parser.add_argument("--strict", action="store_true")
    data_r4_receipt_parser = data_subparsers.add_parser(
        "preflight-r4-external-receipts",
        help=("verify R4 evaluator, reproduction and adoption receipts without accepting their claims"),
    )
    data_r4_receipt_parser.add_argument("--bundle", type=Path, required=True, help="R4 external receipt bundle JSON")
    data_r4_receipt_parser.add_argument(
        "--documents-root", type=Path, required=True, help="root containing R4 receipt files"
    )
    data_r4_receipt_parser.add_argument(
        "--receipt-out", type=Path, required=True, help="structural preflight receipt JSON"
    )
    data_r4_receipt_parser.add_argument("--strict", action="store_true")
    data_r4_t260_receipt_parser = data_subparsers.add_parser(
        "preflight-r4-t260-external-receipts",
        help="preflight r10.45 external evaluator, reproduction and adoption receipts",
    )
    data_r4_t260_receipt_parser.add_argument(
        "--bundle", type=Path, required=True, help="T260 external receipt bundle JSON"
    )
    data_r4_t260_receipt_parser.add_argument(
        "--documents-root", type=Path, required=True, help="root containing T260 external receipt files"
    )
    data_r4_t260_receipt_parser.add_argument(
        "--receipt-out", type=Path, required=True, help="T260 structural preflight receipt JSON"
    )
    data_r4_t260_receipt_parser.add_argument("--strict", action="store_true")
    data_r4_t279_receipt_parser = data_subparsers.add_parser(
        "preflight-r4-t279-external-receipts",
        help="preflight r10.56 external evaluator, reproduction and adoption receipts",
    )
    data_r4_t279_receipt_parser.add_argument(
        "--bundle", type=Path, required=True, help="T279 external receipt bundle JSON"
    )
    data_r4_t279_receipt_parser.add_argument(
        "--documents-root", type=Path, required=True, help="root containing T279 external receipt files"
    )
    data_r4_t279_receipt_parser.add_argument(
        "--receipt-out", type=Path, required=True, help="T279 structural preflight receipt JSON"
    )
    data_r4_t279_receipt_parser.add_argument("--strict", action="store_true")
    data_r4_t286_receipt_parser = data_subparsers.add_parser(
        "preflight-r4-t286-external-receipts",
        help="preflight r10.57 external evaluator, reproduction and adoption receipts",
    )
    data_r4_t286_receipt_parser.add_argument(
        "--bundle", type=Path, required=True, help="T286 external receipt bundle JSON"
    )
    data_r4_t286_receipt_parser.add_argument(
        "--documents-root", type=Path, required=True, help="root containing T286 external receipt files"
    )
    data_r4_t286_receipt_parser.add_argument(
        "--receipt-out", type=Path, required=True, help="T286 structural preflight receipt JSON"
    )
    data_r4_t286_receipt_parser.add_argument("--strict", action="store_true")
    data_external_signature_parser = data_subparsers.add_parser(
        "verify-external-verification-signatures",
        help="verify detached external-receipt signatures without accepting their claims",
    )
    data_external_signature_parser.add_argument(
        "--bundle", type=Path, required=True, help="preflighted external verification bundle JSON"
    )
    data_external_signature_parser.add_argument(
        "--documents-root", type=Path, required=True, help="root containing external receipt files"
    )
    data_external_signature_parser.add_argument(
        "--signature-manifest", type=Path, required=True, help="detached-signature manifest JSON"
    )
    data_external_signature_parser.add_argument(
        "--signatures-root", type=Path, required=True, help="root containing detached signatures"
    )
    data_external_signature_parser.add_argument(
        "--trusted-signer-registry",
        type=Path,
        required=True,
        help="scope-owner-approved trusted signer registry JSON",
    )
    data_external_signature_parser.add_argument(
        "--trusted-keys-root", type=Path, required=True, help="root containing approved public keys"
    )
    data_external_signature_parser.add_argument(
        "--receipt-out", type=Path, required=True, help="new controlled signature receipt JSON"
    )
    data_external_signature_parser.add_argument("--strict", action="store_true")
    stats_parser = subparsers.add_parser("stats", help="freeze and validate empirical analysis contracts")
    stats_subparsers = stats_parser.add_subparsers(dest="stats_command")
    stats_validate_plan_parser = stats_subparsers.add_parser(
        "validate-plan", help="validate the frozen outcome-free empirical analysis plan"
    )
    stats_validate_plan_parser.add_argument("--strict", action="store_true")
    data_validate_parser = data_subparsers.add_parser("validate", help="validate a normalized data release")
    data_validate_subparsers = data_validate_parser.add_subparsers(dest="data_validate_command")
    data_validate_silver_parser = data_validate_subparsers.add_parser(
        "silver", help="validate the immutable fixture Silver release"
    )
    data_validate_silver_parser.add_argument(
        "--fixture", action="store_true", help="validate the sanitized Silver release"
    )
    data_validate_gold_parser = data_validate_subparsers.add_parser(
        "gold-auto", help="validate the immutable fixture Gold-auto release"
    )
    data_validate_gold_parser.add_argument(
        "--fixture", action="store_true", help="validate the sanitized Gold-auto release"
    )
    review_parser = subparsers.add_parser("review", help="export deterministic consensus and expert-review packets")
    review_subparsers = review_parser.add_subparsers(dest="review_command")
    review_export_parser = review_subparsers.add_parser("export", help="export blinded stratified review packets")
    review_export_parser.add_argument("--sample", choices=("stratified",), default="stratified")

    benchmark_parser = subparsers.add_parser("benchmark", help="run deterministic quality benchmarks")
    benchmark_subparsers = benchmark_parser.add_subparsers(dest="benchmark_command")
    benchmark_grade_parser = benchmark_subparsers.add_parser(
        "grade", help="grade deterministic benchmark submissions and abstention metrics"
    )
    benchmark_grade_parser.add_argument("--fixture", action="store_true", help="use the sanitized grading fixture")
    benchmark_baseline_parser = benchmark_subparsers.add_parser(
        "run-baselines", help="run deterministic simple statistical baselines"
    )
    benchmark_baseline_parser.add_argument(
        "--group",
        choices=("simple", "representation"),
        default=None,
        help="baseline group to execute",
    )
    benchmark_build_parser = benchmark_subparsers.add_parser(
        "build", help="build leakage-safe BioInterfaceBench task instances"
    )
    benchmark_build_parser.add_argument("--dev", action="store_true", help="build the development benchmark namespace")
    benchmark_build_parser.add_argument("--fixture", action="store_true", help="use the sanitized benchmark fixture")
    benchmark_subparsers.add_parser("extraction", help="run the extraction calibration and G2 benchmark")
    benchmark_real_parser = benchmark_subparsers.add_parser(
        "evaluate-real", help="evaluate declared raw-cell locators by held-out real study"
    )
    benchmark_real_parser.add_argument("--strict", action="store_true")
    model_parser = subparsers.add_parser("model", help="evaluate the real-model evidence gate")
    model_subparsers = model_parser.add_subparsers(dest="model_command")
    model_real_parser = model_subparsers.add_parser(
        "evaluate-real", help="audit cross-study compatibility before any real model fit"
    )
    model_real_parser.add_argument("--strict", action="store_true")
    model_source_audit_parser = model_subparsers.add_parser(
        "audit-source-candidates",
        help="verify real raw-data candidates without promoting incompatible targets",
    )
    model_source_audit_parser.add_argument("--strict", action="store_true")
    model_source_discovery_parser = model_subparsers.add_parser(
        "audit-source-discovery",
        help="audit screened public sources without consuming reserved lockbox content",
    )
    model_source_discovery_parser.add_argument("--strict", action="store_true")
    model_proteomics_preflight_parser = model_subparsers.add_parser(
        "audit-proteomics-sources",
        help="preflight public protein-corona sources without freezing a model target",
    )
    model_proteomics_preflight_parser.add_argument("--strict", action="store_true")
    model_proteomics_acquire_parser = model_subparsers.add_parser(
        "acquire-proteomics-sources",
        help="resume and verify the fixed public protein-corona source transfer",
    )
    model_proteomics_acquire_parser.add_argument("--strict", action="store_true")
    model_proteomics_acquire_parser.add_argument(
        "--source",
        action="append",
        choices=("PRIDE-PXD017776", "PRIDE-PXD052701", "PRIDE-PXD032162"),
        help="stage only one declared PRIDE source; repeat for multiple sources",
    )
    model_proteomics_acquisition_audit_parser = model_subparsers.add_parser(
        "audit-proteomics-acquisition",
        help="freeze a receipt only after every declared proteomics asset is verified",
    )
    model_proteomics_acquisition_audit_parser.add_argument("--strict", action="store_true")
    model_proteomics_profile_parser = model_subparsers.add_parser(
        "profile-proteomics-results",
        help="profile acquired author results without freezing a predictive target",
    )
    model_proteomics_profile_parser.add_argument("--strict", action="store_true")
    model_cc0_target_admission_parser = model_subparsers.add_parser(
        "audit-cc0-target-admission",
        help="screen CC0 protein-corona candidates without freezing a predictive target",
    )
    model_cc0_target_admission_parser.add_argument("--strict", action="store_true")
    model_cc0_target_discovery_parser = model_subparsers.add_parser(
        "audit-cc0-target-discovery",
        help="record an additional CC0 screening tranche without freezing a target",
    )
    model_cc0_target_discovery_parser.add_argument("--strict", action="store_true")
    model_cc0_target_rescreen_parser = model_subparsers.add_parser(
        "audit-cc0-target-rescreen",
        help="record a bounded CC0 PRIDE rescreen without freezing a target",
    )
    model_cc0_target_rescreen_parser.add_argument("--strict", action="store_true")
    model_two_lab_pair_parser = model_subparsers.add_parser(
        "audit-two-lab-corona-pair",
        help="audit a two-laboratory human-plasma corona candidate pair without admission",
    )
    model_two_lab_pair_parser.add_argument("--strict", action="store_true")
    model_two_lab_asset_parser = model_subparsers.add_parser(
        "audit-two-lab-corona-assets",
        help="audit named first-party corona supplementary assets without admission",
    )
    model_two_lab_asset_parser.add_argument("--strict", action="store_true")
    model_t129_current_target_evidence_parser = model_subparsers.add_parser(
        "audit-t129-current-target-evidence",
        help="consolidate all current T129 receipts without promoting a target",
    )
    model_t129_current_target_evidence_parser.add_argument("--strict", action="store_true")
    model_license_bound_source_maps_parser = model_subparsers.add_parser(
        "audit-license-bound-source-maps",
        help="audit licence-bound protein-corona mappings without promoting a target",
    )
    model_license_bound_source_maps_parser.add_argument("--strict", action="store_true")
    model_pxd017052_source_data_parser = model_subparsers.add_parser(
        "audit-pxd017052-source-data",
        help="audit public PXD017052 source data without inferring a particle unit map",
    )
    model_pxd017052_source_data_parser.add_argument("--strict", action="store_true")
    model_pxd017052_complete_attachments_parser = model_subparsers.add_parser(
        "audit-pxd017052-complete-attachments",
        help="correct T131 against the complete PXD017052 publisher attachment set",
    )
    model_pxd017052_complete_attachments_parser.add_argument("--strict", action="store_true")
    model_cc0_pxd030327_parser = model_subparsers.add_parser(
        "audit-cc0-pxd030327-unit-map",
        help="verify corrected PXD030327 source units without admitting a model target",
    )
    model_cc0_pxd030327_parser.add_argument("--strict", action="store_true")
    benchmark_agents_parser = benchmark_subparsers.add_parser(
        "agents", help="run the end-to-end scientific-agent benchmark"
    )
    benchmark_agents_parser.add_argument(
        "--dev", action="store_true", help="run the development agent benchmark namespace"
    )
    benchmark_freeze_parser = benchmark_subparsers.add_parser(
        "freeze-dev", help="freeze the BioInterfaceBench development release"
    )
    benchmark_freeze_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized benchmark freeze fixture"
    )
    subparsers.add_parser("paper-a", help="generate the evidence-linked Paper A benchmark manuscript")
    subparsers.add_parser("paper-b", help="generate the evidence-linked Paper B method manuscript")
    subparsers.add_parser("paper-c-prelock", help="freeze the Paper C scientific-law manuscript before lockbox access")
    manuscript_parser = subparsers.add_parser(
        "manuscript", help="audit manuscript-scoped external evidence and terminology"
    )
    manuscript_subparsers = manuscript_parser.add_subparsers(dest="manuscript_command")
    manuscript_related_work_parser = manuscript_subparsers.add_parser(
        "audit-related-work",
        help="audit the R2 external literature, comparator, and glossary packet",
    )
    manuscript_related_work_parser.add_argument("--strict", action="store_true")
    manuscript_portfolio_parser = manuscript_subparsers.add_parser(
        "audit-portfolio",
        help="audit the R2 merged A+B and results-blind C manuscript routes",
    )
    manuscript_portfolio_parser.add_argument("--strict", action="store_true")
    claim_parser = subparsers.add_parser("claim", help="freeze and preregister exploratory claim tournaments")
    claim_subparsers = claim_parser.add_subparsers(dest="claim_command")
    claim_preregister_parser = claim_subparsers.add_parser(
        "preregister", help="freeze exploratory hypothesis tournament rules"
    )
    claim_preregister_parser.add_argument(
        "--dev", action="store_true", help="use the development-only tournament fixture"
    )
    claim_audit_parser = claim_subparsers.add_parser(
        "audit-manuscripts", help="run the final claim-to-evidence and language audit"
    )
    claim_audit_parser.add_argument("--strict", action="store_true")
    claim_semantics_parser = claim_subparsers.add_parser(
        "audit-semantics",
        help="audit fixture, replay, and scientific-evidence boundaries for round two",
    )
    claim_semantics_parser.add_argument("--strict", action="store_true")
    design_parser = subparsers.add_parser("design", help="run constrained multiobjective design baselines")
    design_subparsers = design_parser.add_subparsers(dest="design_command")
    design_baseline_parser = design_subparsers.add_parser(
        "baseline", help="run the fixture-backed constrained design baseline"
    )
    design_baseline_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized constrained-design fixture"
    )
    design_generative_parser = design_subparsers.add_parser(
        "generative", help="run the gated target-corona conditional generator"
    )
    design_generative_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized generative-design fixture"
    )
    design_audit_parser = design_subparsers.add_parser(
        "audit-candidates", help="audit supported designs and retrospective evidence metadata"
    )
    design_audit_parser.add_argument("--fixture", action="store_true", help="use the sanitized candidate-audit fixture")
    robustness_parser = subparsers.add_parser("robustness", help="run mandatory robustness and ablation analyses")
    robustness_subparsers = robustness_parser.add_subparsers(dest="robustness_command")
    robustness_ablations_parser = robustness_subparsers.add_parser(
        "ablations", help="run the frozen model and data ablation matrix"
    )
    robustness_ablations_parser.add_argument("--all", action="store_true", help="run all mandatory ablations")
    robustness_ood_parser = robustness_subparsers.add_parser(
        "ood", help="run the leave-group OOD and sensitivity suite"
    )
    robustness_ood_parser.add_argument("--all", action="store_true", help="run all frozen OOD group dimensions")
    robustness_bias_parser = robustness_subparsers.add_parser(
        "bias", help="assess publication selection and missingness bias"
    )
    robustness_bias_parser.add_argument("--fixture", action="store_true", help="use the sanitized bias fixture")
    robustness_negative_parser = robustness_subparsers.add_parser(
        "negative-controls", help="run strict negative controls and leakage attacks"
    )
    robustness_negative_parser.add_argument(
        "--strict", action="store_true", help="fail on any critical leakage finding"
    )
    discover_parser = subparsers.add_parser("discover", help="discover development-scope scientific representations")
    discover_subparsers = discover_parser.add_subparsers(dest="discover_command")
    discover_axes_parser = discover_subparsers.add_parser(
        "functional-axes", help="discover stable protein-corona functional axes"
    )
    discover_axes_parser.add_argument("--fixture", action="store_true", help="use the sanitized development fixture")
    discover_mediation_parser = discover_subparsers.add_parser(
        "mediation", help="estimate preregistered material-corona-outcome mediation paths"
    )
    discover_mediation_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized development fixture"
    )
    discover_transfer_parser = discover_subparsers.add_parser(
        "cross-species", help="compare human-mouse and biofluid transfer models"
    )
    discover_transfer_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized development fixture"
    )
    discover_symbolic_parser = discover_subparsers.add_parser(
        "symbolic-laws", help="discover unit-aware symbolic design laws"
    )
    discover_symbolic_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized development fixture"
    )
    discover_protocol_parser = discover_subparsers.add_parser(
        "protocol-effects", help="test protocol correction and reversal hypotheses"
    )
    discover_protocol_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized development fixture"
    )
    discover_counterfactual_parser = discover_subparsers.add_parser(
        "counterfactuals", help="rank supported counterfactuals and explain contradictions"
    )
    discover_counterfactual_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized development fixture"
    )

    train_parser = subparsers.add_parser("train", help="fit declared benchmark models")
    train_subparsers = train_parser.add_subparsers(dest="train_command")
    train_m1_parser = train_subparsers.add_parser("m1", help="fit the hierarchical mixed-effect M1 baseline")
    train_m1_parser.add_argument("--config", default="configs/models/m1.yaml", help="path to the M1 YAML config")
    train_m2_parser = train_subparsers.add_parser("m2", help="fit the direct black-box M2 baseline")
    train_m2_parser.add_argument("--config", default="configs/models/m2.yaml", help="path to the M2 YAML config")
    train_m3_parser = train_subparsers.add_parser("m3", help="fit the static corona mediator M3 baseline")
    train_m3_parser.add_argument("--config", default="configs/models/m3.yaml", help="path to the M3 YAML config")
    train_m4_parser = train_subparsers.add_parser("m4", help="fit the compositional corona M4 baseline")
    train_m4_parser.add_argument("--config", default="configs/models/m4.yaml", help="path to the M4 YAML config")
    train_m5_parser = train_subparsers.add_parser("m5", help="fit the dynamic corona M5 baseline")
    train_m5_parser.add_argument("--config", default="configs/models/m5.yaml", help="path to the M5 YAML config")
    train_m6_parser = train_subparsers.add_parser("m6", help="fit the hierarchical causal-world M6 model")
    train_m6_parser.add_argument("--config", default="configs/models/m6.yaml", help="path to the M6 YAML config")
    train_m7_parser = train_subparsers.add_parser("m7", help="fit the cross-domain invariant-learning M7 comparison")
    train_m7_parser.add_argument("--config", default="configs/models/m7.yaml", help="path to the M7 YAML config")
    train_uncertainty_parser = train_subparsers.add_parser(
        "uncertainty", help="fit calibrated uncertainty and abstention policy"
    )
    train_uncertainty_parser.add_argument(
        "--config",
        default="configs/models/uncertainty.yaml",
        help="path to the uncertainty YAML config",
    )
    train_multimodal_parser = train_subparsers.add_parser(
        "multimodal", help="fit masked multimodal material and document representations"
    )
    train_multimodal_parser.add_argument(
        "--config",
        default="configs/models/multimodal.yaml",
        help="path to the multimodal YAML config",
    )

    report_parser = subparsers.add_parser("report", help="publish reproducible audit reports")
    report_subparsers = report_parser.add_subparsers(dest="report_command")
    report_subparsers.add_parser("data-coverage", help="audit independent-study coverage and missingness")

    omics_parser = subparsers.add_parser("omics", help="triage and process omics metadata")
    omics_subparsers = omics_parser.add_subparsers(dest="omics_command")
    omics_pride_parser = omics_subparsers.add_parser("pride", help="triage PRIDE projects and freeze sample plans")
    omics_pride_subparsers = omics_pride_parser.add_subparsers(dest="omics_pride_command")
    omics_pride_triage_parser = omics_pride_subparsers.add_parser(
        "triage", help="build development-scope PRIDE project cards"
    )
    omics_pride_triage_parser.add_argument("--scope", choices=("development",), default="development")
    omics_convert_parser = omics_subparsers.add_parser("convert", help="convert bounded fixture mass-spec inputs")
    omics_convert_parser.add_argument("--fixture", action="store_true", help="use the sanitized conversion fixture")
    omics_search_parser = omics_subparsers.add_parser("search", help="run the bounded Sage-style fixture search")
    omics_search_parser.add_argument("--fixture", action="store_true", help="use the sanitized Sage search fixture")
    omics_quantify_parser = omics_subparsers.add_parser(
        "quantify", help="run bounded label-free quantification and protein inference"
    )
    omics_quantify_parser.add_argument("--fixture", action="store_true", help="use the sanitized LFQ fixture")
    omics_harmonize_parser = omics_subparsers.add_parser(
        "harmonize-corona", help="harmonize project-preserving protein-corona matrices"
    )
    omics_harmonize_parser.add_argument("--fixture", action="store_true", help="use the sanitized corona fixture")
    omics_qc_parser = omics_subparsers.add_parser("qc-pride", help="run PRIDE project QC and author-result concordance")
    omics_qc_parser.add_argument("--fixture", action="store_true", help="use the sanitized PRIDE QC fixture")
    omics_signatures_parser = omics_subparsers.add_parser(
        "derive-signatures", help="derive fixture-backed cell and immune response signatures"
    )
    omics_signatures_parser.add_argument("--fixture", action="store_true", help="use the sanitized signature fixture")
    omics_links_parser = omics_subparsers.add_parser(
        "link-modalities", help="link corona modules to response signatures"
    )
    omics_links_parser.add_argument("--fixture", action="store_true", help="use the sanitized modality-link fixture")
    omics_geo_parser = omics_subparsers.add_parser("geo", help="discover GEO/SRA biointerface response datasets")
    omics_geo_subparsers = omics_geo_parser.add_subparsers(dest="omics_geo_command")
    omics_geo_discover_parser = omics_geo_subparsers.add_parser(
        "discover", help="discover development-scope GEO/SRA candidates"
    )
    omics_geo_discover_parser.add_argument("--scope", choices=("development",), default="development")
    omics_geo_discover_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized GEO discovery fixture"
    )
    omics_geo_process_parser = omics_geo_subparsers.add_parser(
        "process", help="ingest eligible processed GEO/SRA matrices"
    )
    omics_geo_process_parser.add_argument("--mode", choices=("processed", "raw"), default="processed")
    omics_geo_process_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized GEO processing fixture"
    )

    resolve_parser = subparsers.add_parser("resolve", help="resolve paper and study identities")
    resolve_subparsers = resolve_parser.add_subparsers(dest="resolve_command")
    resolve_subparsers.add_parser("paper-families", help="resolve fixture-backed paper families and conflicts")
    resolve_materials_parser = resolve_subparsers.add_parser(
        "materials", help="resolve fixture-backed material entities and formulations"
    )
    resolve_materials_parser.add_argument("--fixture", action="store_true", help="use the sanitized material fixture")
    resolve_proteins_parser = resolve_subparsers.add_parser(
        "proteins", help="resolve fixture-backed protein identifiers and orthology"
    )
    resolve_proteins_parser.add_argument("--fixture", action="store_true", help="use the sanitized protein fixture")
    resolve_protocols_parser = resolve_subparsers.add_parser(
        "protocols", help="resolve fixture-backed bioenvironment and protocols"
    )
    resolve_protocols_parser.add_argument("--fixture", action="store_true", help="use the sanitized protocol fixture")
    resolve_endpoints_parser = resolve_subparsers.add_parser(
        "endpoints", help="resolve fixture-backed endpoint measurements"
    )
    resolve_endpoints_parser.add_argument("--fixture", action="store_true", help="use the sanitized endpoint fixture")

    split_parser = subparsers.add_parser("split", help="build leakage-safe split group keys")
    split_subparsers = split_parser.add_subparsers(dest="split_command")
    split_groups_parser = split_subparsers.add_parser(
        "build-groups", help="build canonical study/material/protocol group keys"
    )
    split_groups_parser.add_argument("--fixture", action="store_true", help="use the sanitized group-key fixture")
    split_duplicates_parser = split_subparsers.add_parser(
        "detect-duplicates", help="detect formulation and semantic near-duplicates"
    )
    split_duplicates_parser.add_argument("--fixture", action="store_true", help="use the sanitized duplicate fixture")
    split_freeze_parser = split_subparsers.add_parser(
        "freeze-dev", help="freeze the development train and validation split"
    )
    split_freeze_parser.add_argument("--fixture", action="store_true", help="use the sanitized split-freeze fixture")
    split_audit_parser = split_subparsers.add_parser("audit", help="run adversarial split leakage and lockbox audit")
    split_audit_parser.add_argument("--fixture", action="store_true", help="use the sanitized split-audit fixture")
    split_audit_parser.add_argument("--strict", action="store_true", help="fail on any mandatory audit finding")

    for command in FUTURE_COMMANDS:
        subparsers.add_parser(command, help="reserved; not implemented")
    return parser


def main(argv: Sequence[str] | None = None, *, prog: str = "biointerfaceos") -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser(prog)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor(args.strict)
    if args.command == "state":
        from biointerfaceos.state import (
            StateValidationError,
            next_ready_task,
            validate_repository_state,
        )

        if args.state_command is None:
            parser.parse_args(["state", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("STATE_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            _, tasks = validate_repository_state(root)
        except StateValidationError as exc:
            print(f"STATE_INVALID: {exc}", file=sys.stderr)
            return 1
        if args.state_command == "validate":
            print(f"STATE_VALID tasks={len(tasks)}")
            return 0
        task = next_ready_task(tasks)
        if task is None:
            print("NO_READY_TASK")
            return 1
        print(task.id)
        return 0
    if args.command == "project":
        if args.project_command not in {
            "accept",
            "accept-r2",
            "audit-r2-remediation",
            "audit-r2-external-handoff",
            "audit-r2-external-gate-path",
        }:
            parser.parse_args(["project", "--help"])
            return 0
        if args.project_command == "accept-r2":
            from biointerfaceos.r2_acceptance_workflow import (
                R2AcceptanceError,
                R2AcceptanceWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("R2_ACCEPTANCE_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                r2_acceptance_summary = R2AcceptanceWorkflow(root).run(strict=args.strict)
            except (R2AcceptanceError, OSError) as exc:
                print(f"R2_ACCEPTANCE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R2_ACCEPTANCE_VALID "
                f"status={r2_acceptance_summary.status} "
                f"blockers={r2_acceptance_summary.prerequisite_blocker_count} "
                "external_reproduction_verified=false editorial_rereview_verified=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.project_command == "audit-r2-remediation":
            from biointerfaceos.r2_remediation_workflow import (
                R2RemediationError,
                R2RemediationWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("R2_REMEDIATION_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                remediation_summary = R2RemediationWorkflow(root).run(strict=args.strict)
            except (R2RemediationError, OSError) as exc:
                print(f"R2_REMEDIATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R2_REMEDIATION_VALID "
                f"status={remediation_summary.status} "
                f"findings={remediation_summary.finding_count} "
                f"open={remediation_summary.open_finding_count} "
                f"fallback={remediation_summary.protocol_fallback_count} "
                f"bounded_pass={remediation_summary.bounded_pass_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.project_command == "audit-r2-external-handoff":
            from biointerfaceos.r2_external_handoff_workflow import (
                R2ExternalHandoffError,
                R2ExternalHandoffWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("R2_EXTERNAL_HANDOFF_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                handoff_summary = R2ExternalHandoffWorkflow(root).run(strict=args.strict)
            except (R2ExternalHandoffError, OSError) as exc:
                print(f"R2_EXTERNAL_HANDOFF_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R2_EXTERNAL_HANDOFF_VALID "
                f"status={handoff_summary.status} "
                f"source_fields={handoff_summary.source_intake_field_count} "
                f"analysis_unit_fields={handoff_summary.analysis_unit_field_count} "
                "external_source_received=false independent_evaluator_receipt_verified=false "
                "external_reproduction_verified=false editorial_rereview_verified=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.project_command == "audit-r2-external-gate-path":
            from biointerfaceos.r2_external_gate_path_workflow import (
                R2ExternalGatePathError,
                R2ExternalGatePathWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("R2_EXTERNAL_GATE_PATH_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                gate_path_summary = R2ExternalGatePathWorkflow(root).run(strict=args.strict)
            except (R2ExternalGatePathError, OSError) as exc:
                print(f"R2_EXTERNAL_GATE_PATH_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R2_EXTERNAL_GATE_PATH_VALID "
                f"status={gate_path_summary.status} "
                f"stages={gate_path_summary.stage_count} "
                f"references={gate_path_summary.reference_count} "
                f"commands={gate_path_summary.command_count} "
                "external_source_received=false independent_evaluator_receipt_verified=false "
                "external_reproduction_verified=false editorial_rereview_verified=false "
                "scientific_submission_ready=false"
            )
            return 0
        from biointerfaceos.final_acceptance_workflow import (
            FinalAcceptanceError,
            FinalAcceptanceWorkflow,
        )

        root = find_repository_root()
        if root is None:
            print("PROJECT_ACCEPT_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            acceptance_result = FinalAcceptanceWorkflow(root).run(strict=args.strict)
        except (FinalAcceptanceError, OSError) as exc:
            print(f"PROJECT_ACCEPT_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"PROJECT_ACCEPT_VALID acceptance_id={acceptance_result['acceptance_id']} "
            f"release_id={acceptance_result['release_id']} "
            f"critical_findings={acceptance_result['critical_findings']} "
            "project_status=IN_PROGRESS public_release_verified=true"
        )
        return 0
    if args.command == "schema":
        if args.schema_command is None:
            parser.parse_args(["schema", "--help"])
            return 0
        from biointerfaceos.schema import SchemaError, validate_all

        root = find_repository_root()
        if root is None:
            print("SCHEMA_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            configs = validate_all(root)
        except SchemaError as exc:
            print(f"SCHEMA_INVALID: {exc}", file=sys.stderr)
            return 1
        print(f"SCHEMA_VALID schemas={len(configs)} fixtures={len(configs)}")
        return 0
    if args.command == "source":
        root = find_repository_root()
        if root is None:
            print("SOURCE_INVALID: repository root not found", file=sys.stderr)
            return 1
        if args.source_command == "manifest" and args.manifest_command == "validate":
            from biointerfaceos.manifest import ManifestError, ManifestRegistry

            try:
                summary = ManifestRegistry(root).validate()
            except (ManifestError, OSError) as exc:
                print(f"SOURCE_MANIFEST_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SOURCE_MANIFEST_VALID rows={summary.rows} "
                f"unique_content_hashes={summary.unique_content_hashes} "
                f"admitted={summary.admitted} rejected={summary.rejected} "
                f"quarantined={summary.quarantined}"
            )
            return 0
        if args.source_command == "audit-specialized":
            from biointerfaceos.nanodatabase_audit import NanodatabaseAuditError, load_audit

            try:
                audit_summary = load_audit(root / "tests/fixtures/nanodatabases/admission_decisions.json")
                report_path = root / "reports/NANODATABASE_ADMISSION.md"
                if not report_path.is_file():
                    raise NanodatabaseAuditError(f"missing report: {report_path}")
            except (NanodatabaseAuditError, OSError) as exc:
                print(f"NANODATABASE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"NANODATABASE_AUDIT_VALID candidates={audit_summary.candidates} "
                f"admitted_substitutes={audit_summary.admitted_substitutes} "
                f"metadata_only={audit_summary.metadata_only} "
                f"quarantined={audit_summary.quarantined} rejected={audit_summary.rejected}"
            )
            return 0
        if args.source_command == "policy" and args.policy_command == "self-test":
            from biointerfaceos.policy import PolicyError, RejectionRegistry, SourcePolicyEngine

            try:
                registry = RejectionRegistry(root)
                passed, rejected = SourcePolicyEngine.from_yaml(root).self_test(
                    root / "tests/fixtures/policy",
                    registry,
                )
            except (OSError, PolicyError) as exc:
                print(f"SOURCE_POLICY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SOURCE_POLICY_VALID fixtures={passed} "
                f"rejected_or_quarantined={rejected} registry_rows={registry.validate()}"
            )
            return 0
        parser.parse_args(["source", "--help"])
        return 0
    if args.command == "extract":
        if args.extract_command not in {"tables", "figures", "experiment"}:
            parser.parse_args(["extract", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("EXTRACT_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("EXTRACT_INVALID: --fixture is required", file=sys.stderr)
            return 2
        if args.extract_command == "experiment":
            if not args.dual:
                print("EXTRACT_INVALID: --dual is required", file=sys.stderr)
                return 2
            from biointerfaceos.experiment_extraction import (
                DualExperimentExtractor,
                DualExtractionError,
            )

            try:
                dual_summary = DualExperimentExtractor(root).run()
            except (OSError, DualExtractionError) as exc:
                print(f"DUAL_EXPERIMENT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"DUAL_EXPERIMENT_VALID records={dual_summary.records} "
                f"rule_fields={dual_summary.rule_fields} "
                f"mock_fields={dual_summary.mock_fields} "
                f"agreements={dual_summary.agreements} "
                f"disagreements={dual_summary.disagreements} "
                f"accepted_fields={dual_summary.accepted_fields} "
                f"review_items={dual_summary.review_items} fixture=true"
            )
            return 0
        if args.extract_command == "tables":
            from biointerfaceos.table_semantics import TableSemanticsError, TableSemanticsParser

            try:
                semantic_summary = TableSemanticsParser(root).run()
            except (OSError, TableSemanticsError) as exc:
                print(f"TABLE_SEMANTICS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"TABLE_SEMANTICS_VALID tables={semantic_summary.tables} "
                f"arms={semantic_summary.arms} "
                f"measurements={semantic_summary.measurements} "
                f"review_items={semantic_summary.review_items} fixture=true"
            )
            return 0

        from biointerfaceos.figure_detector import FigureDetectionError, FigureDetector

        try:
            figure_summary = FigureDetector(root).run()
        except (OSError, FigureDetectionError) as exc:
            print(f"FIGURE_DETECTION_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"FIGURE_DETECTION_VALID figures={figure_summary.figures} "
            f"panels={figure_summary.panels} "
            f"supported_panels={figure_summary.supported_panels} "
            f"unsupported_panels={figure_summary.unsupported_panels} "
            f"axes={figure_summary.axes} "
            f"legend_entries={figure_summary.legend_entries} "
            f"curve_candidates={figure_summary.curve_candidates} "
            f"uncertainty_cues={figure_summary.uncertainty_cues} "
            f"review_items={figure_summary.review_items} fixture=true"
        )
        if args.digitize:
            from biointerfaceos.figure_digitizer import (
                FigureDigitizationError,
                FigureDigitizer,
            )

            try:
                digitization_summary = FigureDigitizer(root).run()
            except (OSError, FigureDigitizationError) as exc:
                print(f"FIGURE_DIGITIZATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"FIGURE_DIGITIZATION_VALID figures={digitization_summary.figures} "
                f"panels={digitization_summary.panels} "
                f"series_seen={digitization_summary.series_seen} "
                f"digitized_series={digitization_summary.digitized_series} "
                f"excluded_series={digitization_summary.excluded_series} "
                f"points={digitization_summary.points} "
                f"uncertainty_records={digitization_summary.uncertainty_records} "
                f"review_items={digitization_summary.review_items} fixture=true"
            )
        return 0
    if args.command == "normalize":
        if args.normalize_command != "units":
            parser.parse_args(["normalize", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("NORMALIZE_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("NORMALIZE_INVALID: --fixture is required", file=sys.stderr)
            return 2
        from biointerfaceos.unit_normalizer import UnitNormalizationError, UnitNormalizer

        try:
            unit_summary = UnitNormalizer(root).run()
        except (OSError, UnitNormalizationError) as exc:
            print(f"UNIT_NORMALIZATION_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"UNIT_NORMALIZATION_VALID assertions={unit_summary.assertions} "
            f"normalized={unit_summary.normalized} "
            f"review_items={unit_summary.review_items} "
            f"uncertainty_records={unit_summary.uncertainty_records} fixture=true"
        )
        return 0
    if args.command == "evidence":
        if args.evidence_command != "trace":
            parser.parse_args(["evidence", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("EVIDENCE_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("EVIDENCE_INVALID: --fixture is required", file=sys.stderr)
            return 2
        from biointerfaceos.evidence_resolver import EvidenceResolutionError, EvidenceResolver

        resolver = EvidenceResolver(root)
        try:
            trace_summary = resolver.run()
            trace_matches = len(resolver.reverse_trace(args.locator)) if args.locator is not None else 0
        except (OSError, EvidenceResolutionError) as exc:
            print(f"EVIDENCE_TRACE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"EVIDENCE_TRACE_VALID assertions={trace_summary.assertions} "
            f"resolved={trace_summary.resolved} "
            f"quarantined={trace_summary.quarantined} "
            f"conflict_nodes={trace_summary.conflict_nodes} "
            f"conflict_edges={trace_summary.conflict_edges} "
            f"review_items={trace_summary.review_items} "
            f"trace_matches={trace_matches} fixture=true"
        )
        return 0
    if args.command == "qc":
        if args.qc_command != "records":
            parser.parse_args(["qc", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("QC_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("QC_INVALID: --fixture is required", file=sys.stderr)
            return 2
        from biointerfaceos.plausibility_qc import PlausibilityChecker, PlausibilityQCError

        try:
            qc_summary = PlausibilityChecker(root).run(strict=args.strict)
        except (OSError, PlausibilityQCError) as exc:
            print(f"QC_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"QC_VALID records={qc_summary.records} "
            f"flags={qc_summary.flags} "
            f"critical_flags={qc_summary.critical_flags} "
            f"warning_flags={qc_summary.warning_flags} "
            f"quarantined_records={qc_summary.quarantined_records} "
            f"false_positive_controls={qc_summary.false_positive_controls} "
            f"injected_error_recall={qc_summary.injected_error_recall:.3f} "
            f"review_items={qc_summary.review_items} fixture=true"
        )
        return 0
    if args.command == "review":
        if args.review_command != "export":
            parser.parse_args(["review", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("REVIEW_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.review_packets import ReviewPacketBuilder, ReviewPacketError

        try:
            review_summary = ReviewPacketBuilder(root).export(sample=args.sample)
        except (ReviewPacketError, OSError) as exc:
            print(f"REVIEW_EXPORT_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"REVIEW_EXPORT_VALID packets={review_summary.packets} "
            f"strata={review_summary.strata} "
            f"unsigned_packets={review_summary.unsigned_packets} "
            f"signed_packets={review_summary.signed_packets} "
            f"sample={args.sample}"
        )
        return 0
    if args.command == "paper-a":
        root = find_repository_root()
        if root is None:
            print("PAPER_A_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.paper_a_workflow import PaperAError, PaperAWorkflow

        try:
            paper_a_summary = PaperAWorkflow(root).run(fixture=True)
        except (PaperAError, OSError) as exc:
            print(f"PAPER_A_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"PAPER_A_VALID release_id={paper_a_summary.release_id} "
            f"instances={paper_a_summary.instances} families={paper_a_summary.families} "
            f"train={paper_a_summary.train} validation={paper_a_summary.validation} "
            f"claims={paper_a_summary.claims} tables={paper_a_summary.tables} "
            f"figures={paper_a_summary.figures} evidence_inputs={paper_a_summary.evidence_inputs} "
            f"style_passed={str(paper_a_summary.style_passed).lower()} "
            f"resumed={paper_a_summary.resumed} target_values_exposed=false"
        )
        return 0
    if args.command == "paper-b":
        root = find_repository_root()
        if root is None:
            print("PAPER_B_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.paper_b_workflow import PaperBError, PaperBWorkflow

        try:
            paper_b_summary = PaperBWorkflow(root).run(fixture=True)
        except (PaperBError, OSError) as exc:
            print(f"PAPER_B_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"PAPER_B_VALID release_id={paper_b_summary.release_id} "
            f"data_layers={paper_b_summary.data_layers} "
            f"model_layers={paper_b_summary.model_layers} "
            f"ablations={paper_b_summary.ablations} ood_rows={paper_b_summary.ood_rows} "
            f"claims={paper_b_summary.claims} tables={paper_b_summary.tables} "
            f"figures={paper_b_summary.figures} evidence_inputs={paper_b_summary.evidence_inputs} "
            f"style_passed={str(paper_b_summary.style_passed).lower()} "
            f"resumed={paper_b_summary.resumed} target_values_exposed=false"
        )
        return 0
    if args.command == "paper-c-prelock":
        root = find_repository_root()
        if root is None:
            print("PAPER_C_PRELOCK_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.paper_c_prelock_workflow import (
            PaperCPrelockError,
            PaperCPrelockWorkflow,
        )

        try:
            paper_c_summary = PaperCPrelockWorkflow(root).run(fixture=True)
        except (PaperCPrelockError, OSError) as exc:
            print(f"PAPER_C_PRELOCK_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"PAPER_C_PRELOCK_VALID candidates={paper_c_summary.candidate_count} "
            f"strong_candidates={paper_c_summary.strong_candidates} "
            f"analyses={paper_c_summary.analyses} predictions={paper_c_summary.predictions} "
            f"claims={paper_c_summary.claims} tables={paper_c_summary.tables} "
            f"figures={paper_c_summary.figures} evidence_inputs={paper_c_summary.evidence_inputs} "
            f"style_passed={str(paper_c_summary.style_passed).lower()} "
            f"lockbox_accessed={str(paper_c_summary.lockbox_accessed).lower()} "
            f"resumed={paper_c_summary.resumed} target_values_exposed=false"
        )
        return 0
    if args.command == "claim":
        if args.claim_command == "audit-semantics":
            from biointerfaceos.evidence_semantics_audit import (
                EvidenceSemanticsAuditError,
                EvidenceSemanticsAuditWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("EVIDENCE_SEMANTICS_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                result = EvidenceSemanticsAuditWorkflow(root).run(strict=args.strict)
            except (EvidenceSemanticsAuditError, OSError) as exc:
                print(f"EVIDENCE_SEMANTICS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"EVIDENCE_SEMANTICS_{result['status']} "
                f"audit_id={result['audit_id']} blockers={result['blocking_findings']} "
                "historical_sources_mutated=false submission_ready=false"
            )
            return 0 if result["status"] == "PASS_EVIDENCE_SEMANTICS" else 1
        if args.claim_command == "audit-manuscripts":
            from biointerfaceos.claim_audit_workflow import ClaimAuditError, ClaimAuditWorkflow

            root = find_repository_root()
            if root is None:
                print("FINAL_CLAIM_AUDIT_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                claim_audit_result = ClaimAuditWorkflow(root).run(strict=args.strict)
            except (ClaimAuditError, OSError) as exc:
                print(f"FINAL_CLAIM_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"FINAL_CLAIM_AUDIT_VALID audit_id={claim_audit_result['audit_id']} "
                f"papers={len(claim_audit_result['papers'])} "
                f"claims={claim_audit_result['claim_count']} "
                f"sentences={claim_audit_result['sentence_count']} "
                f"evidence={claim_audit_result['evidence_reference_count']} "
                "critical_findings=0 submission_blockers=0"
            )
            return 0
        if args.claim_command != "preregister":
            parser.parse_args(["claim", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("CLAIM_PREREGISTER_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.dev:
            print("CLAIM_PREREGISTER_INVALID: --dev is required", file=sys.stderr)
            return 2
        from biointerfaceos.hypothesis_tournament_workflow import (
            HypothesisTournamentWorkflow,
            TournamentError,
        )

        try:
            tournament_summary = HypothesisTournamentWorkflow(root).run(development=True)
        except (TournamentError, OSError) as exc:
            print(f"CLAIM_PREREGISTER_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"CLAIM_PREREGISTER_VALID candidates={tournament_summary.candidates} "
            f"ranked={tournament_summary.ranked} "
            f"duplicates_removed={tournament_summary.duplicates_removed} "
            f"exclusions={tournament_summary.exclusions} "
            f"config_frozen={str(tournament_summary.config_frozen).lower()} "
            f"lockbox_clean={str(tournament_summary.lockbox_clean).lower()} "
            f"claims_auto_accepted={str(tournament_summary.claims_auto_accepted).lower()} "
            f"selected_pipeline={tournament_summary.selected_pipeline} "
            f"resumed={tournament_summary.resumed}"
        )
        return 0
    if args.command == "design":
        if args.design_command == "audit-candidates":
            root = find_repository_root()
            if root is None:
                print("DESIGN_AUDIT_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("DESIGN_AUDIT_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.candidate_audit_workflow import (
                CandidateAuditError,
                CandidateAuditWorkflow,
            )

            try:
                candidate_audit_summary = CandidateAuditWorkflow(root).run(fixture=True)
            except (CandidateAuditError, OSError) as exc:
                print(f"DESIGN_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"DESIGN_AUDIT_VALID candidates={candidate_audit_summary.candidates} "
                f"unique_candidates={candidate_audit_summary.unique_candidates} "
                f"duplicate_candidates={candidate_audit_summary.duplicate_candidates} "
                f"supported_candidates={candidate_audit_summary.supported_candidates} "
                f"rejected_candidates={candidate_audit_summary.rejected_candidates} "
                f"temporal_matches={candidate_audit_summary.temporal_matches} "
                f"unresolved_matches={candidate_audit_summary.unresolved_matches} "
                f"abstentions={candidate_audit_summary.abstentions} "
                f"selected_wording={candidate_audit_summary.selected_wording} "
                f"resumed={candidate_audit_summary.resumed}"
            )
            return 0
        if args.design_command == "generative":
            root = find_repository_root()
            if root is None:
                print("DESIGN_GENERATIVE_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("DESIGN_GENERATIVE_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.target_corona_generative_workflow import (
                TargetCoronaGenerativeError,
                TargetCoronaGenerativeWorkflow,
            )

            try:
                generative_summary = TargetCoronaGenerativeWorkflow(root).run(fixture=True)
            except (TargetCoronaGenerativeError, OSError) as exc:
                print(f"DESIGN_GENERATIVE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"DESIGN_GENERATIVE_VALID rows={generative_summary.rows} "
                f"groups={generative_summary.groups} "
                f"heldout={generative_summary.heldout} "
                f"sufficiency_passed={int(generative_summary.sufficiency_passed)} "
                f"generator_attempted={int(generative_summary.generator_attempted)} "
                f"baseline_validity={generative_summary.baseline_validity:.6f} "
                f"generator_validity={generative_summary.generator_validity:.6f} "
                f"novelty_gain={generative_summary.novelty_gain:.6f} "
                f"pareto_gain={generative_summary.pareto_gain} "
                f"ood_uncertainty_delta={generative_summary.ood_uncertainty_delta:.6f} "
                f"ablations={generative_summary.ablations} "
                f"selected_method={generative_summary.selected_method} "
                f"fallback={generative_summary.fallback} "
                f"abstentions={generative_summary.abstentions} "
                f"resumed={generative_summary.resumed}"
            )
            return 0
        if args.design_command != "baseline":
            parser.parse_args(["design", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("DESIGN_BASELINE_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("DESIGN_BASELINE_INVALID: --fixture is required", file=sys.stderr)
            return 2
        from biointerfaceos.design_baseline_workflow import (
            DesignBaselineError,
            DesignBaselineWorkflow,
        )

        try:
            design_summary = DesignBaselineWorkflow(root).run(fixture=True)
        except (DesignBaselineError, OSError) as exc:
            print(f"DESIGN_BASELINE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"DESIGN_BASELINE_VALID candidates={design_summary.candidates} "
            f"valid_candidates={design_summary.valid_candidates} "
            f"invalid_candidates={design_summary.invalid_candidates} "
            f"supported_candidates={design_summary.supported_candidates} "
            f"methods={design_summary.methods} "
            f"constraint_pass_rate={design_summary.constraint_pass_rate:.6f} "
            f"controls_recovered={design_summary.controls_recovered} "
            f"controls_total={design_summary.controls_total} "
            f"pareto_members={design_summary.pareto_members} "
            f"abstentions={design_summary.abstentions} "
            f"selected_method={design_summary.selected_method} "
            f"resumed={design_summary.resumed}"
        )
        return 0
    if args.command == "robustness":
        if args.robustness_command == "negative-controls":
            root = find_repository_root()
            if root is None:
                print("NEGATIVE_CONTROLS_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.strict:
                print("NEGATIVE_CONTROLS_INVALID: --strict is required", file=sys.stderr)
                return 2
            from biointerfaceos.negative_controls_workflow import (
                NegativeControlsError,
                NegativeControlsWorkflow,
            )

            try:
                negative_controls_summary = NegativeControlsWorkflow(root).run(strict=True)
            except (NegativeControlsError, OSError) as exc:
                print(f"NEGATIVE_CONTROLS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"NEGATIVE_CONTROLS_VALID attacks={negative_controls_summary.attacks} "
                f"expected_failures={negative_controls_summary.expected_failures} "
                f"detected={negative_controls_summary.detected} "
                f"critical_leaks={negative_controls_summary.critical_leaks} "
                f"duplicate_hits={negative_controls_summary.duplicate_hits} "
                f"strict_pass={int(negative_controls_summary.strict_pass)} "
                f"claim_status={negative_controls_summary.claim_status} "
                f"resumed={negative_controls_summary.resumed}"
            )
            return 0
        if args.robustness_command == "bias":
            root = find_repository_root()
            if root is None:
                print("BIAS_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("BIAS_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.bias_workflow import BiasWorkflow, BiasWorkflowError

            try:
                robustness_bias_summary = BiasWorkflow(root).run(fixture=True)
            except (BiasWorkflowError, OSError) as exc:
                print(f"BIAS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BIAS_VALID rows={robustness_bias_summary.rows} "
                f"clusters={robustness_bias_summary.clusters} "
                f"models={robustness_bias_summary.models} "
                f"observed_rows={robustness_bias_summary.observed_rows} "
                f"missing_rows={robustness_bias_summary.missing_rows} "
                f"missing_mechanisms={robustness_bias_summary.missing_mechanisms} "
                f"interval_records={robustness_bias_summary.interval_records} "
                f"model_disagreement={robustness_bias_summary.model_disagreement:.6f} "
                f"p_values_used={int(robustness_bias_summary.p_values_used)} "
                f"claim_status={robustness_bias_summary.claim_status} "
                f"resumed={robustness_bias_summary.resumed}"
            )
            return 0
        if args.robustness_command == "ood":
            root = find_repository_root()
            if root is None:
                print("OOD_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.all:
                print("OOD_INVALID: --all is required", file=sys.stderr)
                return 2
            from biointerfaceos.ood_workflow import OODWorkflow, OODWorkflowError

            try:
                robustness_ood_summary = OODWorkflow(root).run(all_groups=True)
            except (OODWorkflowError, OSError) as exc:
                print(f"OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"OOD_VALID dimensions={robustness_ood_summary.dimensions} "
                f"groups={robustness_ood_summary.groups} "
                f"low_n_groups={robustness_ood_summary.low_n_groups} "
                f"leave_largest={robustness_ood_summary.leave_largest} "
                f"sensitivity_records={robustness_ood_summary.sensitivity_records} "
                f"primary_records={robustness_ood_summary.primary_records} "
                f"calibration_records={robustness_ood_summary.calibration_records} "
                f"selective_risk_records={robustness_ood_summary.selective_risk_records} "
                f"claim_status={robustness_ood_summary.claim_status} "
                f"resumed={robustness_ood_summary.resumed}"
            )
            return 0
        if args.robustness_command != "ablations":
            parser.parse_args(["robustness", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("ABLATIONS_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.all:
            print("ABLATIONS_INVALID: --all is required", file=sys.stderr)
            return 2
        from biointerfaceos.ablation_workflow import AblationError, AblationWorkflow

        try:
            robustness_ablation_summary = AblationWorkflow(root).run(all_ablations=True)
        except (AblationError, OSError) as exc:
            print(f"ABLATIONS_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"ABLATIONS_VALID comparisons={robustness_ablation_summary.comparisons} "
            f"rows={robustness_ablation_summary.rows} "
            f"same_splits={int(robustness_ablation_summary.same_splits)} "
            f"same_budget={int(robustness_ablation_summary.same_budget)} "
            f"mean_effect={robustness_ablation_summary.mean_effect:.6f} "
            f"interval_records={robustness_ablation_summary.interval_records} "
            f"calibration_records={robustness_ablation_summary.calibration_records} "
            f"ood_records={robustness_ablation_summary.ood_records} "
            f"missing_ablations={robustness_ablation_summary.missing_ablations} "
            f"claim_blocks={robustness_ablation_summary.claim_blocks} "
            f"resumed={robustness_ablation_summary.resumed}"
        )
        return 0
    if args.command == "discover":
        if args.discover_command == "counterfactuals":
            root = find_repository_root()
            if root is None:
                print("COUNTERFACTUALS_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("COUNTERFACTUALS_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.counterfactual_workflow import (
                CounterfactualError,
                CounterfactualWorkflow,
            )

            try:
                counterfactual_summary = CounterfactualWorkflow(root).run(fixture=True)
            except (CounterfactualError, OSError) as exc:
                print(f"COUNTERFACTUALS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"COUNTERFACTUALS_VALID rows={counterfactual_summary.rows} "
                f"interventions={counterfactual_summary.interventions} "
                f"supported={counterfactual_summary.supported} "
                f"rejected={counterfactual_summary.rejected} "
                f"model_families={counterfactual_summary.model_families} "
                f"scored={counterfactual_summary.scored} "
                f"abstentions={counterfactual_summary.abstentions} "
                f"rank_pairs={counterfactual_summary.rank_pairs} "
                f"rank_stability={counterfactual_summary.rank_stability:.6f} "
                f"contradictions={counterfactual_summary.contradictions} "
                f"unresolved={counterfactual_summary.unresolved} "
                f"resumed={counterfactual_summary.resumed}"
            )
            return 0
        if args.discover_command == "protocol-effects":
            root = find_repository_root()
            if root is None:
                print("PROTOCOL_EFFECTS_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("PROTOCOL_EFFECTS_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.protocol_effects_workflow import (
                ProtocolEffectsError,
                ProtocolEffectsWorkflow,
            )

            try:
                protocol_effects_summary = ProtocolEffectsWorkflow(root).run(fixture=True)
            except (ProtocolEffectsError, OSError) as exc:
                print(f"PROTOCOL_EFFECTS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PROTOCOL_EFFECTS_VALID rows={protocol_effects_summary.rows} "
                f"variables={protocol_effects_summary.variables} "
                f"studies={protocol_effects_summary.studies} "
                f"raw_effect={protocol_effects_summary.raw_effect:.6f} "
                f"adjusted_effect={protocol_effects_summary.adjusted_effect:.6f} "
                f"reversal_tests={protocol_effects_summary.reversal_tests} "
                f"reversals_detected={protocol_effects_summary.reversals_detected} "
                f"counterexamples={protocol_effects_summary.counterexamples} "
                f"heterogeneity_max={protocol_effects_summary.heterogeneity_max:.6f} "
                "universal_reversal_permitted="
                f"{str(protocol_effects_summary.universal_reversal_permitted).lower()} "
                f"language_status={protocol_effects_summary.language_status} "
                f"resumed={protocol_effects_summary.resumed}"
            )
            return 0
        if args.discover_command == "symbolic-laws":
            root = find_repository_root()
            if root is None:
                print("SYMBOLIC_LAWS_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("SYMBOLIC_LAWS_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.symbolic_laws_workflow import (
                SymbolicLawsError,
                SymbolicLawsWorkflow,
            )

            try:
                symbolic_summary = SymbolicLawsWorkflow(root).run(fixture=True)
            except (SymbolicLawsError, OSError) as exc:
                print(f"SYMBOLIC_LAWS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SYMBOLIC_LAWS_VALID candidates={symbolic_summary.candidates} "
                f"unit_valid={symbolic_summary.unit_valid} "
                f"rejected={symbolic_summary.rejected} "
                f"nested_folds={symbolic_summary.nested_folds} "
                f"controls={symbolic_summary.controls} "
                f"bootstrap_stability={symbolic_summary.bootstrap_stability:.6f} "
                f"ood_passed={str(symbolic_summary.ood_passed).lower()} "
                f"selected_expression={symbolic_summary.selected_expression} "
                f"fallback={str(symbolic_summary.fallback).lower()} "
                f"resumed={symbolic_summary.resumed}"
            )
            return 0
        if args.discover_command == "cross-species":
            root = find_repository_root()
            if root is None:
                print("CROSS_SPECIES_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("CROSS_SPECIES_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.cross_species_workflow import (
                CrossSpeciesError,
                CrossSpeciesWorkflow,
            )

            try:
                transfer_summary = CrossSpeciesWorkflow(root).run(fixture=True)
            except (CrossSpeciesError, OSError) as exc:
                print(f"CROSS_SPECIES_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"CROSS_SPECIES_VALID rows={transfer_summary.rows} "
                f"strata={transfer_summary.strata} methods={transfer_summary.methods} "
                f"development_materials={transfer_summary.development_materials} "
                f"heldout_materials={transfer_summary.heldout_materials} "
                f"scored_heldout={transfer_summary.scored_heldout} "
                f"abstentions={transfer_summary.abstentions} "
                f"overlap_passed={str(transfer_summary.overlap_passed).lower()} "
                f"pairing_passed={str(transfer_summary.pairing_passed).lower()} "
                f"selected_method={transfer_summary.selected_method} "
                f"resumed={transfer_summary.resumed}"
            )
            return 0
        if args.discover_command == "mediation":
            root = find_repository_root()
            if root is None:
                print("MEDIATION_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("MEDIATION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.mediation_workflow import MediationError, MediationWorkflow

            try:
                mediation_summary = MediationWorkflow(root).run(fixture=True)
            except (MediationError, OSError) as exc:
                print(f"MEDIATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"MEDIATION_VALID rows={mediation_summary.rows} "
                f"development={mediation_summary.development_rows} "
                f"replication={mediation_summary.replication_rows} "
                f"study_clusters={mediation_summary.study_clusters} "
                f"estimands={mediation_summary.estimands} "
                f"alternative_mediators={mediation_summary.alternative_mediators} "
                f"dag_scenarios={mediation_summary.dag_scenarios} "
                f"cluster_bootstrap_records={mediation_summary.cluster_bootstrap_records} "
                f"replication_attempted={str(mediation_summary.replication_attempted).lower()} "
                f"replication_passed={str(mediation_summary.replication_passed).lower()} "
                f"causal_claim_permitted={str(mediation_summary.causal_claim_permitted).lower()} "
                f"language_status={mediation_summary.language_status} "
                f"resumed={mediation_summary.resumed}"
            )
            return 0
        if args.discover_command != "functional-axes":
            parser.parse_args(["discover", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("FUNCTIONAL_AXES_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("FUNCTIONAL_AXES_INVALID: --fixture is required", file=sys.stderr)
            return 2
        from biointerfaceos.functional_axes_workflow import (
            FunctionalAxesError,
            FunctionalAxesWorkflow,
        )

        try:
            axes_summary = FunctionalAxesWorkflow(root).run(fixture=True)
        except (FunctionalAxesError, OSError) as exc:
            print(f"FUNCTIONAL_AXES_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"FUNCTIONAL_AXES_VALID samples={axes_summary.samples} "
            f"modules={axes_summary.modules} alternatives={axes_summary.alternatives} "
            f"candidate_axes={axes_summary.candidate_axes} "
            f"bootstrap_stability={axes_summary.bootstrap_stability:.6f} "
            f"leave_study_stability={axes_summary.leave_study_stability:.6f} "
            f"random_control_stability={axes_summary.random_control_stability:.6f} "
            f"uncertainty_records={axes_summary.uncertainty_records} "
            f"selected_model={axes_summary.selected_model} "
            f"lockbox_clean={str(axes_summary.lockbox_clean).lower()} "
            f"resumed={axes_summary.resumed}"
        )
        return 0
    if args.command == "train":
        if args.train_command not in {
            "m1",
            "m2",
            "m3",
            "m4",
            "m5",
            "m6",
            "m7",
            "uncertainty",
            "multimodal",
        }:
            parser.parse_args(["train", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("M1_INVALID: repository root not found", file=sys.stderr)
            return 1
        config_path = (root / args.config).resolve()
        try:
            config_path.relative_to(root)
        except ValueError:
            print("M1_INVALID: config path escaped repository", file=sys.stderr)
            return 1
        if args.train_command == "m2":
            from biointerfaceos.m2_workflow import M2Error, M2Workflow

            try:
                m2_summary = M2Workflow(root, config_path=config_path).run(fixture=True)
            except (M2Error, OSError) as exc:
                print(f"M2_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"M2_VALID instances={m2_summary.instances} train={m2_summary.train} "
                f"validation={m2_summary.validation} model_kind={m2_summary.model_kind} "
                f"validation_rmse={m2_summary.validation_rmse:.6f} "
                f"resumed={m2_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "m3":
            from biointerfaceos.m3_workflow import M3Error, M3Workflow

            try:
                m3_summary = M3Workflow(root, config_path=config_path).run(fixture=True)
            except (M3Error, OSError) as exc:
                print(f"M3_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"M3_VALID pairs={m3_summary.pairs} train={m3_summary.train} "
                f"validation={m3_summary.validation} "
                f"identification_status={m3_summary.identification_status} "
                f"direct_rmse={m3_summary.direct_rmse:.6f} "
                f"mediated_rmse={m3_summary.mediated_rmse:.6f} "
                f"resumed={m3_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "m4":
            from biointerfaceos.m4_workflow import M4Error, M4Workflow

            try:
                m4_summary = M4Workflow(root, config_path=config_path).run(fixture=True)
            except (M4Error, OSError) as exc:
                print(f"M4_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"M4_VALID rows={m4_summary.rows} train={m4_summary.train} "
                f"validation={m4_summary.validation} alternatives={m4_summary.alternatives} "
                f"best_rmse={m4_summary.best_rmse:.6f} "
                f"toy_recovery={str(m4_summary.toy_recovery).lower()} "
                f"resumed={m4_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "m5":
            from biointerfaceos.m5_workflow import M5Error, M5Workflow

            try:
                m5_summary = M5Workflow(root, config_path=config_path).run(fixture=True)
            except (M5Error, OSError) as exc:
                print(f"M5_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"M5_VALID trajectories={m5_summary.trajectories} "
                f"train_trajectories={m5_summary.train_trajectories} "
                f"validation_trajectories={m5_summary.validation_trajectories} "
                f"model_kind={m5_summary.model_kind} "
                f"sufficiency_passed={str(m5_summary.sufficiency_passed).lower()} "
                f"validation_rmse={m5_summary.validation_rmse:.6f} "
                f"resumed={m5_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "m6":
            from biointerfaceos.m6_workflow import M6Error, M6Workflow

            try:
                m6_summary = M6Workflow(root, config_path=config_path).run(fixture=True)
            except (M6Error, OSError) as exc:
                print(f"M6_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"M6_VALID rows={m6_summary.rows} train={m6_summary.train} "
                f"validation={m6_summary.validation} "
                f"overlap_passed={str(m6_summary.overlap_passed).lower()} "
                f"causal_claim_permitted={str(m6_summary.causal_claim_permitted).lower()} "
                f"validation_rmse={m6_summary.validation_rmse:.6f} "
                f"resumed={m6_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "m7":
            from biointerfaceos.m7_workflow import M7Error, M7Workflow

            try:
                m7_summary = M7Workflow(root, config_path=config_path).run(fixture=True)
            except (M7Error, OSError) as exc:
                print(f"M7_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"M7_VALID rows={m7_summary.rows} train={m7_summary.train} "
                f"validation={m7_summary.validation} "
                f"domain_definitions={m7_summary.domain_definitions} "
                f"selected_model={m7_summary.selected_model} "
                f"hierarchical_erm_rmse={m7_summary.hierarchical_erm_rmse:.6f} "
                f"ood_rmse={m7_summary.ood_rmse:.6f} "
                f"leakage_passed={str(m7_summary.leakage_passed).lower()} "
                f"resumed={m7_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "uncertainty":
            from biointerfaceos.uncertainty_workflow import (
                UncertaintyError,
                UncertaintyWorkflow,
            )

            try:
                uncertainty_summary = UncertaintyWorkflow(root, config_path=config_path).run(fixture=True)
            except (UncertaintyError, OSError) as exc:
                print(f"UNCERTAINTY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"UNCERTAINTY_VALID rows={uncertainty_summary.rows} "
                f"calibration={uncertainty_summary.calibration} "
                f"validation={uncertainty_summary.validation} "
                f"selected_model={uncertainty_summary.selected_model} "
                f"calibration_passed={str(uncertainty_summary.calibration_passed).lower()} "
                f"coverage={uncertainty_summary.coverage:.6f} "
                "selective_risk_decreases="
                f"{str(uncertainty_summary.selective_risk_decreases).lower()} "
                f"ood_abstentions={uncertainty_summary.ood_abstentions} "
                f"resumed={uncertainty_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.train_command == "multimodal":
            from biointerfaceos.multimodal_workflow import MultimodalError, MultimodalWorkflow

            try:
                multimodal_summary = MultimodalWorkflow(root, config_path=config_path).run(fixture=True)
            except (MultimodalError, OSError) as exc:
                print(f"MULTIMODAL_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"MULTIMODAL_VALID rows={multimodal_summary.rows} "
                f"train={multimodal_summary.train} "
                f"validation={multimodal_summary.validation} "
                f"modalities={multimodal_summary.modalities} "
                f"selected_model={multimodal_summary.selected_model} "
                f"fusion_ood_gain={multimodal_summary.fusion_ood_gain:.6f} "
                f"selected_ood_rmse={multimodal_summary.selected_ood_rmse:.6f} "
                f"leakage_passed={str(multimodal_summary.leakage_passed).lower()} "
                f"missingness_masked={str(multimodal_summary.missingness_masked).lower()} "
                f"resumed={multimodal_summary.resumed} target_values_exposed=false"
            )
            return 0
        from biointerfaceos.m1_workflow import M1Error, M1Workflow

        try:
            m1_summary = M1Workflow(root, config_path=config_path).run(fixture=True)
        except (M1Error, OSError) as exc:
            print(f"M1_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"M1_VALID instances={m1_summary.instances} train={m1_summary.train} "
            f"validation={m1_summary.validation} converged={str(m1_summary.converged).lower()} "
            f"toy_recovery={str(m1_summary.toy_recovery).lower()} "
            f"validation_rmse={m1_summary.validation_rmse:.6f} "
            f"resumed={m1_summary.resumed} target_values_exposed=false"
        )
        return 0
    if args.command == "benchmark":
        if args.benchmark_command == "evaluate-real":
            from biointerfaceos.real_benchmark_workflow import (
                RealBenchmarkError,
                RealBenchmarkWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("REAL_BENCHMARK_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                real_benchmark_summary = RealBenchmarkWorkflow(root).run(strict=args.strict)
            except (RealBenchmarkError, OSError) as exc:
                print(f"REAL_BENCHMARK_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"REAL_BENCHMARK_VALID benchmark_id={real_benchmark_summary.benchmark_id} "
                f"studies={real_benchmark_summary.study_count} "
                f"laboratories={real_benchmark_summary.laboratory_count} "
                f"items={real_benchmark_summary.item_count} "
                f"predictions={real_benchmark_summary.prediction_count} "
                "held_out_groups=true raw_predictions_published=true "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.benchmark_command == "run-baselines":
            root = find_repository_root()
            if root is None:
                print("BENCHMARK_BASELINE_INVALID: repository root not found", file=sys.stderr)
                return 1
            if args.group != "simple":
                if args.group != "representation":
                    print(
                        "BENCHMARK_BASELINE_INVALID: --group simple or representation is required",
                        file=sys.stderr,
                    )
                    return 2
                from biointerfaceos.benchmark_representations import (
                    BenchmarkRepresentationError,
                    BenchmarkRepresentationWorkflow,
                )

                try:
                    representation_summary = BenchmarkRepresentationWorkflow(root).run(group=args.group)
                except (BenchmarkRepresentationError, OSError) as exc:
                    print(f"BENCHMARK_REPRESENTATION_INVALID: {exc}", file=sys.stderr)
                    return 1
                print(
                    f"REPRESENTATIONS_VALID group={args.group} "
                    f"baselines={representation_summary.baselines} "
                    f"successful={representation_summary.successful} "
                    f"validation_instances={representation_summary.validation_instances} "
                    f"best_rmse={representation_summary.best_rmse:.6f} "
                    f"resumed={representation_summary.resumed} target_values_exposed=false"
                )
                return 0
            from biointerfaceos.benchmark_baselines import (
                BenchmarkBaselineError,
                BenchmarkBaselineWorkflow,
            )

            try:
                baseline_summary = BenchmarkBaselineWorkflow(root).run(group=args.group)
            except (BenchmarkBaselineError, OSError) as exc:
                print(f"BENCHMARK_BASELINE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BASELINES_VALID group={args.group} "
                f"baselines={baseline_summary.baselines} "
                f"successful={baseline_summary.successful} "
                f"validation_instances={baseline_summary.validation_instances} "
                f"best_rmse={baseline_summary.best_rmse:.6f} "
                f"resumed={baseline_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.benchmark_command == "grade":
            root = find_repository_root()
            if root is None:
                print("BENCHMARK_GRADE_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("BENCHMARK_GRADE_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.benchmark_grading import (
                BenchmarkGradeError,
                BenchmarkGradingWorkflow,
            )

            try:
                grade_summary = BenchmarkGradingWorkflow(root).run(fixture=True)
            except (BenchmarkGradeError, OSError) as exc:
                print(f"BENCHMARK_GRADE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BENCHMARK_GRADE_VALID cases={grade_summary.cases} "
                f"instances={grade_summary.instances} "
                f"perfect_accuracy={grade_summary.perfect_accuracy:.6f} "
                f"wrong_accuracy={grade_summary.wrong_accuracy:.6f} "
                f"abstain_coverage={grade_summary.abstain_coverage:.6f} "
                f"resumed={grade_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.benchmark_command == "build":
            root = find_repository_root()
            if root is None:
                print("BENCHMARK_BUILD_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.dev:
                print("BENCHMARK_BUILD_INVALID: --dev is required", file=sys.stderr)
                return 2
            if not args.fixture:
                print("BENCHMARK_BUILD_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.benchmark_instances import (
                BenchmarkBuildError,
                BenchmarkInstanceWorkflow,
            )

            try:
                build_summary = BenchmarkInstanceWorkflow(root).run(dev=True, fixture=True)
            except (BenchmarkBuildError, OSError) as exc:
                print(f"BENCHMARK_BUILD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BENCHMARK_BUILD_VALID instances={build_summary.instances} "
                f"families={build_summary.families} "
                f"primary_families={build_summary.primary_families} "
                f"pilot_families={build_summary.pilot_families} "
                f"train={build_summary.train} validation={build_summary.validation} "
                f"missingness_mean={build_summary.missingness_mean:.6f} "
                f"resumed={build_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.benchmark_command == "agents":
            root = find_repository_root()
            if root is None:
                print("AGENT_BENCHMARK_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.dev:
                print("AGENT_BENCHMARK_INVALID: --dev is required", file=sys.stderr)
                return 2
            from biointerfaceos.agent_benchmark_workflow import (
                AgentBenchmarkError,
                AgentBenchmarkWorkflow,
            )

            try:
                agent_benchmark_summary = AgentBenchmarkWorkflow(root).run(development=True)
            except (AgentBenchmarkError, OSError) as exc:
                print(f"AGENT_BENCHMARK_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_BENCHMARK_VALID tasks={agent_benchmark_summary.tasks} "
                f"modes={agent_benchmark_summary.modes} "
                f"completion={agent_benchmark_summary.completion:.6f} "
                f"correctness={agent_benchmark_summary.correctness:.6f} "
                f"evidence={agent_benchmark_summary.evidence:.6f} "
                f"schema={agent_benchmark_summary.schema:.6f} "
                f"safety={agent_benchmark_summary.safety:.6f} "
                f"reproducibility={agent_benchmark_summary.reproducibility:.6f} "
                f"failures={agent_benchmark_summary.failures} "
                f"selected_mode={agent_benchmark_summary.selected_mode} "
                f"resumed={agent_benchmark_summary.resumed}"
            )
            return 0
        if args.benchmark_command == "freeze-dev":
            root = find_repository_root()
            if root is None:
                print("BENCHMARK_FREEZE_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("BENCHMARK_FREEZE_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.benchmark_freeze import (
                BenchmarkFreezeError,
                BenchmarkFreezeWorkflow,
            )

            try:
                benchmark_freeze_summary = BenchmarkFreezeWorkflow(root).run(fixture=True)
            except (BenchmarkFreezeError, OSError) as exc:
                print(f"BENCHMARK_FREEZE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BENCHMARK_FREEZE_VALID release_id={benchmark_freeze_summary.release_id} "
                f"version={benchmark_freeze_summary.semantic_version} "
                f"instances={benchmark_freeze_summary.instances} "
                f"train={benchmark_freeze_summary.train} "
                f"validation={benchmark_freeze_summary.validation} "
                f"graders={benchmark_freeze_summary.graders} "
                f"baselines={benchmark_freeze_summary.baselines} "
                f"representations={benchmark_freeze_summary.representations} "
                "public_hidden_separated="
                f"{str(benchmark_freeze_summary.public_hidden_separated).lower()} "
                "negative_controls_clean="
                f"{str(benchmark_freeze_summary.negative_controls_clean).lower()} "
                f"resumed={benchmark_freeze_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.benchmark_command != "extraction":
            parser.parse_args(["benchmark", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("BENCHMARK_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.extraction_benchmark import (
            BenchmarkError,
            ExtractionBenchmark,
        )

        try:
            benchmark_summary = ExtractionBenchmark(root).run()
        except (BenchmarkError, OSError) as exc:
            print(f"BENCHMARK_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"BENCHMARK_VALID rows={benchmark_summary.rows} "
            f"correct={benchmark_summary.correct} errors={benchmark_summary.errors} "
            f"eligible={benchmark_summary.eligible_rows} "
            f"precision={benchmark_summary.precision:.3f} "
            f"recall={benchmark_summary.recall:.3f} "
            f"calibration_error={benchmark_summary.calibration_error:.3f} "
            f"g2_status={benchmark_summary.g2_status}"
        )
        return 0
    if args.command == "model":
        if args.model_command not in {
            "evaluate-real",
            "audit-source-candidates",
            "audit-source-discovery",
            "audit-proteomics-sources",
            "acquire-proteomics-sources",
            "audit-proteomics-acquisition",
            "profile-proteomics-results",
            "audit-cc0-target-admission",
            "audit-cc0-target-discovery",
            "audit-cc0-target-rescreen",
            "audit-two-lab-corona-pair",
            "audit-two-lab-corona-assets",
            "audit-cc0-pxd030327-unit-map",
            "audit-t129-current-target-evidence",
            "audit-license-bound-source-maps",
            "audit-pxd017052-source-data",
            "audit-pxd017052-complete-attachments",
        }:
            parser.parse_args(["model", "--help"])
            return 0
        if args.model_command in {
            "acquire-proteomics-sources",
            "audit-proteomics-acquisition",
        }:
            from biointerfaceos.real_proteomics_acquisition import (
                RealProteomicsAcquisitionError,
                RealProteomicsAcquisitionWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "REAL_PROTEOMICS_ACQUISITION_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            acquisition_workflow = RealProteomicsAcquisitionWorkflow(root)
            try:
                if args.model_command == "acquire-proteomics-sources":
                    acquisition_summary = acquisition_workflow.stage(
                        strict=args.strict,
                        source_ids=args.source,
                    )
                    print(
                        "REAL_PROTEOMICS_ACQUISITION_STAGED "
                        f"assets={acquisition_summary.asset_count} "
                        f"sources={acquisition_summary.source_count} "
                        "target_frozen=false model_fitted=false scientific_submission_ready=false"
                    )
                else:
                    acquisition_summary = acquisition_workflow.run(strict=args.strict)
                    acquisition_workflow.verify()
                    print(
                        "REAL_PROTEOMICS_ACQUISITION_AUDIT_VALID "
                        f"assets={acquisition_summary.asset_count} "
                        f"sources={acquisition_summary.source_count} "
                        "publisher_checksums="
                        f"{acquisition_summary.publisher_checksum_verified_count} "
                        "target_frozen=false model_fitted=false scientific_submission_ready=false"
                    )
            except (RealProteomicsAcquisitionError, OSError) as exc:
                print(f"REAL_PROTEOMICS_ACQUISITION_INVALID: {exc}", file=sys.stderr)
                return 1
            return 0
        if args.model_command == "profile-proteomics-results":
            from biointerfaceos.real_proteomics_result_profile import (
                RealProteomicsResultProfileError,
                RealProteomicsResultProfileWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "REAL_PROTEOMICS_RESULT_PROFILE_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            result_profile_workflow = RealProteomicsResultProfileWorkflow(root)
            try:
                result_profile_summary = result_profile_workflow.run(strict=args.strict)
                result_profile_workflow.verify()
            except (RealProteomicsResultProfileError, OSError) as exc:
                print(f"REAL_PROTEOMICS_RESULT_PROFILE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "REAL_PROTEOMICS_RESULT_PROFILE_VALID "
                f"sources={result_profile_summary.source_count} "
                f"profiles={result_profile_summary.source_result_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-cc0-target-admission":
            from biointerfaceos.cc0_target_admission import (
                CC0TargetAdmissionError,
                CC0TargetAdmissionWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("CC0_TARGET_ADMISSION_INVALID: repository root not found", file=sys.stderr)
                return 1
            cc0_target_admission_workflow = CC0TargetAdmissionWorkflow(root)
            try:
                cc0_target_admission_summary = cc0_target_admission_workflow.run(strict=args.strict)
                cc0_target_admission_workflow.verify()
            except (CC0TargetAdmissionError, OSError) as exc:
                print(f"CC0_TARGET_ADMISSION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "CC0_TARGET_ADMISSION_VALID "
                f"candidates={cc0_target_admission_summary.candidate_source_count} "
                f"laboratories={cc0_target_admission_summary.candidate_laboratory_count} "
                f"source_conditions={cc0_target_admission_summary.source_condition_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-cc0-target-discovery":
            from biointerfaceos.cc0_target_discovery import (
                CC0TargetDiscoveryError,
                CC0TargetDiscoveryWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("CC0_TARGET_DISCOVERY_INVALID: repository root not found", file=sys.stderr)
                return 1
            cc0_target_discovery_workflow = CC0TargetDiscoveryWorkflow(root)
            try:
                cc0_target_discovery_summary = cc0_target_discovery_workflow.run(strict=args.strict)
                cc0_target_discovery_workflow.verify()
            except (CC0TargetDiscoveryError, OSError) as exc:
                print(f"CC0_TARGET_DISCOVERY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "CC0_TARGET_DISCOVERY_VALID "
                f"candidates={cc0_target_discovery_summary.candidate_source_count} "
                f"laboratories={cc0_target_discovery_summary.candidate_laboratory_count} "
                f"screened_assets={cc0_target_discovery_summary.screened_asset_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-cc0-target-rescreen":
            from biointerfaceos.cc0_target_rescreen import (
                CC0TargetRescreenError,
                CC0TargetRescreenWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("CC0_TARGET_RESCREEN_INVALID: repository root not found", file=sys.stderr)
                return 1
            cc0_target_rescreen_workflow = CC0TargetRescreenWorkflow(root)
            try:
                cc0_target_rescreen_summary = cc0_target_rescreen_workflow.run(strict=args.strict)
                cc0_target_rescreen_workflow.verify()
            except (CC0TargetRescreenError, OSError) as exc:
                print(f"CC0_TARGET_RESCREEN_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "CC0_TARGET_RESCREEN_VALID "
                f"candidates={cc0_target_rescreen_summary.candidate_source_count} "
                f"disclosed_laboratories={cc0_target_rescreen_summary.disclosed_laboratory_count} "
                f"screened_assets={cc0_target_rescreen_summary.screened_asset_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-two-lab-corona-pair":
            from biointerfaceos.two_lab_corona_pair_rescreen import (
                TwoLabCoronaPairRescreenError,
                TwoLabCoronaPairRescreenWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("TWO_LAB_CORONA_PAIR_INVALID: repository root not found", file=sys.stderr)
                return 1
            two_lab_pair_workflow = TwoLabCoronaPairRescreenWorkflow(root)
            try:
                two_lab_pair_summary = two_lab_pair_workflow.run(strict=args.strict)
                two_lab_pair_workflow.verify()
            except (TwoLabCoronaPairRescreenError, OSError) as exc:
                print(f"TWO_LAB_CORONA_PAIR_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "TWO_LAB_CORONA_PAIR_VALID "
                f"candidates={two_lab_pair_summary.candidate_source_count} "
                f"laboratories={two_lab_pair_summary.independent_laboratory_count} "
                f"sizes_nm={two_lab_pair_summary.candidate_size_count} "
                f"status={two_lab_pair_summary.status} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-two-lab-corona-assets":
            from biointerfaceos.two_lab_corona_asset_audit import (
                TwoLabCoronaAssetAuditError,
                TwoLabCoronaAssetAuditWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "TWO_LAB_CORONA_ASSET_AUDIT_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            two_lab_asset_workflow = TwoLabCoronaAssetAuditWorkflow(root)
            try:
                two_lab_asset_summary = two_lab_asset_workflow.run(strict=args.strict)
                two_lab_asset_workflow.verify()
            except (TwoLabCoronaAssetAuditError, OSError) as exc:
                print(f"TWO_LAB_CORONA_ASSET_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "TWO_LAB_CORONA_ASSET_AUDIT_VALID "
                f"assets={two_lab_asset_summary.asset_count} sources={two_lab_asset_summary.source_count} "
                f"byte_verified={two_lab_asset_summary.byte_verified_count} "
                f"redistributable={two_lab_asset_summary.redistributable_count} "
                f"status={two_lab_asset_summary.status} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-cc0-pxd030327-unit-map":
            from biointerfaceos.cc0_pxd030327_unit_map import (
                CC0PXD030327UnitMapError,
                CC0PXD030327UnitMapWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("CC0_PXD030327_UNIT_MAP_INVALID: repository root not found", file=sys.stderr)
                return 1
            unit_map_workflow = CC0PXD030327UnitMapWorkflow(root)
            try:
                unit_map_summary = unit_map_workflow.run(strict=args.strict)
                unit_map_workflow.verify()
            except (CC0PXD030327UnitMapError, OSError) as exc:
                print(f"CC0_PXD030327_UNIT_MAP_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "CC0_PXD030327_UNIT_MAP_VALID "
                f"status={unit_map_summary.status} "
                f"unexcluded_units={unit_map_summary.unexcluded_unit_count} "
                f"matrix_runs={unit_map_summary.matrix_run_count} "
                f"unmapped_matrix_columns={unit_map_summary.unmapped_matrix_column_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-t129-current-target-evidence":
            from biointerfaceos.t129_current_target_evidence import (
                T129CurrentTargetEvidenceError,
                T129CurrentTargetEvidenceWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "T129_CURRENT_TARGET_EVIDENCE_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            t129_target_workflow = T129CurrentTargetEvidenceWorkflow(root)
            try:
                t129_target_summary = t129_target_workflow.run(strict=args.strict)
                t129_target_workflow.verify()
            except (T129CurrentTargetEvidenceError, OSError) as exc:
                print(f"T129_CURRENT_TARGET_EVIDENCE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "T129_CURRENT_TARGET_EVIDENCE_VALID "
                f"candidates={t129_target_summary.candidate_source_count} "
                f"laboratories={t129_target_summary.candidate_laboratory_count} "
                f"verified_source_assets={t129_target_summary.verified_source_asset_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-license-bound-source-maps":
            from biointerfaceos.license_bound_source_map import (
                LicenseBoundSourceMapError,
                LicenseBoundSourceMapWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("LICENSE_BOUND_SOURCE_MAP_INVALID: repository root not found", file=sys.stderr)
                return 1
            license_map_workflow = LicenseBoundSourceMapWorkflow(root)
            try:
                license_map_summary = license_map_workflow.run(strict=args.strict)
                license_map_workflow.verify()
            except (LicenseBoundSourceMapError, OSError) as exc:
                print(f"LICENSE_BOUND_SOURCE_MAP_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "LICENSE_BOUND_SOURCE_MAP_VALID "
                f"routes={license_map_summary.route_count} "
                f"laboratories={license_map_summary.independent_laboratory_count} "
                f"analysis_only_complete_maps={license_map_summary.analysis_only_complete_map_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-pxd017052-source-data":
            from biointerfaceos.pxd017052_source_data import (
                PXD017052SourceDataError,
                PXD017052SourceDataWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("PXD017052_SOURCE_DATA_INVALID: repository root not found", file=sys.stderr)
                return 1
            pxd_source_workflow = PXD017052SourceDataWorkflow(root)
            try:
                pxd_source_summary = pxd_source_workflow.run(strict=args.strict)
                pxd_source_workflow.verify()
            except (PXD017052SourceDataError, OSError) as exc:
                print(f"PXD017052_SOURCE_DATA_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "PXD017052_SOURCE_DATA_VALID "
                f"official_assets={pxd_source_summary.official_asset_count} "
                f"result_units={pxd_source_summary.result_unit_count} "
                f"result_to_raw_matches={pxd_source_summary.result_to_raw_match_count} "
                f"explicit_raw_to_particle_maps={pxd_source_summary.explicit_raw_to_particle_map_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-pxd017052-complete-attachments":
            from biointerfaceos.pxd017052_complete_attachments import (
                PXD017052CompleteAttachmentsError,
                PXD017052CompleteAttachmentsWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "PXD017052_COMPLETE_ATTACHMENTS_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            try:
                attachments_summary = PXD017052CompleteAttachmentsWorkflow(root).run(strict=args.strict)
            except (PXD017052CompleteAttachmentsError, OSError) as exc:
                print(f"PXD017052_COMPLETE_ATTACHMENTS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "PXD017052_COMPLETE_ATTACHMENTS_VALID "
                f"extension_assets={attachments_summary.asset_count} "
                f"explicit_unit_particle_maps={attachments_summary.unit_map_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-proteomics-sources":
            from biointerfaceos.real_proteomics_source_preflight import (
                RealProteomicsSourcePreflightError,
                RealProteomicsSourcePreflightWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "REAL_PROTEOMICS_SOURCE_PREFLIGHT_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            try:
                preflight_summary = RealProteomicsSourcePreflightWorkflow(root).run(strict=args.strict)
            except (RealProteomicsSourcePreflightError, OSError) as exc:
                print(f"REAL_PROTEOMICS_SOURCE_PREFLIGHT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "REAL_PROTEOMICS_SOURCE_PREFLIGHT_VALID "
                f"sources={preflight_summary.source_count} "
                f"source_defined_units={preflight_summary.source_defined_unit_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-source-discovery":
            from biointerfaceos.real_model_source_discovery_workflow import (
                RealModelSourceDiscoveryError,
                RealModelSourceDiscoveryWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print(
                    "REAL_MODEL_SOURCE_DISCOVERY_INVALID: repository root not found",
                    file=sys.stderr,
                )
                return 1
            try:
                source_discovery_summary = RealModelSourceDiscoveryWorkflow(root).run(strict=args.strict)
            except (RealModelSourceDiscoveryError, OSError) as exc:
                print(f"REAL_MODEL_SOURCE_DISCOVERY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "REAL_MODEL_SOURCE_DISCOVERY_VALID "
                f"candidates={source_discovery_summary.candidate_count} "
                f"rejected={source_discovery_summary.rejected_candidate_count} "
                f"reserved_lockbox={source_discovery_summary.reserved_lockbox_candidate_count} "
                "admitted=0 model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.model_command == "audit-source-candidates":
            from biointerfaceos.real_model_source_audit import (
                RealModelSourceAudit,
                RealModelSourceAuditError,
            )

            root = find_repository_root()
            if root is None:
                print("REAL_MODEL_SOURCE_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                source_summary = RealModelSourceAudit(root).run(strict=args.strict)
            except (RealModelSourceAuditError, OSError) as exc:
                print(f"REAL_MODEL_SOURCE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"REAL_MODEL_SOURCE_AUDIT_VALID sources={source_summary.source_count} "
                "studies=3 laboratories=3 "
                f"measurement_definitions={source_summary.distinct_measurement_definitions} "
                f"admissible_targets={source_summary.admissible_target_count} "
                "model_fitted=false paired_ablations_run=false "
                "external_ood_evaluated=false independent_validation=false "
                "scientific_submission_ready=false"
            )
            return 0
        from biointerfaceos.real_model_compatibility_workflow import (
            RealModelCompatibilityError,
            RealModelCompatibilityWorkflow,
        )

        root = find_repository_root()
        if root is None:
            print("REAL_MODEL_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            real_model_summary = RealModelCompatibilityWorkflow(root).run(strict=args.strict)
        except (RealModelCompatibilityError, OSError) as exc:
            print(f"REAL_MODEL_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"REAL_MODEL_GATE_VALID sources={real_model_summary.source_count} "
            f"endpoints={real_model_summary.endpoint_count} "
            f"compatible_targets={real_model_summary.compatible_target_count} "
            "model_fitted=false paired_ablations_run=false "
            "external_ood_evaluated=false independent_validation=false "
            "scientific_submission_ready=false"
        )
        return 0
    if args.command == "manuscript":
        if args.manuscript_command not in {"audit-related-work", "audit-portfolio"}:
            parser.parse_args(["manuscript", "--help"])
            return 0
        if args.manuscript_command == "audit-portfolio":
            from biointerfaceos.manuscript_portfolio_workflow import (
                ManuscriptPortfolioError,
                ManuscriptPortfolioWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("MANUSCRIPT_PORTFOLIO_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                portfolio_summary = ManuscriptPortfolioWorkflow(root).run(strict=args.strict)
            except (ManuscriptPortfolioError, OSError) as exc:
                print(f"MANUSCRIPT_PORTFOLIO_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "MANUSCRIPT_PORTFOLIO_VALID "
                f"status={portfolio_summary.status} "
                f"manuscripts={portfolio_summary.manuscript_count} "
                f"protocol_figures={portfolio_summary.protocol_figure_count} "
                f"legacy_withdrawals={portfolio_summary.legacy_withdrawal_count} "
                "historical_fixture_manuscripts_reused=false "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        from biointerfaceos.related_work_workflow import RelatedWorkError, RelatedWorkWorkflow

        root = find_repository_root()
        if root is None:
            print("RELATED_WORK_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            related_work_summary = RelatedWorkWorkflow(root).run(strict=args.strict)
        except (RelatedWorkError, OSError) as exc:
            print(f"RELATED_WORK_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"RELATED_WORK_VALID citations={related_work_summary.citation_count} "
            f"comparators={related_work_summary.comparator_count} "
            f"manuscript_scopes={related_work_summary.manuscript_scope_count} "
            f"glossary_terms={related_work_summary.glossary_term_count} "
            "historical_fixture_manuscripts_retroactively_cleared=false "
            "independent_validation=false scientific_submission_ready=false"
        )
        return 0
    if args.command == "report":
        if args.report_command != "data-coverage":
            parser.parse_args(["report", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("DATA_COVERAGE_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.coverage_audit import DataCoverageAuditor, DataCoverageError

        try:
            coverage_summary = DataCoverageAuditor(root).run()
        except (DataCoverageError, OSError) as exc:
            print(f"DATA_COVERAGE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"DATA_COVERAGE_VALID studies={coverage_summary.independent_studies} "
            f"admitted_candidates={coverage_summary.admitted_candidates} "
            f"represented_candidates={coverage_summary.represented_candidates} "
            f"missing_values={coverage_summary.missing_values} "
            f"gaps={coverage_summary.gaps} "
            f"bias_warnings={coverage_summary.bias_warnings} no_imputation=true"
        )
        return 0
    if args.command == "omics":
        if args.omics_command == "link-modalities":
            root = find_repository_root()
            if root is None:
                print("LINK_MODALITIES_INVALID: repository root not found", file=sys.stderr)
                return 1
            from biointerfaceos.link_workflow import LinkModalitiesError, LinkModalitiesWorkflow

            try:
                link_summary = LinkModalitiesWorkflow(root).run(fixture=True)
            except (LinkModalitiesError, OSError) as exc:
                print(f"LINK_MODALITIES_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"LINK_MODALITIES_VALID links_attempted={link_summary.links_attempted} "
                f"direct={link_summary.direct_links} "
                f"indirect={link_summary.indirect_links} "
                f"unmatched={link_summary.unmatched_links} "
                f"candidate_cards={link_summary.candidate_cards} "
                f"resumed={link_summary.resumed} pseudo_pairs=false causal_claims=false"
            )
            return 0
        if args.omics_command == "derive-signatures":
            root = find_repository_root()
            if root is None:
                print("SIGNATURES_INVALID: repository root not found", file=sys.stderr)
                return 1
            from biointerfaceos.signature_workflow import SignatureWorkflow, SignatureWorkflowError

            try:
                signature_summary = SignatureWorkflow(root).run(fixture=True)
            except (SignatureWorkflowError, OSError) as exc:
                print(f"SIGNATURES_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SIGNATURES_VALID studies={signature_summary.studies} "
                f"samples={signature_summary.samples} "
                f"signatures={signature_summary.signatures} "
                f"scores={signature_summary.scores} "
                f"stable_folds={signature_summary.stable_folds}/"
                f"{signature_summary.total_folds} resumed={signature_summary.resumed} "
                "predefined_data_driven_separate=true leakage_passed=true"
            )
            return 0
        if args.omics_command == "convert":
            root = find_repository_root()
            if root is None:
                print("CONVERSION_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("CONVERSION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.conversion_workflow import ConversionError, ConversionWorkflow

            try:
                conversion_summary = ConversionWorkflow(root).run(fixture=True)
            except (ConversionError, OSError) as exc:
                print(f"CONVERSION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"CONVERSION_VALID records={conversion_summary.records} "
                f"completed={conversion_summary.completed} refused={conversion_summary.refused} "
                f"resumed={conversion_summary.resumed} raw_downloaded=false "
                f"locked_payload_accessed=false"
            )
            return 0
        if args.omics_command == "search":
            root = find_repository_root()
            if root is None:
                print("SEARCH_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("SEARCH_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.sage_search import SageSearchError, SageSearchWorkflow

            try:
                search_summary = SageSearchWorkflow(root).run(fixture=True)
            except (SageSearchError, OSError) as exc:
                print(f"SEARCH_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SAGE_SEARCH_VALID psms={search_summary.psm_rows} "
                f"accepted_psms={search_summary.accepted_psms} "
                f"peptides={search_summary.accepted_peptides} "
                f"proteins={search_summary.accepted_proteins} "
                f"target_psms={search_summary.target_psms} "
                f"decoy_psms={search_summary.decoy_psms} "
                f"estimated_fdr={search_summary.estimated_fdr:.8f} "
                f"recovered_spike_ins={search_summary.recovered_spike_ins}/"
                f"{search_summary.total_spike_ins} resumed={search_summary.resumed}"
            )
            return 0
        if args.omics_command == "quantify":
            root = find_repository_root()
            if root is None:
                print("QUANTIFICATION_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("QUANTIFICATION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.quantification_workflow import (
                QuantificationError,
                QuantificationWorkflow,
            )

            try:
                quantification_summary = QuantificationWorkflow(root).run(fixture=True)
            except (QuantificationError, OSError) as exc:
                print(f"QUANTIFICATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"LFQ_VALID runs={quantification_summary.runs} "
                f"samples={quantification_summary.samples} "
                f"proteins={quantification_summary.quantifiable_proteins} "
                f"groups={quantification_summary.groups} "
                f"missing_cells={quantification_summary.missing_cells} "
                f"contaminant_groups={quantification_summary.contaminant_groups} "
                f"ratios={quantification_summary.ratios_passed}/"
                f"{quantification_summary.ratios_total} resumed={quantification_summary.resumed}"
            )
            return 0
        if args.omics_command == "harmonize-corona":
            root = find_repository_root()
            if root is None:
                print("HARMONIZE_INVALID: repository root not found", file=sys.stderr)
                return 1
            from biointerfaceos.harmonize_corona import (
                HarmonizationError,
                HarmonizationWorkflow,
            )

            try:
                harmonization_summary = HarmonizationWorkflow(root).run(fixture=True)
            except (HarmonizationError, OSError) as exc:
                print(f"HARMONIZE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"HARMONIZE_VALID projects={harmonization_summary.projects} "
                f"samples={harmonization_summary.samples} "
                f"proteins={harmonization_summary.proteins} "
                f"modules={harmonization_summary.modules} "
                f"missing_cells={harmonization_summary.missing_cells} "
                f"mapping_rows={harmonization_summary.mapping_rows} "
                f"resumed={harmonization_summary.resumed}"
            )
            return 0
        if args.omics_command == "qc-pride":
            root = find_repository_root()
            if root is None:
                print("PRIDE_QC_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("PRIDE_QC_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.pride_qc import PrideQCError, PrideQCWorkflow

            try:
                pride_qc_summary = PrideQCWorkflow(root).run(fixture=True)
            except (PrideQCError, OSError) as exc:
                print(f"PRIDE_QC_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PRIDE_QC_VALID attempted={pride_qc_summary.attempted_projects} "
                f"processed_passed={pride_qc_summary.processed_qc_passed} "
                f"failed={pride_qc_summary.failed_projects} claims={pride_qc_summary.claims} "
                f"concordant={pride_qc_summary.concordant} "
                f"discrepant={pride_qc_summary.discrepant} "
                f"unavailable={pride_qc_summary.unavailable} "
                f"resumed={pride_qc_summary.resumed}"
            )
            return 0
        if args.omics_command == "geo":
            if args.omics_geo_command == "process":
                root = find_repository_root()
                if root is None:
                    print("GEO_PROCESS_INVALID: repository root not found", file=sys.stderr)
                    return 1
                if args.mode == "raw":
                    if not args.fixture:
                        print(
                            "GEO_PROCESS_INVALID: --fixture is required for raw mode",
                            file=sys.stderr,
                        )
                        return 2
                    from biointerfaceos.geo_raw_processing import (
                        GeoRawProcessingError,
                        GeoRawProcessingWorkflow,
                    )

                    try:
                        raw_summary = GeoRawProcessingWorkflow(root).run(mode=args.mode, fixture=True)
                    except (GeoRawProcessingError, OSError) as exc:
                        print(f"GEO_PROCESS_INVALID: {exc}", file=sys.stderr)
                        return 1
                    print(
                        f"GEO_PROCESS_VALID mode={args.mode} "
                        f"studies_attempted={raw_summary.studies_attempted} "
                        f"studies_passed={raw_summary.studies_passed} "
                        f"excluded_studies={raw_summary.excluded_studies} "
                        f"genes={raw_summary.genes} "
                        f"samples={raw_summary.samples} "
                        f"pairs={raw_summary.pairs} "
                        f"matched_pairs={raw_summary.matched_pairs} "
                        f"unmatched_pairs={raw_summary.unmatched_pairs} "
                        f"resumed={raw_summary.resumed}"
                    )
                    return 0
                from biointerfaceos.geo_processing import (
                    GeoProcessingError,
                    GeoProcessingWorkflow,
                )

                try:
                    processing_summary = GeoProcessingWorkflow(root).run(mode=args.mode)
                except (GeoProcessingError, OSError) as exc:
                    print(f"GEO_PROCESS_INVALID: {exc}", file=sys.stderr)
                    return 1
                print(
                    f"GEO_PROCESS_VALID mode={args.mode} "
                    f"studies_attempted={processing_summary.studies_attempted} "
                    f"studies_passed={processing_summary.studies_passed} "
                    f"excluded_studies={processing_summary.excluded_studies} "
                    f"genes={processing_summary.genes} "
                    f"samples={processing_summary.samples} "
                    f"contrasts={processing_summary.contrasts} "
                    f"missing_cells={processing_summary.missing_cells} "
                    f"resumed={processing_summary.resumed}"
                )
                return 0
            if args.omics_geo_command != "discover":
                parser.parse_args(["omics", "geo", "--help"])
                return 0
            root = find_repository_root()
            if root is None:
                print("GEO_DISCOVERY_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("GEO_DISCOVERY_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.geo_discovery import GeoDiscoveryError, GeoDiscoveryWorkflow

            try:
                discovery_summary = GeoDiscoveryWorkflow(root).run(fixture=True, scope=args.scope)
            except (GeoDiscoveryError, OSError) as exc:
                print(f"GEO_DISCOVERY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"GEO_DISCOVERY_VALID scope={args.scope} "
                f"candidates={discovery_summary.candidates} "
                f"eligible={discovery_summary.eligible} "
                f"restricted_rejected={discovery_summary.restricted_rejected} "
                f"metadata_only={discovery_summary.metadata_only} "
                f"coverage_gaps={discovery_summary.coverage_gaps} "
                f"resumed={discovery_summary.resumed}"
            )
            return 0
        if args.omics_command != "pride" or args.omics_pride_command != "triage":
            parser.parse_args(["omics", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("PRIDE_TRIAGE_INVALID: repository root not found", file=sys.stderr)
            return 1
        from biointerfaceos.pride_triage import PrideTriage, PrideTriageError

        try:
            triage_summary = PrideTriage(root).run(scope=args.scope)
        except (PrideTriageError, OSError) as exc:
            print(f"PRIDE_TRIAGE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"PRIDE_TRIAGE_VALID projects={triage_summary.projects} "
            f"eligible={triage_summary.eligible_projects} "
            f"review={triage_summary.review_projects} "
            f"metadata_only={triage_summary.metadata_only_projects} "
            f"sample_rows={triage_summary.sample_rows} "
            f"scope={args.scope} raw_downloaded=false locked_payload_accessed=false"
        )
        return 0
    if args.command == "data":
        if args.data_command not in {
            "fetch",
            "build-bronze",
            "build-silver",
            "build-gold-auto",
            "validate",
            "audit-provenance",
            "audit-fulltext-multicore",
            "audit-fulltext-gold-source",
            "audit-pxd017052-source-cells",
            "map-r3-uniprot-human",
            "admit-r3-common-rank-target",
            "build-r3-uniprot-sequence-features",
            "freeze-r3-analysis-protocol",
            "evaluate-r3-common-rank-models",
            "audit-r3-silver-plasma-source",
            "audit-r4-edinburgh-clinical-source",
            "audit-r4-small-molecule-corona-source",
            "audit-r4-pmc13106918-source",
            "verify-r4-pmc13106918-source",
            "audit-r4-pxd068107-source",
            "verify-r4-pxd068107-source",
            "audit-r4-pmc3252235-source",
            "verify-r4-pmc3252235-source",
            "audit-r4-pxd064962-source",
            "verify-r4-pxd064962-source",
            "audit-r4-manchester-nanoomic-source",
            "verify-r4-manchester-nanoomic-source",
            "evaluate-r4-manchester-nanoomic-ood",
            "verify-r4-manchester-nanoomic-ood",
            "audit-r4-pxd017052-nsclc-source",
            "verify-r4-pxd017052-nsclc-source",
            "evaluate-r4-pxd017052-nsclc-biological-ood",
            "verify-r4-pxd017052-nsclc-biological-ood",
            "evaluate-r4-pmc13106918-technical-ood",
            "verify-r4-pmc13106918-technical-ood",
            "evaluate-r4-pxd068107-technical-ood",
            "verify-r4-pxd068107-technical-ood",
            "audit-r4-pmc10257194-paper-source",
            "verify-r4-pmc10257194-paper-source",
            "evaluate-r4-pmc10257194-paper-ood",
            "verify-r4-pmc10257194-paper-ood",
            "audit-r4-three-lab-common-target",
            "verify-r4-three-lab-common-target",
            "audit-r4-t192-three-lab-common-target",
            "verify-r4-t192-three-lab-common-target",
            "audit-r4-t249-four-lab-common-target",
            "verify-r4-t249-four-lab-common-target",
            "audit-r4-t258-source-unit-endpoint-license",
            "verify-r4-t258-source-unit-endpoint-license",
            "evaluate-r4-t250-four-lab-common-target",
            "verify-r4-t250-four-lab-common-target",
            "evaluate-r4-t265-biological-common-target",
            "verify-r4-t265-biological-common-target",
            "evaluate-r4-t273-biological-unit-primary",
            "verify-r4-t273-biological-unit-primary",
            "preflight-r4-t260-external-receipts",
            "preflight-r4-t279-external-receipts",
            "preflight-r4-t286-external-receipts",
            "evaluate-r4-t193-three-lab-prefrozen-target",
            "verify-r4-t193-three-lab-prefrozen-target",
            "evaluate-r4-t194-fulltext-core-facility",
            "verify-r4-t194-fulltext-core-facility",
            "evaluate-r4-t195-three-lab-common-target",
            "verify-r4-t195-three-lab-common-target",
            "evaluate-r4-t282-t195-replicate-aware-refit",
            "verify-r4-t282-t195-replicate-aware-refit",
            "evaluate-r4-t197-source-availability",
            "verify-r4-t197-source-availability",
            "evaluate-r4-t238-four-source-availability",
            "verify-r4-t238-four-source-availability",
            "evaluate-r4-t255-cluster-uncertainty",
            "verify-r4-t255-cluster-uncertainty",
            "evaluate-r4-t198-paper-cohort-missingness",
            "verify-r4-t198-paper-cohort-missingness",
            "evaluate-r4-t200-statistical-closure",
            "verify-r4-t200-statistical-closure",
            "evaluate-r4-t217-statistical-amendment",
            "verify-r4-t217-statistical-amendment",
            "audit-r4-t222-paper-data-fallback",
            "verify-r4-t222-paper-data-fallback",
            "evaluate-r4-t214-source-heterogeneity",
            "verify-r4-t214-source-heterogeneity",
            "evaluate-r4-t284-paper-ood-synthesis",
            "verify-r4-t284-paper-ood-synthesis",
            "audit-r4-dalian-plasma-corona-source",
            "evaluate-r4-dalian-plasma-corona-sensitivity",
            "evaluate-r4-pxd064962-low-coverage-sensitivity",
            "verify-r4-pxd064962-low-coverage-sensitivity",
            "evaluate-r4-small-molecule-corona-ood",
            "audit-r4-ood-effective-n",
            "verify-r4-ood-effective-n",
            "audit-r4-ood-cluster-sensitivity",
            "verify-r4-ood-cluster-sensitivity",
            "evaluate-r3-silver-external-ood",
            "preflight-external-source-intake",
            "preflight-external-verification",
            "preflight-r4-external-receipts",
            "verify-external-verification-signatures",
        }:
            parser.parse_args(["data", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("DATA_FETCH_INVALID: repository root not found", file=sys.stderr)
            return 1
        if args.data_command == "preflight-external-source-intake":
            from biointerfaceos.external_source_intake import (
                ExternalSourceIntakeError,
                ExternalSourceIntakeWorkflow,
            )

            try:
                external_intake_summary = ExternalSourceIntakeWorkflow(args.manifest, args.assets_root).run(
                    strict=args.strict
                )
            except (ExternalSourceIntakeError, OSError) as exc:
                print(f"EXTERNAL_SOURCE_INTAKE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "EXTERNAL_SOURCE_INTAKE_VALID "
                f"status={external_intake_summary.status} "
                f"sources={external_intake_summary.source_count} "
                f"laboratories={external_intake_summary.laboratory_count} "
                f"assets={external_intake_summary.source_asset_count} "
                f"analysis_units={external_intake_summary.analysis_unit_count} "
                "target_admitted=false t121_amendment=false model_fitted=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-fulltext-multicore":
            from biointerfaceos.fulltext_multicore_audit import (
                FulltextMulticoreAuditError,
                FulltextMulticoreAuditWorkflow,
            )

            try:
                fulltext_multicore_summary = FulltextMulticoreAuditWorkflow(root, args.assets_root).run(
                    strict=args.strict
                )
            except (FulltextMulticoreAuditError, OSError) as exc:
                print(f"FULLTEXT_MULTICORE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "FULLTEXT_MULTICORE_AUDIT_VALID "
                f"status={fulltext_multicore_summary.status} "
                f"assets={fulltext_multicore_summary.source_asset_count} "
                f"cores={fulltext_multicore_summary.semiquantitative_core_count} "
                f"analysis_units={fulltext_multicore_summary.analysis_unit_count} "
                f"replicate_source_cells={fulltext_multicore_summary.replicate_source_cell_count} "
                f"numeric_replicate_values={fulltext_multicore_summary.numeric_replicate_value_count} "
                "target=technical_only model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-fulltext-gold-source":
            from biointerfaceos.fulltext_gold_source_audit import (
                FulltextGoldSourceAuditError,
                FulltextGoldSourceAuditWorkflow,
            )

            try:
                fulltext_gold_summary = FulltextGoldSourceAuditWorkflow(root, args.assets_root).run(strict=args.strict)
            except (FulltextGoldSourceAuditError, OSError) as exc:
                print(f"FULLTEXT_GOLD_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "FULLTEXT_GOLD_SOURCE_AUDIT_VALID "
                f"status={fulltext_gold_summary.status} "
                f"assets={fulltext_gold_summary.source_asset_count} "
                f"tables={fulltext_gold_summary.table_count} "
                f"analysis_units={fulltext_gold_summary.analysis_unit_count} "
                f"explicit_zeros={fulltext_gold_summary.explicit_zero_count} "
                "target=source_native_rank_only model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-pxd017052-source-cells":
            from biointerfaceos.pxd017052_source_cell_audit import (
                PXD017052SourceCellAuditError,
                PXD017052SourceCellAuditWorkflow,
            )

            try:
                pxd017052_source_cell_summary = PXD017052SourceCellAuditWorkflow(root, args.assets_root).run(
                    strict=args.strict
                )
            except (PXD017052SourceCellAuditError, OSError) as exc:
                print(f"PXD017052_SOURCE_CELL_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "PXD017052_SOURCE_CELL_AUDIT_VALID "
                f"status={pxd017052_source_cell_summary.status} "
                f"assets={pxd017052_source_cell_summary.source_asset_count} "
                f"protein_rows={pxd017052_source_cell_summary.protein_row_count} "
                f"result_units={pxd017052_source_cell_summary.result_unit_count} "
                f"analysis_units={pxd017052_source_cell_summary.analysis_unit_count} "
                f"source_blanks={pxd017052_source_cell_summary.source_blank_count} "
                "target=source_native_only model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "map-r3-uniprot-human":
            from biointerfaceos.r3_uniprot_mapping import (
                R3UniProtMappingError,
                R3UniProtMappingWorkflow,
            )

            try:
                r3_uniprot_summary = R3UniProtMappingWorkflow(root, args.mapping_root).run(strict=args.strict)
            except (R3UniProtMappingError, OSError) as exc:
                print(f"R3_UNIPROT_MAPPING_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_UNIPROT_MAPPING_VALID "
                f"status={r3_uniprot_summary.status} "
                f"queried_tokens={r3_uniprot_summary.queried_token_count} "
                f"resolved_identifiers={r3_uniprot_summary.resolved_identifier_count} "
                f"shared_canonical_proteins={r3_uniprot_summary.shared_canonical_protein_count} "
                f"shared_source_cells={r3_uniprot_summary.shared_source_cell_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "admit-r3-common-rank-target":
            from biointerfaceos.r3_common_rank_target import (
                R3CommonRankTargetError,
                R3CommonRankTargetWorkflow,
            )

            try:
                common_rank_summary = R3CommonRankTargetWorkflow(root, args.output_data_root).run(strict=args.strict)
            except (R3CommonRankTargetError, OSError) as exc:
                print(f"R3_COMMON_RANK_TARGET_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_COMMON_RANK_TARGET_VALID "
                f"status={common_rank_summary.status} "
                f"shared_proteins={common_rank_summary.shared_canonical_protein_count} "
                f"eligible_observations={common_rank_summary.eligible_rank_observation_count} "
                f"laboratory_anchors={common_rank_summary.laboratory_anchor_count} "
                f"measurement_batches={common_rank_summary.measurement_batch_count} "
                "target_frozen=false model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "build-r3-uniprot-sequence-features":
            from biointerfaceos.r3_uniprot_sequence_features import (
                R3UniProtSequenceFeaturesError,
                R3UniProtSequenceFeaturesWorkflow,
            )

            try:
                sequence_features_summary = R3UniProtSequenceFeaturesWorkflow(root, args.feature_root).run(
                    strict=args.strict
                )
            except (R3UniProtSequenceFeaturesError, OSError) as exc:
                print(f"R3_UNIPROT_SEQUENCE_FEATURES_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_UNIPROT_SEQUENCE_FEATURES_VALID "
                f"status={sequence_features_summary.status} "
                f"canonical_proteins={sequence_features_summary.canonical_protein_count} "
                f"descriptors={sequence_features_summary.descriptor_count} "
                f"response_batches={sequence_features_summary.response_batch_count} "
                "model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "freeze-r3-analysis-protocol":
            from biointerfaceos.r3_analysis_protocol import (
                R3AnalysisProtocolError,
                R3AnalysisProtocolWorkflow,
            )

            try:
                protocol_summary = R3AnalysisProtocolWorkflow(root, args.output_data_root).run(strict=args.strict)
            except (R3AnalysisProtocolError, OSError) as exc:
                print(f"R3_ANALYSIS_PROTOCOL_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_ANALYSIS_PROTOCOL_VALID "
                f"eligible_observations={protocol_summary.eligible_observation_count} "
                f"canonical_proteins={protocol_summary.canonical_protein_count} "
                f"laboratory_anchors={protocol_summary.laboratory_anchor_count} "
                f"measurement_batches={protocol_summary.measurement_batch_count} "
                f"outer_folds={protocol_summary.outer_fold_count} "
                "target_frozen=true model_fitted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r3-common-rank-models":
            from biointerfaceos.r3_model_evaluation import (
                R3ModelEvaluationError,
                R3ModelEvaluationWorkflow,
            )

            try:
                model_evaluation_summary = R3ModelEvaluationWorkflow(
                    root, args.output_data_root, args.feature_root
                ).run(strict=args.strict)
            except (R3ModelEvaluationError, OSError) as exc:
                print(f"R3_MODEL_EVALUATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_MODEL_EVALUATION_VALID "
                f"eligible_observations={model_evaluation_summary.eligible_observation_count} "
                f"canonical_proteins={model_evaluation_summary.canonical_protein_count} "
                f"laboratory_anchors={model_evaluation_summary.laboratory_anchor_count} "
                f"measurement_batches={model_evaluation_summary.measurement_batch_count} "
                f"models={model_evaluation_summary.model_count} "
                "target_frozen=true model_fitted=true independent_validation=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r3-silver-plasma-source":
            from biointerfaceos.r3_silver_plasma_source_audit import (
                R3SilverPlasmaSourceAuditError,
                R3SilverPlasmaSourceAuditWorkflow,
            )

            try:
                silver_source_summary = R3SilverPlasmaSourceAuditWorkflow(
                    root, args.assets_root, output_root=args.output_root
                ).run(strict=args.strict)
            except (R3SilverPlasmaSourceAuditError, OSError) as exc:
                print(f"R3_SILVER_PLASMA_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_SILVER_PLASMA_SOURCE_AUDIT_VALID "
                f"assets={silver_source_summary.source_asset_count} "
                f"protein_rows={silver_source_summary.protein_row_count} "
                f"measurement_batches={silver_source_summary.analysis_measurement_batch_count} "
                f"source_cells={silver_source_summary.source_cell_count} "
                f"positive_source_cells={silver_source_summary.positive_source_cell_count} "
                "model_fitted=false independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-edinburgh-clinical-source":
            from biointerfaceos.r4_edinburgh_clinical_source_audit import (
                R4EdinburghClinicalSourceAuditError,
                R4EdinburghClinicalSourceAuditWorkflow,
            )

            try:
                edinburgh_summary = R4EdinburghClinicalSourceAuditWorkflow(root, args.assets_root).run(
                    strict=args.strict
                )
            except (R4EdinburghClinicalSourceAuditError, OSError) as exc:
                print(f"R4_EDINBURGH_CLINICAL_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_EDINBURGH_CLINICAL_SOURCE_AUDIT_VALID "
                f"assets={edinburgh_summary.source_asset_count} "
                f"protein_rows={edinburgh_summary.protein_row_count} "
                f"measurement_batches={edinburgh_summary.measurement_batch_count} "
                f"shared_canonical_proteins={edinburgh_summary.shared_canonical_protein_count} "
                f"source_cells={edinburgh_summary.source_cell_count} "
                f"positive_source_cells={edinburgh_summary.positive_source_cell_count} "
                "model_fitted=false independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-small-molecule-corona-source":
            from biointerfaceos.r4_small_molecule_corona_source_audit import (
                R4SmallMoleculeCoronaSourceAuditError,
                R4SmallMoleculeCoronaSourceAuditWorkflow,
            )

            try:
                small_molecule_summary = R4SmallMoleculeCoronaSourceAuditWorkflow(root, args.assets_root).run(
                    strict=args.strict
                )
            except (R4SmallMoleculeCoronaSourceAuditError, OSError) as exc:
                print(f"R4_SMALL_MOLECULE_CORONA_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_SMALL_MOLECULE_CORONA_SOURCE_AUDIT_VALID "
                f"assets={small_molecule_summary.source_asset_count} "
                f"protein_rows={small_molecule_summary.protein_row_count} "
                f"all_measurement_batches={small_molecule_summary.all_measurement_batch_count} "
                f"corona_measurement_batches={small_molecule_summary.corona_measurement_batch_count} "
                f"rank_qualified_measurement_batches={small_molecule_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={small_molecule_summary.shared_canonical_protein_count} "
                f"source_cells={small_molecule_summary.source_cell_count} "
                f"positive_source_cells={small_molecule_summary.candidate_positive_source_cell_count} "
                "model_fitted=false independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-pmc13106918-source":
            from biointerfaceos.r4_pmc13106918_source_audit import (
                R4PMC13106918SourceAuditError,
                R4PMC13106918SourceAuditWorkflow,
            )

            try:
                pmc13106918_summary = R4PMC13106918SourceAuditWorkflow(root, args.assets_root).run(strict=args.strict)
            except (R4PMC13106918SourceAuditError, OSError) as exc:
                print(f"R4_PMC13106918_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC13106918_SOURCE_AUDIT_VALID "
                f"assets={pmc13106918_summary.source_asset_count} "
                f"protein_rows={pmc13106918_summary.protein_row_count} "
                f"measurement_batches={pmc13106918_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={pmc13106918_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={pmc13106918_summary.shared_canonical_protein_count} "
                f"source_cells={pmc13106918_summary.source_cell_count} "
                f"positive_source_cells={pmc13106918_summary.positive_source_cell_count} "
                "biological_units=1 laboratories=1 model_fitted=false independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pmc13106918-source":
            from biointerfaceos.r4_pmc13106918_source_audit import (
                R4PMC13106918SourceAuditError,
                R4PMC13106918SourceAuditWorkflow,
            )

            if not args.strict:
                print("R4_PMC13106918_SOURCE_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                pmc13106918_summary = R4PMC13106918SourceAuditWorkflow(root, args.assets_root).verify()
            except (R4PMC13106918SourceAuditError, OSError) as exc:
                print(f"R4_PMC13106918_SOURCE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC13106918_SOURCE_VERIFY_VALID "
                f"assets={pmc13106918_summary.source_asset_count} "
                f"protein_rows={pmc13106918_summary.protein_row_count} "
                f"measurement_batches={pmc13106918_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={pmc13106918_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={pmc13106918_summary.shared_canonical_protein_count} "
                f"source_cells={pmc13106918_summary.source_cell_count} "
                f"positive_source_cells={pmc13106918_summary.positive_source_cell_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-pxd068107-source":
            from biointerfaceos.r4_pxd068107_source_audit import (
                R4PXD068107SourceAuditError,
                R4PXD068107SourceAuditWorkflow,
            )

            try:
                pxd068107_summary = R4PXD068107SourceAuditWorkflow(root, args.assets_root).run(strict=args.strict)
            except (R4PXD068107SourceAuditError, OSError) as exc:
                print(f"R4_PXD068107_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD068107_SOURCE_AUDIT_VALID "
                f"assets={pxd068107_summary.source_asset_count} "
                f"protein_rows={pxd068107_summary.protein_row_count} "
                f"measurement_batches={pxd068107_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={pxd068107_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={pxd068107_summary.shared_canonical_protein_count} "
                f"source_cells={pxd068107_summary.source_cell_count} "
                f"positive_source_cells={pxd068107_summary.positive_source_cell_count} "
                "biological_units=1 laboratories=1 model_fitted=false independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pxd068107-source":
            from biointerfaceos.r4_pxd068107_source_audit import (
                R4PXD068107SourceAuditError,
                R4PXD068107SourceAuditWorkflow,
            )

            if not args.strict:
                print("R4_PXD068107_SOURCE_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                pxd068107_summary = R4PXD068107SourceAuditWorkflow(root, args.assets_root).verify()
            except (R4PXD068107SourceAuditError, OSError) as exc:
                print(f"R4_PXD068107_SOURCE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD068107_SOURCE_VERIFY_VALID "
                f"assets={pxd068107_summary.source_asset_count} "
                f"protein_rows={pxd068107_summary.protein_row_count} "
                f"measurement_batches={pxd068107_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={pxd068107_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={pxd068107_summary.shared_canonical_protein_count} "
                f"source_cells={pxd068107_summary.source_cell_count} "
                f"positive_source_cells={pxd068107_summary.positive_source_cell_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-pmc3252235-source":
            from biointerfaceos.r4_pmc3252235_source_screen import (
                R4PMC3252235SourceScreenError,
                R4PMC3252235SourceScreenWorkflow,
            )

            try:
                pnnl_summary = R4PMC3252235SourceScreenWorkflow(root, args.assets_root).run(strict=args.strict)
            except (R4PMC3252235SourceScreenError, OSError) as exc:
                print(f"R4_PMC3252235_SOURCE_SCREEN_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC3252235_SOURCE_SCREEN_VALID "
                f"source_bytes={pnnl_summary.source_bytes} "
                f"direct_overlap_accessions={pnnl_summary.direct_overlap_accessions} "
                f"measurement_columns={pnnl_summary.measurement_columns} "
                f"rank_qualified_columns={pnnl_summary.rank_qualified_columns} "
                "model_fitted=false independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pmc3252235-source":
            from biointerfaceos.r4_pmc3252235_source_screen import (
                R4PMC3252235SourceScreenError,
                R4PMC3252235SourceScreenWorkflow,
            )

            if not args.strict:
                print("R4_PMC3252235_SOURCE_SCREEN_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                pnnl_summary = R4PMC3252235SourceScreenWorkflow(root, args.assets_root).verify()
            except (R4PMC3252235SourceScreenError, OSError) as exc:
                print(f"R4_PMC3252235_SOURCE_SCREEN_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC3252235_SOURCE_SCREEN_VERIFY_VALID "
                f"source_bytes={pnnl_summary.source_bytes} "
                f"direct_overlap_accessions={pnnl_summary.direct_overlap_accessions} "
                f"measurement_columns={pnnl_summary.measurement_columns} "
                f"rank_qualified_columns={pnnl_summary.rank_qualified_columns} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-pxd064962-source":
            from biointerfaceos.r4_pxd064962_source_audit import (
                R4PXD064962SourceAuditError,
                R4PXD064962SourceAuditWorkflow,
            )

            try:
                pxd064962_summary = R4PXD064962SourceAuditWorkflow(root, args.assets_root).run(strict=args.strict)
            except (R4PXD064962SourceAuditError, OSError) as exc:
                print(f"R4_PXD064962_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD064962_SOURCE_AUDIT_VALID "
                f"source_cells={pxd064962_summary.source_cell_count} "
                f"positive_source_cells={pxd064962_summary.positive_source_cell_count} "
                f"target_source_cells={pxd064962_summary.target_source_cell_count} "
                f"target_positive_source_cells={pxd064962_summary.target_positive_source_cell_count} "
                f"target_positive_batch_observations={pxd064962_summary.target_positive_batch_observation_count} "
                f"unique_target_source_coordinates={pxd064962_summary.unique_target_source_coordinate_count} "
                f"ambiguous_target_source_coordinates={pxd064962_summary.ambiguous_target_source_coordinate_count} "
                f"positive_shared_canonical_proteins={pxd064962_summary.positive_shared_canonical_protein_count} "
                f"biological_units={pxd064962_summary.biological_unit_count} "
                f"measurement_batches={pxd064962_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={pxd064962_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={pxd064962_summary.shared_canonical_protein_count} "
                "primary_ood_minimum_met=false secondary_low_coverage_sensitivity_candidate=true "
                "model_fitted=false independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pxd064962-source":
            from biointerfaceos.r4_pxd064962_source_audit import (
                R4PXD064962SourceAuditError,
                R4PXD064962SourceAuditWorkflow,
            )

            if not args.strict:
                print("R4_PXD064962_SOURCE_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                pxd064962_summary = R4PXD064962SourceAuditWorkflow(root, args.assets_root).verify()
            except (R4PXD064962SourceAuditError, OSError) as exc:
                print(f"R4_PXD064962_SOURCE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD064962_SOURCE_VERIFY_VALID "
                f"source_cells={pxd064962_summary.source_cell_count} "
                f"target_positive_batch_observations={pxd064962_summary.target_positive_batch_observation_count} "
                f"unique_target_source_coordinates={pxd064962_summary.unique_target_source_coordinate_count} "
                f"ambiguous_target_source_coordinates={pxd064962_summary.ambiguous_target_source_coordinate_count} "
                f"biological_units={pxd064962_summary.biological_unit_count} "
                f"measurement_batches={pxd064962_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={pxd064962_summary.rank_qualified_measurement_batch_count} "
                "primary_ood_minimum_met=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-manchester-nanoomic-source":
            from biointerfaceos.r4_manchester_nanoomic_ood import (
                R4ManchesterNanoOmicError,
                R4ManchesterNanoOmicWorkflow,
            )

            try:
                manchester_summary = R4ManchesterNanoOmicWorkflow(root, args.assets_root).audit(strict=args.strict)
            except (R4ManchesterNanoOmicError, OSError) as exc:
                print(f"R4_MANCHESTER_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_MANCHESTER_SOURCE_AUDIT_VALID "
                f"source_cells={manchester_summary.source_cell_count} "
                f"positive_source_cells={manchester_summary.positive_source_cell_count} "
                f"biological_units={manchester_summary.biological_unit_count} "
                f"measurement_batches={manchester_summary.measurement_batch_count} "
                f"rank_qualified_batches={manchester_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={manchester_summary.shared_canonical_protein_count} "
                "analysis_only=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-manchester-nanoomic-source":
            from biointerfaceos.r4_manchester_nanoomic_ood import (
                R4ManchesterNanoOmicError,
                R4ManchesterNanoOmicWorkflow,
            )

            if not args.strict:
                print("R4_MANCHESTER_SOURCE_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                manchester_summary = R4ManchesterNanoOmicWorkflow(root, args.assets_root).verify_audit()
            except (R4ManchesterNanoOmicError, OSError) as exc:
                print(f"R4_MANCHESTER_SOURCE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_MANCHESTER_SOURCE_VERIFY_VALID "
                f"source_cells={manchester_summary.source_cell_count} "
                f"positive_source_cells={manchester_summary.positive_source_cell_count} "
                f"biological_units={manchester_summary.biological_unit_count} "
                f"measurement_batches={manchester_summary.measurement_batch_count} "
                f"rank_qualified_batches={manchester_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={manchester_summary.shared_canonical_protein_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-manchester-nanoomic-ood":
            from biointerfaceos.r4_manchester_nanoomic_ood import (
                R4ManchesterNanoOmicError,
                R4ManchesterNanoOmicWorkflow,
            )

            try:
                manchester_ood = R4ManchesterNanoOmicWorkflow(
                    root,
                    root / "data/raw/r4_candidate_pmc13212878/author_repo",
                ).evaluate(strict=args.strict)
            except (R4ManchesterNanoOmicError, OSError) as exc:
                print(f"R4_MANCHESTER_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_MANCHESTER_OOD_VALID "
                f"external_observations={manchester_ood.external_observation_count} "
                f"shared_canonical_proteins={manchester_ood.shared_canonical_protein_count} "
                f"measurement_batches={manchester_ood.external_measurement_batch_count} "
                f"biological_units={manchester_ood.biological_unit_count} "
                f"models={manchester_ood.model_count} analysis_only=true "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-manchester-nanoomic-ood":
            from biointerfaceos.r4_manchester_nanoomic_ood import (
                R4ManchesterNanoOmicError,
                R4ManchesterNanoOmicWorkflow,
            )

            if not args.strict:
                print("R4_MANCHESTER_OOD_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                manchester_ood = R4ManchesterNanoOmicWorkflow(
                    root, root / "data/raw/r4_candidate_pmc13212878/author_repo"
                ).verify_ood()
            except (OSError, R4ManchesterNanoOmicError) as exc:
                print(f"R4_MANCHESTER_OOD_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_MANCHESTER_OOD_VERIFY_VALID "
                f"external_observations={manchester_ood.external_observation_count} "
                f"measurement_batches={manchester_ood.external_measurement_batch_count} "
                f"biological_units={manchester_ood.biological_unit_count} "
                "analysis_only=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-pxd017052-nsclc-source":
            from biointerfaceos.r4_pxd017052_nsclc_source_audit import (
                R4PXD017052NSCLCSourceAuditError,
                R4PXD017052NSCLCSourceAuditWorkflow,
            )

            try:
                nsclc_summary = R4PXD017052NSCLCSourceAuditWorkflow(root, args.assets_root).run(strict=args.strict)
            except (R4PXD017052NSCLCSourceAuditError, OSError) as exc:
                print(f"R4_PXD017052_NSCLC_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD017052_NSCLC_SOURCE_AUDIT_VALID "
                f"assets={nsclc_summary.source_asset_count} "
                f"protein_rows={nsclc_summary.protein_row_count} "
                f"biological_units={nsclc_summary.biological_unit_count} "
                f"measurement_batches={nsclc_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={nsclc_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={nsclc_summary.shared_canonical_protein_count} "
                f"source_cells={nsclc_summary.source_cell_count} "
                f"positive_source_cells={nsclc_summary.positive_source_cell_count} "
                "laboratories=1 model_fitted=false independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pxd017052-nsclc-source":
            from biointerfaceos.r4_pxd017052_nsclc_source_audit import (
                R4PXD017052NSCLCSourceAuditError,
                R4PXD017052NSCLCSourceAuditWorkflow,
            )

            if not args.strict:
                print("R4_PXD017052_NSCLC_SOURCE_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                nsclc_summary = R4PXD017052NSCLCSourceAuditWorkflow(root, args.assets_root).verify()
            except (R4PXD017052NSCLCSourceAuditError, OSError) as exc:
                print(f"R4_PXD017052_NSCLC_SOURCE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD017052_NSCLC_SOURCE_VERIFY_VALID "
                f"biological_units={nsclc_summary.biological_unit_count} "
                f"measurement_batches={nsclc_summary.measurement_batch_count} "
                f"rank_qualified_measurement_batches={nsclc_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={nsclc_summary.shared_canonical_protein_count} "
                f"source_cells={nsclc_summary.source_cell_count} "
                f"positive_source_cells={nsclc_summary.positive_source_cell_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-pxd017052-nsclc-biological-ood":
            from biointerfaceos.r4_pxd017052_nsclc_biological_ood import (
                R4PXD017052NSCLCBOODError,
                R4PXD017052NSCLCBOODWorkflow,
            )

            try:
                nsclc_ood = R4PXD017052NSCLCBOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pxd017052_nsclc",
                ).run(strict=args.strict)
            except (R4PXD017052NSCLCBOODError, OSError) as exc:
                print(f"R4_PXD017052_NSCLC_BIOLOGICAL_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD017052_NSCLC_BIOLOGICAL_OOD_VALID "
                f"development_observations={nsclc_ood.development_observation_count} "
                f"external_observations={nsclc_ood.external_observation_count} "
                f"external_shared_canonical_proteins={nsclc_ood.external_shared_canonical_protein_count} "
                f"external_measurement_batches={nsclc_ood.external_measurement_batch_count} "
                f"biological_units={nsclc_ood.biological_unit_count} models={nsclc_ood.model_count} laboratories=1 "
                "independent_validation=false external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pxd017052-nsclc-biological-ood":
            from biointerfaceos.r4_pxd017052_nsclc_biological_ood import (
                R4PXD017052NSCLCBOODError,
                R4PXD017052NSCLCBOODWorkflow,
            )

            if not args.strict:
                print(
                    "R4_PXD017052_NSCLC_BIOLOGICAL_OOD_VERIFY_INVALID: requires --strict",
                    file=sys.stderr,
                )
                return 1
            try:
                nsclc_ood = R4PXD017052NSCLCBOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pxd017052_nsclc",
                ).verify()
            except (R4PXD017052NSCLCBOODError, OSError) as exc:
                print(f"R4_PXD017052_NSCLC_BIOLOGICAL_OOD_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD017052_NSCLC_BIOLOGICAL_OOD_VERIFY_VALID "
                f"development_observations={nsclc_ood.development_observation_count} "
                f"external_observations={nsclc_ood.external_observation_count} "
                f"external_measurement_batches={nsclc_ood.external_measurement_batch_count} "
                f"biological_units={nsclc_ood.biological_unit_count} models={nsclc_ood.model_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-pmc13106918-technical-ood":
            from biointerfaceos.r4_pmc13106918_technical_ood import (
                R4PMC13106918TechnicalOODError,
                R4PMC13106918TechnicalOODWorkflow,
            )

            try:
                technical_ood = R4PMC13106918TechnicalOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pmc13106918",
                ).run(strict=args.strict)
            except (R4PMC13106918TechnicalOODError, OSError) as exc:
                print(f"R4_PMC13106918_TECHNICAL_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC13106918_TECHNICAL_OOD_VALID "
                f"development_observations={technical_ood.development_observation_count} "
                f"external_observations={technical_ood.external_observation_count} "
                f"external_shared_canonical_proteins={technical_ood.shared_canonical_protein_count} "
                f"external_measurement_batches={technical_ood.external_measurement_batch_count} "
                f"models={technical_ood.model_count} biological_units=1 "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pmc13106918-technical-ood":
            from biointerfaceos.r4_pmc13106918_technical_ood import (
                R4PMC13106918TechnicalOODError,
                R4PMC13106918TechnicalOODWorkflow,
            )

            if not args.strict:
                print(
                    "R4_PMC13106918_TECHNICAL_OOD_VERIFY_INVALID: requires --strict",
                    file=sys.stderr,
                )
                return 1
            try:
                technical_ood = R4PMC13106918TechnicalOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pmc13106918",
                ).verify()
            except (R4PMC13106918TechnicalOODError, OSError) as exc:
                print(f"R4_PMC13106918_TECHNICAL_OOD_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC13106918_TECHNICAL_OOD_VERIFY_VALID "
                f"development_observations={technical_ood.development_observation_count} "
                f"external_observations={technical_ood.external_observation_count} "
                f"external_shared_canonical_proteins={technical_ood.shared_canonical_protein_count} "
                f"external_measurement_batches={technical_ood.external_measurement_batch_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-pxd068107-technical-ood":
            from biointerfaceos.r4_pxd068107_technical_ood import (
                R4PXD068107TechnicalOODError,
                R4PXD068107TechnicalOODWorkflow,
            )

            try:
                technical_ood = R4PXD068107TechnicalOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pxd068107",
                ).run(strict=args.strict)
            except (R4PXD068107TechnicalOODError, OSError) as exc:
                print(f"R4_PXD068107_TECHNICAL_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD068107_TECHNICAL_OOD_VALID "
                f"development_observations={technical_ood.development_observation_count} "
                f"external_observations={technical_ood.external_observation_count} "
                f"external_shared_canonical_proteins={technical_ood.shared_canonical_protein_count} "
                f"external_measurement_batches={technical_ood.external_measurement_batch_count} "
                f"models={technical_ood.model_count} biological_units=1 laboratories=1 "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pxd068107-technical-ood":
            from biointerfaceos.r4_pxd068107_technical_ood import (
                R4PXD068107TechnicalOODError,
                R4PXD068107TechnicalOODWorkflow,
            )

            if not args.strict:
                print("R4_PXD068107_TECHNICAL_OOD_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                technical_ood = R4PXD068107TechnicalOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pxd068107",
                ).verify()
            except (R4PXD068107TechnicalOODError, OSError) as exc:
                print(f"R4_PXD068107_TECHNICAL_OOD_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD068107_TECHNICAL_OOD_VERIFY_VALID "
                f"development_observations={technical_ood.development_observation_count} "
                f"external_observations={technical_ood.external_observation_count} "
                f"external_shared_canonical_proteins={technical_ood.shared_canonical_protein_count} "
                f"external_measurement_batches={technical_ood.external_measurement_batch_count} "
                f"models={technical_ood.model_count} scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-pmc10257194-paper-source":
            from biointerfaceos.r4_pmc10257194_paper_source_audit import (
                R4PMC10257194PaperSourceAuditError,
                R4PMC10257194PaperSourceAuditWorkflow,
            )

            try:
                paper_summary = R4PMC10257194PaperSourceAuditWorkflow(
                    root, root / "data/raw/r4_candidate_pmc10257194"
                ).run(strict=args.strict)
            except (R4PMC10257194PaperSourceAuditError, OSError) as exc:
                print(f"R4_PMC10257194_PAPER_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC10257194_PAPER_SOURCE_AUDIT_VALID "
                f"source_cells={paper_summary.source_cell_count} "
                f"positive_source_cells={paper_summary.positive_source_cell_count} "
                f"shared_canonical_proteins={paper_summary.shared_canonical_protein_count} "
                f"measurement_batches={paper_summary.measurement_batch_count} "
                f"biological_units={paper_summary.biological_unit_count} "
                "analysis_only=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pmc10257194-paper-source":
            from biointerfaceos.r4_pmc10257194_paper_source_audit import (
                R4PMC10257194PaperSourceAuditError,
                R4PMC10257194PaperSourceAuditWorkflow,
            )

            if not args.strict:
                print(
                    "R4_PMC10257194_PAPER_SOURCE_VERIFY_INVALID: requires --strict",
                    file=sys.stderr,
                )
                return 1
            try:
                paper_summary = R4PMC10257194PaperSourceAuditWorkflow(
                    root, root / "data/raw/r4_candidate_pmc10257194"
                ).verify()
            except (R4PMC10257194PaperSourceAuditError, OSError) as exc:
                print(f"R4_PMC10257194_PAPER_SOURCE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC10257194_PAPER_SOURCE_VERIFY_VALID "
                f"source_cells={paper_summary.source_cell_count} "
                f"positive_source_cells={paper_summary.positive_source_cell_count} "
                f"shared_canonical_proteins={paper_summary.shared_canonical_protein_count} "
                f"measurement_batches={paper_summary.measurement_batch_count} "
                f"biological_units={paper_summary.biological_unit_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-pmc10257194-paper-ood":
            from biointerfaceos.r4_pmc10257194_paper_ood import (
                R4PMC10257194PaperOODError,
                R4PMC10257194PaperOODWorkflow,
            )

            try:
                paper_ood = R4PMC10257194PaperOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pmc10257194",
                ).run(strict=args.strict)
            except (R4PMC10257194PaperOODError, OSError) as exc:
                print(f"R4_PMC10257194_PAPER_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC10257194_PAPER_OOD_VALID "
                f"development_observations={paper_ood.development_observation_count} "
                f"external_observations={paper_ood.external_observation_count} "
                f"external_shared_canonical_proteins={paper_ood.shared_canonical_protein_count} "
                f"external_measurement_batches={paper_ood.external_measurement_batch_count} "
                f"models={paper_ood.model_count} biological_units=45 laboratories=1 "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pmc10257194-paper-ood":
            from biointerfaceos.r4_pmc10257194_paper_ood import (
                R4PMC10257194PaperOODError,
                R4PMC10257194PaperOODWorkflow,
            )

            if not args.strict:
                print(
                    "R4_PMC10257194_PAPER_OOD_VERIFY_INVALID: requires --strict",
                    file=sys.stderr,
                )
                return 1
            try:
                paper_ood = R4PMC10257194PaperOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    root / "data/raw/r4_candidate_pmc10257194",
                ).verify()
            except (R4PMC10257194PaperOODError, OSError) as exc:
                print(f"R4_PMC10257194_PAPER_OOD_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PMC10257194_PAPER_OOD_VERIFY_VALID "
                f"development_observations={paper_ood.development_observation_count} "
                f"external_observations={paper_ood.external_observation_count} "
                f"external_measurement_batches={paper_ood.external_measurement_batch_count} "
                f"models={paper_ood.model_count} scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-three-lab-common-target":
            from biointerfaceos.r4_three_lab_common_target_audit import (
                R4ThreeLabCommonTargetAuditError,
                R4ThreeLabCommonTargetAuditWorkflow,
            )

            try:
                three_lab_summary = R4ThreeLabCommonTargetAuditWorkflow(root).run(strict=args.strict)
            except (R4ThreeLabCommonTargetAuditError, OSError) as exc:
                print(f"R4_THREE_LAB_COMMON_TARGET_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_THREE_LAB_COMMON_TARGET_AUDIT_VALID "
                f"sources={three_lab_summary.source_count} "
                f"laboratories={three_lab_summary.laboratory_anchor_count} "
                f"common_targets={three_lab_summary.common_target_count} "
                f"common_rank_observations={three_lab_summary.common_rank_observation_count} "
                f"selected_source_rows={three_lab_summary.selected_source_row_count} "
                f"measurement_batches={three_lab_summary.measurement_batch_count} "
                f"source_cells={three_lab_summary.source_cell_count} "
                "development_only=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-three-lab-common-target":
            from biointerfaceos.r4_three_lab_common_target_audit import (
                R4ThreeLabCommonTargetAuditError,
                R4ThreeLabCommonTargetAuditWorkflow,
            )

            if not args.strict:
                print("R4_THREE_LAB_COMMON_TARGET_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                three_lab_summary = R4ThreeLabCommonTargetAuditWorkflow(root).verify()
            except (R4ThreeLabCommonTargetAuditError, OSError) as exc:
                print(f"R4_THREE_LAB_COMMON_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_THREE_LAB_COMMON_TARGET_VERIFY_VALID "
                f"sources={three_lab_summary.source_count} "
                f"laboratories={three_lab_summary.laboratory_anchor_count} "
                f"common_targets={three_lab_summary.common_target_count} "
                f"common_rank_observations={three_lab_summary.common_rank_observation_count} "
                f"measurement_batches={three_lab_summary.measurement_batch_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-t192-three-lab-common-target":
            from biointerfaceos.r4_t192_three_lab_common_target import (
                R4T192ThreeLabCommonTargetError,
                R4T192ThreeLabCommonTargetWorkflow,
            )

            try:
                t192_summary = R4T192ThreeLabCommonTargetWorkflow(root).run(strict=args.strict)
            except (R4T192ThreeLabCommonTargetError, OSError) as exc:
                print(f"R4_T192_THREE_LAB_COMMON_TARGET_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T192_THREE_LAB_COMMON_TARGET_AUDIT_VALID "
                f"sources={t192_summary.source_count} "
                f"laboratories={t192_summary.laboratory_anchor_count} "
                f"common_targets={t192_summary.common_target_count} "
                f"common_rows={t192_summary.common_row_count} "
                f"source_cells={t192_summary.source_cell_count} "
                f"rank_eligible_cells={t192_summary.rank_eligible_cell_count} "
                "development_only=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t192-three-lab-common-target":
            from biointerfaceos.r4_t192_three_lab_common_target import (
                R4T192ThreeLabCommonTargetError,
                R4T192ThreeLabCommonTargetWorkflow,
            )

            try:
                t192_summary = R4T192ThreeLabCommonTargetWorkflow(root).verify(strict=args.strict)
            except (R4T192ThreeLabCommonTargetError, OSError) as exc:
                print(f"R4_T192_THREE_LAB_COMMON_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T192_THREE_LAB_COMMON_TARGET_VERIFY_VALID "
                f"sources={t192_summary.source_count} "
                f"laboratories={t192_summary.laboratory_anchor_count} "
                f"common_targets={t192_summary.common_target_count} "
                f"common_rows={t192_summary.common_row_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-t249-four-lab-common-target":
            from biointerfaceos.r4_t249_four_lab_common_target import (
                R4T249FourLabCommonTargetError,
                R4T249FourLabCommonTargetWorkflow,
            )

            try:
                t249_summary = R4T249FourLabCommonTargetWorkflow(root).run(strict=args.strict)
            except (R4T249FourLabCommonTargetError, OSError) as exc:
                print(f"R4_T249_FOUR_LAB_COMMON_TARGET_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T249_FOUR_LAB_COMMON_TARGET_AUDIT_VALID "
                f"sources={t249_summary.source_count} "
                f"laboratories={t249_summary.laboratory_anchor_count} "
                f"common_targets={t249_summary.common_target_count} "
                f"common_rows={t249_summary.common_row_count} "
                f"source_cells={t249_summary.source_cell_count} "
                f"rank_eligible_cells={t249_summary.rank_eligible_cell_count} "
                "development_only=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t249-four-lab-common-target":
            from biointerfaceos.r4_t249_four_lab_common_target import (
                R4T249FourLabCommonTargetError,
                R4T249FourLabCommonTargetWorkflow,
            )

            try:
                t249_summary = R4T249FourLabCommonTargetWorkflow(root).verify(strict=args.strict)
            except (R4T249FourLabCommonTargetError, OSError) as exc:
                print(f"R4_T249_FOUR_LAB_COMMON_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T249_FOUR_LAB_COMMON_TARGET_VERIFY_VALID "
                f"sources={t249_summary.source_count} "
                f"laboratories={t249_summary.laboratory_anchor_count} "
                f"common_targets={t249_summary.common_target_count} "
                f"common_rows={t249_summary.common_row_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-t258-source-unit-endpoint-license":
            from biointerfaceos.r4_t258_source_unit_endpoint_license import (
                R4T258SourceUnitEndpointLicenseError,
                R4T258SourceUnitEndpointLicenseWorkflow,
            )

            try:
                t258_summary = R4T258SourceUnitEndpointLicenseWorkflow(root).run(strict=args.strict)
            except (R4T258SourceUnitEndpointLicenseError, OSError) as exc:
                print(f"R4_T258_SOURCE_UNIT_ENDPOINT_LICENSE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T258_SOURCE_UNIT_ENDPOINT_LICENSE_AUDIT_VALID "
                f"sources={t258_summary.source_count} "
                f"source_cells={t258_summary.source_cell_count} "
                f"rank_eligible_cells={t258_summary.rank_eligible_cell_count} "
                f"encoded_biological_units={t258_summary.encoded_biological_unit_count} "
                "technical_replicates_not_independent=true "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t258-source-unit-endpoint-license":
            from biointerfaceos.r4_t258_source_unit_endpoint_license import (
                R4T258SourceUnitEndpointLicenseError,
                R4T258SourceUnitEndpointLicenseWorkflow,
            )

            try:
                t258_summary = R4T258SourceUnitEndpointLicenseWorkflow(root).verify(strict=args.strict)
            except (R4T258SourceUnitEndpointLicenseError, OSError) as exc:
                print(f"R4_T258_SOURCE_UNIT_ENDPOINT_LICENSE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T258_SOURCE_UNIT_ENDPOINT_LICENSE_VERIFY_VALID "
                f"sources={t258_summary.source_count} "
                f"source_cells={t258_summary.source_cell_count} "
                f"rank_eligible_cells={t258_summary.rank_eligible_cell_count} "
                f"encoded_biological_units={t258_summary.encoded_biological_unit_count} "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t250-four-lab-common-target":
            from biointerfaceos.r4_t250_four_lab_common_target_execution import (
                R4T250FourLabCommonTargetExecutionError,
                R4T250FourLabCommonTargetExecutionWorkflow,
            )

            try:
                t250_summary = R4T250FourLabCommonTargetExecutionWorkflow(root).run(strict=args.strict)
            except (R4T250FourLabCommonTargetExecutionError, OSError) as exc:
                print(f"R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_VALID "
                f"observations={t250_summary.observation_count} "
                f"targets={t250_summary.target_universe_count} "
                f"laboratories={t250_summary.laboratory_anchor_count} "
                f"measurement_batches={t250_summary.measurement_batch_count} "
                f"models={t250_summary.model_count} "
                "model_fitted=true independent_validation=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t250-four-lab-common-target":
            from biointerfaceos.r4_t250_four_lab_common_target_execution import (
                R4T250FourLabCommonTargetExecutionError,
                R4T250FourLabCommonTargetExecutionWorkflow,
            )

            try:
                t250_summary = R4T250FourLabCommonTargetExecutionWorkflow(root).verify(strict=args.strict)
            except (R4T250FourLabCommonTargetExecutionError, OSError) as exc:
                print(f"R4_T250_FOUR_LAB_COMMON_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T250_FOUR_LAB_COMMON_TARGET_VERIFY_VALID "
                f"observations={t250_summary.observation_count} "
                f"targets={t250_summary.target_universe_count} "
                f"laboratories={t250_summary.laboratory_anchor_count} "
                f"measurement_batches={t250_summary.measurement_batch_count} "
                f"models={t250_summary.model_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t265-biological-common-target":
            from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError
            from biointerfaceos.r4_t265_biological_common_target import (
                R4T265BiologicalCommonTargetError,
                R4T265BiologicalCommonTargetWorkflow,
            )

            try:
                t265_summary = R4T265BiologicalCommonTargetWorkflow(root).run(strict=args.strict)
            except (R4T265BiologicalCommonTargetError, OSError, R3ModelEvaluationError) as exc:
                print(f"R4_T265_BIOLOGICAL_COMMON_TARGET_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T265_BIOLOGICAL_COMMON_TARGET_EXECUTION_VALID "
                f"observations={t265_summary.observation_count} "
                f"targets={t265_summary.target_universe_count} "
                f"laboratories={t265_summary.laboratory_anchor_count} "
                f"measurement_batches={t265_summary.measurement_batch_count} "
                f"models={t265_summary.model_count} "
                "biological_units=246 study_held_out=true nested_selection=true cluster_aware=true "
                "analysis_only=true independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t265-biological-common-target":
            from biointerfaceos.r4_t265_biological_common_target import (
                R4T265BiologicalCommonTargetError,
                R4T265BiologicalCommonTargetWorkflow,
            )

            if not args.strict:
                print("R4_T265_BIOLOGICAL_COMMON_TARGET_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                t265_summary = R4T265BiologicalCommonTargetWorkflow(root).verify(strict=True)
            except (R4T265BiologicalCommonTargetError, OSError) as exc:
                print(f"R4_T265_BIOLOGICAL_COMMON_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T265_BIOLOGICAL_COMMON_TARGET_VERIFY_VALID "
                f"observations={t265_summary.observation_count} "
                f"targets={t265_summary.target_universe_count} "
                f"laboratories={t265_summary.laboratory_anchor_count} "
                f"measurement_batches={t265_summary.measurement_batch_count} "
                "biological_units=246 model_fitted=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t273-biological-unit-primary":
            from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError
            from biointerfaceos.r4_t273_biological_unit_primary import (
                R4T273BiologicalUnitPrimaryError,
                R4T273BiologicalUnitPrimaryWorkflow,
            )

            try:
                t273_summary = R4T273BiologicalUnitPrimaryWorkflow(root).run(strict=args.strict)
            except (R4T273BiologicalUnitPrimaryError, OSError, R3ModelEvaluationError) as exc:
                print(f"R4_T273_BIOLOGICAL_UNIT_PRIMARY_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T273_BIOLOGICAL_UNIT_PRIMARY_EXECUTION_VALID "
                f"observations={t273_summary.observation_count} "
                f"targets={t273_summary.target_universe_count} "
                f"laboratories={t273_summary.laboratory_anchor_count} "
                f"measurement_batches={t273_summary.measurement_batch_count} "
                f"models={t273_summary.model_count} biological_unit_primary=true "
                "grouped_nested_selection=true selection_aware_null=true "
                "analysis_only=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t273-biological-unit-primary":
            from biointerfaceos.r4_t273_biological_unit_primary import (
                R4T273BiologicalUnitPrimaryError,
                R4T273BiologicalUnitPrimaryWorkflow,
            )

            if not args.strict:
                print("R4_T273_BIOLOGICAL_UNIT_PRIMARY_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                t273_summary = R4T273BiologicalUnitPrimaryWorkflow(root).verify(strict=True)
            except (R4T273BiologicalUnitPrimaryError, OSError) as exc:
                print(f"R4_T273_BIOLOGICAL_UNIT_PRIMARY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T273_BIOLOGICAL_UNIT_PRIMARY_VERIFY_VALID "
                f"observations={t273_summary.observation_count} "
                f"targets={t273_summary.target_universe_count} "
                f"laboratories={t273_summary.laboratory_anchor_count} "
                f"measurement_batches={t273_summary.measurement_batch_count} "
                "biological_unit_primary=true model_fitted=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t193-three-lab-prefrozen-target":
            from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError
            from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
                R4T193ThreeLabExecutionError,
                R4T193ThreeLabPrefrozenExecutionWorkflow,
            )

            try:
                t193_summary = R4T193ThreeLabPrefrozenExecutionWorkflow(root).run(strict=args.strict)
            except (R4T193ThreeLabExecutionError, OSError, R3ModelEvaluationError) as exc:
                print(f"R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_VALID "
                f"observations={t193_summary.observation_count} "
                f"target_universe={t193_summary.target_universe_count} "
                f"laboratories={t193_summary.laboratory_anchor_count} "
                f"measurement_batches={t193_summary.measurement_batch_count} "
                f"models={t193_summary.model_count} "
                "study_held_out=true nested_selection=true cluster_aware=true "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t193-three-lab-prefrozen-target":
            from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
                R4T193ThreeLabExecutionError,
                R4T193ThreeLabPrefrozenExecutionWorkflow,
            )

            try:
                t193_summary = R4T193ThreeLabPrefrozenExecutionWorkflow(root).verify(strict=args.strict)
            except (R4T193ThreeLabExecutionError, OSError) as exc:
                print(f"R4_T193_THREE_LAB_PREFROZEN_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T193_THREE_LAB_PREFROZEN_TARGET_VERIFY_VALID "
                f"observations={t193_summary.observation_count} "
                f"target_universe={t193_summary.target_universe_count} "
                f"laboratories={t193_summary.laboratory_anchor_count} "
                f"measurement_batches={t193_summary.measurement_batch_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t194-fulltext-core-facility":
            from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError
            from biointerfaceos.r4_t194_fulltext_core_facility_execution import (
                R4T194FulltextCoreFacilityExecutionWorkflow,
                R4T194FulltextExecutionError,
            )

            try:
                t194_summary = R4T194FulltextCoreFacilityExecutionWorkflow(root).run(strict=args.strict)
            except (R4T194FulltextExecutionError, OSError, R3ModelEvaluationError) as exc:
                print(f"R4_T194_FULLTEXT_CORE_FACILITY_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T194_FULLTEXT_CORE_FACILITY_EXECUTION_VALID "
                f"observations={t194_summary.observation_count} "
                f"target_universe={t194_summary.target_universe_count} "
                f"core_facilities={t194_summary.core_facility_count} "
                f"measurement_batches={t194_summary.measurement_batch_count} "
                f"models={t194_summary.model_count} "
                "study_held_out=true nested_selection=true cluster_aware=true "
                "independent_biological_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t194-fulltext-core-facility":
            from biointerfaceos.r4_t194_fulltext_core_facility_execution import (
                R4T194FulltextCoreFacilityExecutionWorkflow,
                R4T194FulltextExecutionError,
            )

            try:
                t194_summary = R4T194FulltextCoreFacilityExecutionWorkflow(root).verify(strict=args.strict)
            except (R4T194FulltextExecutionError, OSError) as exc:
                print(f"R4_T194_FULLTEXT_CORE_FACILITY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T194_FULLTEXT_CORE_FACILITY_VERIFY_VALID "
                f"observations={t194_summary.observation_count} "
                f"target_universe={t194_summary.target_universe_count} "
                f"core_facilities={t194_summary.core_facility_count} "
                f"measurement_batches={t194_summary.measurement_batch_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t195-three-lab-common-target":
            from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError
            from biointerfaceos.r4_t195_three_lab_common_target_execution import (
                R4T195CommonTargetExecutionError,
                R4T195ThreeLabCommonTargetExecutionWorkflow,
            )

            try:
                t195_summary = R4T195ThreeLabCommonTargetExecutionWorkflow(root).run(strict=args.strict)
            except (R4T195CommonTargetExecutionError, OSError, R3ModelEvaluationError) as exc:
                print(f"R4_T195_COMMON_TARGET_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T195_COMMON_TARGET_EXECUTION_VALID "
                f"observations={t195_summary.observation_count} "
                f"target_universe={t195_summary.target_universe_count} "
                f"laboratories={t195_summary.laboratory_anchor_count} "
                f"measurement_batches={t195_summary.measurement_batch_count} "
                f"models={t195_summary.model_count} "
                "study_held_out=true nested_selection=true cluster_aware=true "
                "independent_biological_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t195-three-lab-common-target":
            from biointerfaceos.r4_t195_three_lab_common_target_execution import (
                R4T195CommonTargetExecutionError,
                R4T195ThreeLabCommonTargetExecutionWorkflow,
            )

            try:
                t195_summary = R4T195ThreeLabCommonTargetExecutionWorkflow(root).verify(strict=args.strict)
            except (R4T195CommonTargetExecutionError, OSError) as exc:
                print(f"R4_T195_COMMON_TARGET_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T195_COMMON_TARGET_VERIFY_VALID "
                f"observations={t195_summary.observation_count} "
                f"target_universe={t195_summary.target_universe_count} "
                f"laboratories={t195_summary.laboratory_anchor_count} "
                f"measurement_batches={t195_summary.measurement_batch_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t282-t195-replicate-aware-refit":
            from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError
            from biointerfaceos.r4_t282_t195_replicate_aware_refit import (
                R4T282T195ReplicateAwareRefitError,
                R4T282T195ReplicateAwareRefitWorkflow,
            )

            try:
                t282_summary = R4T282T195ReplicateAwareRefitWorkflow(root).run(strict=args.strict)
            except (R4T282T195ReplicateAwareRefitError, OSError, R3ModelEvaluationError) as exc:
                print(f"R4_T282_T195_REPLICATE_AWARE_REFIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T282_T195_REPLICATE_AWARE_REFIT_VALID "
                f"observations={t282_summary.observation_count} "
                f"target_universe={t282_summary.target_universe_count} "
                f"laboratories={t282_summary.laboratory_anchor_count} "
                f"measurement_batches={t282_summary.measurement_batch_count} "
                f"models={t282_summary.model_count} raw_observations=809 collapsed_groups=165 "
                "technical_replicates_collapsed_before_split=true study_held_out=true "
                "nested_selection=true cluster_aware=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t282-t195-replicate-aware-refit":
            from biointerfaceos.r4_t282_t195_replicate_aware_refit import (
                R4T282T195ReplicateAwareRefitError,
                R4T282T195ReplicateAwareRefitWorkflow,
            )

            try:
                t282_summary = R4T282T195ReplicateAwareRefitWorkflow(root).verify(strict=args.strict)
            except (R4T282T195ReplicateAwareRefitError, OSError) as exc:
                print(f"R4_T282_T195_REPLICATE_AWARE_REFIT_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T282_T195_REPLICATE_AWARE_REFIT_VERIFY_VALID "
                f"observations={t282_summary.observation_count} "
                f"target_universe={t282_summary.target_universe_count} "
                f"laboratories={t282_summary.laboratory_anchor_count} "
                f"measurement_batches={t282_summary.measurement_batch_count} "
                "raw_observations=809 collapsed_groups=165 scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t197-source-availability":
            from biointerfaceos.r4_t197_source_availability_execution import (
                R4T197SourceAvailabilityError,
                R4T197SourceAvailabilityWorkflow,
            )

            try:
                t197_summary = R4T197SourceAvailabilityWorkflow(root).run(strict=args.strict)
            except (R4T197SourceAvailabilityError, OSError) as exc:
                print(f"R4_T197_SOURCE_AVAILABILITY_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T197_SOURCE_AVAILABILITY_EXECUTION_VALID "
                f"observations={t197_summary.observation_count} "
                f"outer_folds={t197_summary.outer_fold_count} "
                f"target_count_minimum={t197_summary.target_count_minimum} "
                f"measurement_batches={t197_summary.measurement_batch_count} "
                f"models={t197_summary.model_count} "
                "development_only_target_membership=true selection_reexecuted=true "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t197-source-availability":
            from biointerfaceos.r4_t197_source_availability_execution import (
                R4T197SourceAvailabilityError,
                R4T197SourceAvailabilityWorkflow,
            )

            try:
                t197_summary = R4T197SourceAvailabilityWorkflow(root).verify(strict=args.strict)
            except (R4T197SourceAvailabilityError, OSError) as exc:
                print(f"R4_T197_SOURCE_AVAILABILITY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T197_SOURCE_AVAILABILITY_VERIFY_VALID "
                f"observations={t197_summary.observation_count} "
                f"outer_folds={t197_summary.outer_fold_count} "
                f"target_count_minimum={t197_summary.target_count_minimum} "
                f"measurement_batches={t197_summary.measurement_batch_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t238-four-source-availability":
            from biointerfaceos.r4_t197_source_availability_execution import R4T197SourceAvailabilityError
            from biointerfaceos.r4_t238_four_source_availability_execution import R4T238FourSourceAvailabilityWorkflow

            try:
                t238_summary = R4T238FourSourceAvailabilityWorkflow(root).run(strict=args.strict)
            except (R4T197SourceAvailabilityError, OSError) as exc:
                print(f"R4_T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_VALID "
                f"observations={t238_summary.observation_count} "
                f"outer_folds={t238_summary.outer_fold_count} "
                f"target_count_minimum={t238_summary.target_count_minimum} "
                f"measurement_batches={t238_summary.measurement_batch_count} "
                f"models={t238_summary.model_count} "
                "development_only_target_membership=true selection_reexecuted=true "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t238-four-source-availability":
            from biointerfaceos.r4_t197_source_availability_execution import R4T197SourceAvailabilityError
            from biointerfaceos.r4_t238_four_source_availability_execution import R4T238FourSourceAvailabilityWorkflow

            try:
                t238_summary = R4T238FourSourceAvailabilityWorkflow(root).verify(strict=args.strict)
            except (R4T197SourceAvailabilityError, OSError) as exc:
                print(f"R4_T238_FOUR_SOURCE_AVAILABILITY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T238_FOUR_SOURCE_AVAILABILITY_VERIFY_VALID "
                f"observations={t238_summary.observation_count} "
                f"outer_folds={t238_summary.outer_fold_count} "
                f"target_count_minimum={t238_summary.target_count_minimum} "
                f"measurement_batches={t238_summary.measurement_batch_count} "
                f"models={t238_summary.model_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t255-cluster-uncertainty":
            from biointerfaceos.r4_t255_cluster_uncertainty import (
                R4T255ClusterUncertaintyError,
                R4T255ClusterUncertaintyWorkflow,
            )

            try:
                t255_summary = R4T255ClusterUncertaintyWorkflow(root).run(strict=args.strict)
            except (R4T255ClusterUncertaintyError, OSError, ValueError) as exc:
                print(f"R4_T255_CLUSTER_UNCERTAINTY_EXECUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T255_CLUSTER_UNCERTAINTY_EXECUTION_VALID "
                f"outer_folds={t255_summary.outer_fold_count} "
                f"models={t255_summary.model_count} "
                f"metric_rows={t255_summary.metric_row_count} "
                "measurement_batch_cluster_bootstrap=true donor_level_effective_n_claimed=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t255-cluster-uncertainty":
            from biointerfaceos.r4_t255_cluster_uncertainty import (
                R4T255ClusterUncertaintyError,
                R4T255ClusterUncertaintyWorkflow,
            )

            try:
                t255_summary = R4T255ClusterUncertaintyWorkflow(root).verify(strict=args.strict)
            except (R4T255ClusterUncertaintyError, OSError, ValueError) as exc:
                print(f"R4_T255_CLUSTER_UNCERTAINTY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T255_CLUSTER_UNCERTAINTY_VERIFY_VALID "
                f"outer_folds={t255_summary.outer_fold_count} "
                f"models={t255_summary.model_count} "
                f"metric_rows={t255_summary.metric_row_count} "
                "donor_level_effective_n_claimed=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t198-paper-cohort-missingness":
            from biointerfaceos.r4_t198_paper_cohort_missingness import (
                R4T198MissingnessError,
                R4T198PaperCohortMissingnessWorkflow,
            )

            try:
                t198_summary = R4T198PaperCohortMissingnessWorkflow(root).run(strict=args.strict)
            except (R4T198MissingnessError, OSError) as exc:
                print(f"R4_T198_PAPER_COHORT_MISSINGNESS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T198_PAPER_COHORT_MISSINGNESS_VALID "
                f"thresholds={t198_summary.threshold_count} "
                f"primary_threshold={t198_summary.primary_threshold} "
                f"primary_batches={t198_summary.primary_batch_count} "
                f"primary_biological_units={t198_summary.primary_biological_unit_count} "
                f"primary_observations={t198_summary.primary_observation_count} "
                "selection_reexecuted=true independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t198-paper-cohort-missingness":
            from biointerfaceos.r4_t198_paper_cohort_missingness import (
                R4T198MissingnessError,
                R4T198PaperCohortMissingnessWorkflow,
            )

            try:
                t198_summary = R4T198PaperCohortMissingnessWorkflow(root).verify(strict=args.strict)
            except (R4T198MissingnessError, OSError) as exc:
                print(f"R4_T198_PAPER_COHORT_MISSINGNESS_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T198_PAPER_COHORT_MISSINGNESS_VERIFY_VALID "
                f"thresholds={t198_summary.threshold_count} "
                f"primary_threshold={t198_summary.primary_threshold} "
                f"primary_batches={t198_summary.primary_batch_count} "
                f"primary_biological_units={t198_summary.primary_biological_unit_count} "
                f"primary_observations={t198_summary.primary_observation_count} "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t200-statistical-closure":
            from biointerfaceos.r4_t200_statistical_closure import (
                R4T200StatisticalClosureError,
                R4T200StatisticalClosureWorkflow,
            )

            try:
                t200_summary = R4T200StatisticalClosureWorkflow(root).run(strict=args.strict)
            except (R4T200StatisticalClosureError, OSError) as exc:
                print(f"R4_T200_STATISTICAL_CLOSURE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T200_STATISTICAL_CLOSURE_VALID "
                f"t197_fold_intervals={t200_summary.t197_fold_interval_count} "
                f"t198_strata={t200_summary.t198_stratum_count} "
                f"t198_threshold_strata={t200_summary.t198_threshold_stratum_count} "
                "estimand_frozen=true multiplicity_policy_frozen=true "
                "missingness_stratified=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t200-statistical-closure":
            from biointerfaceos.r4_t200_statistical_closure import (
                R4T200StatisticalClosureError,
                R4T200StatisticalClosureWorkflow,
            )

            try:
                t200_summary = R4T200StatisticalClosureWorkflow(root).verify(strict=args.strict)
            except (R4T200StatisticalClosureError, OSError) as exc:
                print(f"R4_T200_STATISTICAL_CLOSURE_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T200_STATISTICAL_CLOSURE_VERIFY_VALID "
                f"t197_fold_intervals={t200_summary.t197_fold_interval_count} "
                f"t198_strata={t200_summary.t198_stratum_count} "
                f"t198_threshold_strata={t200_summary.t198_threshold_stratum_count} "
                "estimand_frozen=true multiplicity_policy_frozen=true "
                "missingness_stratified=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t217-statistical-amendment":
            from biointerfaceos.r4_t217_statistical_amendment import (
                R4T217StatisticalAmendmentError,
                R4T217StatisticalAmendmentWorkflow,
            )

            try:
                t217_summary = R4T217StatisticalAmendmentWorkflow(root).run(strict=args.strict)
            except (R4T217StatisticalAmendmentError, OSError) as exc:
                print(f"R4_T217_STATISTICAL_AMENDMENT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T217_STATISTICAL_AMENDMENT_VALID "
                f"availability_rows={t217_summary.availability_row_count} "
                f"missingness_rows={t217_summary.missingness_row_count} "
                f"multiplicity_rows={t217_summary.multiplicity_row_count} "
                "primary_estimand_frozen=true availability_denominators_audited=true "
                "missingness_policy_frozen=true project_multiplicity_ledger_frozen=true "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t217-statistical-amendment":
            from biointerfaceos.r4_t217_statistical_amendment import (
                R4T217StatisticalAmendmentError,
                R4T217StatisticalAmendmentWorkflow,
            )

            try:
                t217_summary = R4T217StatisticalAmendmentWorkflow(root).verify(strict=args.strict)
            except (R4T217StatisticalAmendmentError, OSError) as exc:
                print(f"R4_T217_STATISTICAL_AMENDMENT_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T217_STATISTICAL_AMENDMENT_VERIFY_VALID "
                f"availability_rows={t217_summary.availability_row_count} "
                f"missingness_rows={t217_summary.missingness_row_count} "
                f"multiplicity_rows={t217_summary.multiplicity_row_count} "
                "primary_estimand_frozen=true availability_denominators_audited=true "
                "missingness_policy_frozen=true project_multiplicity_ledger_frozen=true "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-t222-paper-data-fallback":
            from biointerfaceos.r4_paper_data_fallback import (
                R4PaperDataFallbackError,
                R4PaperDataFallbackWorkflow,
            )

            try:
                t222_summary = R4PaperDataFallbackWorkflow(root).run(strict=args.strict)
            except (R4PaperDataFallbackError, OSError) as exc:
                print(f"R4_T222_PAPER_DATA_FALLBACK_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T222_PAPER_DATA_FALLBACK_VALID "
                f"routes={t222_summary.route_count} "
                f"references={t222_summary.reference_count} "
                f"source_registries={t222_summary.source_registry_count} "
                f"source_maps={t222_summary.source_map_count} "
                f"reports={t222_summary.report_count} "
                "published_paper_data_audited=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t222-paper-data-fallback":
            from biointerfaceos.r4_paper_data_fallback import (
                R4PaperDataFallbackError,
                R4PaperDataFallbackWorkflow,
            )

            if not args.strict:
                print(
                    "R4_T222_PAPER_DATA_FALLBACK_VERIFY_INVALID: requires --strict",
                    file=sys.stderr,
                )
                return 1
            try:
                t222_summary = R4PaperDataFallbackWorkflow(root).verify(strict=True)
            except (R4PaperDataFallbackError, OSError) as exc:
                print(f"R4_T222_PAPER_DATA_FALLBACK_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T222_PAPER_DATA_FALLBACK_VERIFY_VALID "
                f"routes={t222_summary.route_count} "
                f"references={t222_summary.reference_count} "
                f"source_registries={t222_summary.source_registry_count} "
                f"source_maps={t222_summary.source_map_count} "
                f"reports={t222_summary.report_count} "
                "published_paper_data_audited=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t214-source-heterogeneity":
            from biointerfaceos.r4_t214_source_heterogeneity import (
                R4T214SourceHeterogeneityError,
                R4T214SourceHeterogeneityWorkflow,
            )

            try:
                t214_summary = R4T214SourceHeterogeneityWorkflow(root).run(strict=args.strict)
            except (R4T214SourceHeterogeneityError, OSError) as exc:
                print(f"R4_T214_SOURCE_HETEROGENEITY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T214_SOURCE_HETEROGENEITY_VALID "
                f"effect_rows={t214_summary.effect_row_count} "
                f"effect_units={t214_summary.primary_effect_unit_count} "
                f"positive_effects={t214_summary.positive_effect_count} "
                f"negative_effects={t214_summary.negative_effect_count} "
                "pooling_prohibited=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t214-source-heterogeneity":
            from biointerfaceos.r4_t214_source_heterogeneity import (
                R4T214SourceHeterogeneityError,
                R4T214SourceHeterogeneityWorkflow,
            )

            try:
                t214_summary = R4T214SourceHeterogeneityWorkflow(root).verify(strict=args.strict)
            except (R4T214SourceHeterogeneityError, OSError) as exc:
                print(f"R4_T214_SOURCE_HETEROGENEITY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T214_SOURCE_HETEROGENEITY_VERIFY_VALID "
                f"effect_rows={t214_summary.effect_row_count} "
                f"effect_units={t214_summary.primary_effect_unit_count} "
                f"positive_effects={t214_summary.positive_effect_count} "
                f"negative_effects={t214_summary.negative_effect_count} "
                "pooling_prohibited=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-t284-paper-ood-synthesis":
            from biointerfaceos.r4_t284_paper_ood_synthesis import (
                R4T284PaperOodSynthesisError,
                R4T284PaperOodSynthesisWorkflow,
            )

            try:
                t284_summary = R4T284PaperOodSynthesisWorkflow(root).run(strict=args.strict)
            except (R4T284PaperOodSynthesisError, OSError) as exc:
                print(f"R4_T284_PAPER_OOD_SYNTHESIS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T284_PAPER_OOD_SYNTHESIS_VALID "
                f"routes={t284_summary.route_count} "
                f"positive_effects={t284_summary.positive_effect_count} "
                f"negative_effects={t284_summary.negative_effect_count} "
                f"near_zero_effects={t284_summary.near_zero_effect_count} "
                "pooling_prohibited=true independent_validation=false "
                "external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-t284-paper-ood-synthesis":
            from biointerfaceos.r4_t284_paper_ood_synthesis import (
                R4T284PaperOodSynthesisError,
                R4T284PaperOodSynthesisWorkflow,
            )

            try:
                t284_summary = R4T284PaperOodSynthesisWorkflow(root).verify(strict=args.strict)
            except (R4T284PaperOodSynthesisError, OSError) as exc:
                print(f"R4_T284_PAPER_OOD_SYNTHESIS_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T284_PAPER_OOD_SYNTHESIS_VERIFY_VALID "
                f"routes={t284_summary.route_count} "
                f"positive_effects={t284_summary.positive_effect_count} "
                f"negative_effects={t284_summary.negative_effect_count} "
                f"near_zero_effects={t284_summary.near_zero_effect_count} "
                "pooling_prohibited=true scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-dalian-plasma-corona-source":
            from biointerfaceos.r4_dalian_plasma_corona_source_audit import (
                R4DalianPlasmaCoronaSourceAuditError,
                R4DalianPlasmaCoronaSourceAuditWorkflow,
            )

            try:
                dalian_summary = R4DalianPlasmaCoronaSourceAuditWorkflow(root, args.assets_root).run(strict=args.strict)
            except (R4DalianPlasmaCoronaSourceAuditError, OSError) as exc:
                print(f"R4_DALIAN_PLASMA_CORONA_SOURCE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_DALIAN_PLASMA_CORONA_SOURCE_AUDIT_VALID "
                f"assets={dalian_summary.source_asset_count} "
                f"protein_rows={dalian_summary.protein_row_count} "
                f"all_measurement_batches={dalian_summary.all_measurement_batch_count} "
                f"corona_measurement_batches={dalian_summary.corona_measurement_batch_count} "
                f"rank_qualified_measurement_batches={dalian_summary.rank_qualified_measurement_batch_count} "
                f"shared_canonical_proteins={dalian_summary.shared_canonical_protein_count} "
                f"source_cells={dalian_summary.source_cell_count} "
                f"positive_source_cells={dalian_summary.candidate_positive_source_cell_count} "
                "primary_ood_minimum_met=false model_fitted=false independent_validation=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-dalian-plasma-corona-sensitivity":
            from biointerfaceos.r4_dalian_plasma_corona_sensitivity import (
                R4DalianPlasmaCoronaSensitivityError,
                R4DalianPlasmaCoronaSensitivityWorkflow,
            )

            try:
                sensitivity = R4DalianPlasmaCoronaSensitivityWorkflow(root).run(strict=args.strict)
            except (R4DalianPlasmaCoronaSensitivityError, OSError) as exc:
                print(f"R4_DALIAN_PLASMA_CORONA_SENSITIVITY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_DALIAN_PLASMA_CORONA_SENSITIVITY_VALID "
                f"external_observations={sensitivity['external_observation_count']} "
                f"external_measurement_batches={sensitivity['external_measurement_batch_count']} "
                "small_n_sensitivity_only=true model_fitted=true independent_validation=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-pxd064962-low-coverage-sensitivity":
            from biointerfaceos.r4_pxd064962_low_coverage_sensitivity import (
                R4PXD064962LowCoverageSensitivityWorkflow,
                R4PXD064962SensitivityError,
            )

            try:
                low_coverage_sensitivity = R4PXD064962LowCoverageSensitivityWorkflow(
                    root, output_root=args.output_root
                ).run(strict=args.strict)
            except (R4PXD064962SensitivityError, OSError) as exc:
                print(f"R4_PXD064962_SENSITIVITY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD064962_SENSITIVITY_VALID "
                f"development_observations={low_coverage_sensitivity.development_observation_count} "
                f"external_observations={low_coverage_sensitivity.external_observation_count} "
                f"all_eligible_batches={low_coverage_sensitivity.all_eligible_batch_count} "
                f"low_coverage_batches={low_coverage_sensitivity.low_coverage_batch_count} "
                f"high_coverage_batches={low_coverage_sensitivity.high_coverage_batch_count} "
                f"biological_units={low_coverage_sensitivity.biological_unit_count} "
                f"positive_targets={low_coverage_sensitivity.shared_positive_target_count} "
                f"models={low_coverage_sensitivity.model_count} primary_ood_minimum_met=false "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-pxd064962-low-coverage-sensitivity":
            from biointerfaceos.r4_pxd064962_low_coverage_sensitivity import (
                R4PXD064962LowCoverageSensitivityWorkflow,
                R4PXD064962SensitivityError,
            )

            if not args.strict:
                print("R4_PXD064962_SENSITIVITY_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                low_coverage_sensitivity = R4PXD064962LowCoverageSensitivityWorkflow(
                    root, output_root=args.output_root
                ).verify()
            except (R4PXD064962SensitivityError, OSError) as exc:
                print(f"R4_PXD064962_SENSITIVITY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_PXD064962_SENSITIVITY_VERIFY_VALID "
                f"external_observations={low_coverage_sensitivity.external_observation_count} "
                f"all_eligible_batches={low_coverage_sensitivity.all_eligible_batch_count} "
                f"low_coverage_batches={low_coverage_sensitivity.low_coverage_batch_count} "
                f"high_coverage_batches={low_coverage_sensitivity.high_coverage_batch_count} "
                "primary_ood_minimum_met=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r4-small-molecule-corona-ood":
            from biointerfaceos.r4_small_molecule_corona_ood import (
                R4SmallMoleculeCoronaOODError,
                R4SmallMoleculeCoronaOODWorkflow,
            )

            try:
                r4_ood_summary = R4SmallMoleculeCoronaOODWorkflow(
                    root,
                    root / "data/raw",
                    root / "data/raw/r3_uniprot_sequence_features",
                    args.source_assets_root,
                ).run(strict=args.strict)
            except (R4SmallMoleculeCoronaOODError, OSError) as exc:
                print(f"R4_SMALL_MOLECULE_CORONA_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_SMALL_MOLECULE_CORONA_OOD_VALID "
                f"development_observations={r4_ood_summary.development_observation_count} "
                f"external_observations={r4_ood_summary.external_observation_count} "
                f"external_shared_canonical_proteins={r4_ood_summary.shared_canonical_protein_count} "
                f"external_measurement_batches={r4_ood_summary.external_measurement_batch_count} "
                f"models={r4_ood_summary.model_count} "
                "independent_validation=false external_scientific_reproduction=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-ood-effective-n":
            from biointerfaceos.r4_ood_effective_n_audit import (
                R4OODEffectiveNAuditError,
                R4OODEffectiveNAuditWorkflow,
            )

            try:
                effective_n_summary = R4OODEffectiveNAuditWorkflow(root).run(strict=args.strict)
            except (R4OODEffectiveNAuditError, OSError) as exc:
                print(f"R4_OOD_EFFECTIVE_N_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_OOD_EFFECTIVE_N_AUDIT_VALID "
                f"source_rows={effective_n_summary.source_row_count} "
                f"measurement_batches={effective_n_summary.measurement_batch_count} "
                f"primary_rank_eligible_batches={effective_n_summary.primary_rank_eligible_batch_count} "
                f"biological_units={effective_n_summary.biological_unit_count} "
                f"laboratories={effective_n_summary.laboratory_count} "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-ood-effective-n":
            from biointerfaceos.r4_ood_effective_n_audit import (
                R4OODEffectiveNAuditError,
                R4OODEffectiveNAuditWorkflow,
            )

            if not args.strict:
                print("R4_OOD_EFFECTIVE_N_VERIFY_INVALID: requires --strict", file=sys.stderr)
                return 1
            try:
                effective_n_summary = R4OODEffectiveNAuditWorkflow(root).verify()
            except (R4OODEffectiveNAuditError, OSError) as exc:
                print(f"R4_OOD_EFFECTIVE_N_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_OOD_EFFECTIVE_N_VERIFY_VALID "
                f"source_rows={effective_n_summary.source_row_count} "
                f"measurement_batches={effective_n_summary.measurement_batch_count} "
                f"primary_rank_eligible_batches={effective_n_summary.primary_rank_eligible_batch_count} "
                f"biological_units={effective_n_summary.biological_unit_count} "
                f"laboratories={effective_n_summary.laboratory_count} "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-r4-ood-cluster-sensitivity":
            from biointerfaceos.r4_ood_cluster_sensitivity import (
                R4OODClusterSensitivityError,
                R4OODClusterSensitivityWorkflow,
            )

            try:
                cluster_summary = R4OODClusterSensitivityWorkflow(root).run(strict=args.strict)
            except (R4OODClusterSensitivityError, OSError) as exc:
                print(f"R4_OOD_CLUSTER_SENSITIVITY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_OOD_CLUSTER_SENSITIVITY_VALID "
                f"batches={cluster_summary.batch_count} "
                f"biological_units={cluster_summary.biological_unit_count} "
                f"laboratories={cluster_summary.laboratory_count} "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-r4-ood-cluster-sensitivity":
            from biointerfaceos.r4_ood_cluster_sensitivity import (
                R4OODClusterSensitivityError,
                R4OODClusterSensitivityWorkflow,
            )

            if not args.strict:
                print(
                    "R4_OOD_CLUSTER_SENSITIVITY_VERIFY_INVALID: requires --strict",
                    file=sys.stderr,
                )
                return 1
            try:
                cluster_summary = R4OODClusterSensitivityWorkflow(root).verify()
            except (R4OODClusterSensitivityError, OSError) as exc:
                print(f"R4_OOD_CLUSTER_SENSITIVITY_VERIFY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_OOD_CLUSTER_SENSITIVITY_VERIFY_VALID "
                f"batches={cluster_summary.batch_count} "
                f"biological_units={cluster_summary.biological_unit_count} "
                f"laboratories={cluster_summary.laboratory_count} "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "evaluate-r3-silver-external-ood":
            from biointerfaceos.r3_silver_external_ood import (
                R3SilverExternalOODerror,
                R3SilverExternalOODWorkflow,
            )

            try:
                silver_ood_summary = R3SilverExternalOODWorkflow(
                    root,
                    args.output_data_root,
                    args.feature_root,
                    args.silver_assets_root,
                    output_root=args.output_root,
                ).run(strict=args.strict)
            except (R3SilverExternalOODerror, OSError) as exc:
                print(f"R3_SILVER_EXTERNAL_OOD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R3_SILVER_EXTERNAL_OOD_VALID "
                f"development_observations={silver_ood_summary.development_observation_count} "
                f"external_observations={silver_ood_summary.external_observation_count} "
                f"shared_canonical_proteins={silver_ood_summary.shared_canonical_protein_count} "
                f"external_measurement_batches={silver_ood_summary.external_measurement_batch_count} "
                f"models={silver_ood_summary.model_count} "
                "independent_validation=false external_scientific_reproduction=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "preflight-external-verification":
            from biointerfaceos.external_verification_intake import (
                ExternalVerificationIntakeError,
                ExternalVerificationIntakeWorkflow,
            )

            try:
                external_verification_summary = ExternalVerificationIntakeWorkflow(
                    args.bundle, args.documents_root
                ).run(strict=args.strict)
            except (ExternalVerificationIntakeError, OSError) as exc:
                print(f"EXTERNAL_VERIFICATION_INTAKE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "EXTERNAL_VERIFICATION_INTAKE_VALID "
                f"status={external_verification_summary.status} "
                f"documents={external_verification_summary.document_count} "
                f"r2_findings={external_verification_summary.finding_count} "
                "external_receipts_accepted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "preflight-r4-external-receipts":
            from biointerfaceos.r4_external_receipt_preflight import (
                R4ExternalReceiptPreflightError,
                R4ExternalReceiptPreflightWorkflow,
            )

            try:
                repository_root_candidate = Path.cwd().resolve(strict=False)
                repository_root: Path | None = repository_root_candidate
                if not args.bundle.resolve(strict=False).is_relative_to(repository_root_candidate):
                    repository_root = None
                r4_receipt_summary = R4ExternalReceiptPreflightWorkflow(
                    bundle_path=args.bundle,
                    documents_root=args.documents_root,
                    receipt_out=args.receipt_out,
                    repository_root=repository_root,
                ).run(strict=args.strict)
            except (R4ExternalReceiptPreflightError, OSError) as exc:
                print(f"R4_EXTERNAL_RECEIPT_PREFLIGHT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_EXTERNAL_RECEIPT_PREFLIGHT_VALID "
                f"status={r4_receipt_summary.status} "
                f"documents={r4_receipt_summary.document_count} "
                f"non_author_declared={r4_receipt_summary.non_author_declared_count} "
                "identity_authenticated=false independence_authenticated=false "
                "protected_lockbox_accepted=false external_scientific_reproduction_accepted=false "
                "external_user_adoption_accepted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "preflight-r4-t260-external-receipts":
            from biointerfaceos.r4_t260_external_receipt_preflight import (
                R4ExternalReceiptPreflightError,
                R4T260ExternalReceiptPreflightError,
                R4T260ExternalReceiptPreflightWorkflow,
            )

            try:
                repository_root_candidate = Path.cwd().resolve(strict=False)
                repository_root: Path | None = repository_root_candidate
                if not args.bundle.resolve(strict=False).is_relative_to(repository_root_candidate):
                    repository_root = None
                t260_receipt_summary = R4T260ExternalReceiptPreflightWorkflow(
                    bundle_path=args.bundle,
                    documents_root=args.documents_root,
                    receipt_out=args.receipt_out,
                    repository_root=repository_root,
                ).run(strict=args.strict)
            except (R4ExternalReceiptPreflightError, R4T260ExternalReceiptPreflightError, OSError) as exc:
                print(f"R4_T260_EXTERNAL_RECEIPT_PREFLIGHT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T260_EXTERNAL_RECEIPT_PREFLIGHT_VALID "
                f"status={t260_receipt_summary.status} "
                f"documents={t260_receipt_summary.document_count} "
                f"non_author_declared={t260_receipt_summary.non_author_declared_count} "
                "identity_authenticated=false independence_authenticated=false "
                "protected_lockbox_accepted=false external_scientific_reproduction_accepted=false "
                "external_user_adoption_accepted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "preflight-r4-t279-external-receipts":
            from biointerfaceos.r4_t279_external_receipt_preflight import (
                R4ExternalReceiptPreflightError,
                R4T279ExternalReceiptPreflightError,
                R4T279ExternalReceiptPreflightWorkflow,
            )

            try:
                repository_root_candidate = Path.cwd().resolve(strict=False)
                repository_root: Path | None = repository_root_candidate
                if not args.bundle.resolve(strict=False).is_relative_to(repository_root_candidate):
                    repository_root = None
                t279_receipt_summary = R4T279ExternalReceiptPreflightWorkflow(
                    bundle_path=args.bundle,
                    documents_root=args.documents_root,
                    receipt_out=args.receipt_out,
                    repository_root=repository_root,
                ).run(strict=args.strict)
            except (R4ExternalReceiptPreflightError, R4T279ExternalReceiptPreflightError, OSError) as exc:
                print(f"R4_T279_EXTERNAL_RECEIPT_PREFLIGHT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T279_EXTERNAL_RECEIPT_PREFLIGHT_VALID "
                f"status={t279_receipt_summary.status} "
                f"documents={t279_receipt_summary.document_count} "
                f"non_author_declared={t279_receipt_summary.non_author_declared_count} "
                "identity_authenticated=false independence_authenticated=false "
                "protected_lockbox_accepted=false external_scientific_reproduction_accepted=false "
                "external_user_adoption_accepted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "preflight-r4-t286-external-receipts":
            from biointerfaceos.r4_t286_external_receipt_preflight import (
                R4T286ExternalReceiptPreflightError,
                R4T286ExternalReceiptPreflightWorkflow,
            )

            try:
                repository_root_candidate = Path.cwd().resolve(strict=False)
                repository_root: Path | None = repository_root_candidate
                if not args.bundle.resolve(strict=False).is_relative_to(repository_root_candidate):
                    repository_root = None
                t286_receipt_summary = R4T286ExternalReceiptPreflightWorkflow(
                    bundle_path=args.bundle,
                    documents_root=args.documents_root,
                    receipt_out=args.receipt_out,
                    repository_root=repository_root,
                ).run(strict=args.strict)
            except (R4T286ExternalReceiptPreflightError, OSError) as exc:
                print(f"R4_T286_EXTERNAL_RECEIPT_PREFLIGHT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "R4_T286_EXTERNAL_RECEIPT_PREFLIGHT_VALID "
                f"status={t286_receipt_summary.status} "
                f"documents={t286_receipt_summary.document_count} "
                f"non_author_declared={t286_receipt_summary.non_author_declared_count} "
                "identity_authenticated=false independence_authenticated=false "
                "protected_lockbox_accepted=false external_scientific_reproduction_accepted=false "
                "external_user_adoption_accepted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "verify-external-verification-signatures":
            from biointerfaceos.external_verification_signature import (
                ExternalVerificationSignatureError,
                ExternalVerificationSignatureWorkflow,
            )

            try:
                external_signature_summary = ExternalVerificationSignatureWorkflow(
                    bundle_path=args.bundle,
                    documents_root=args.documents_root,
                    signature_manifest_path=args.signature_manifest,
                    signatures_root=args.signatures_root,
                    trusted_signer_registry_path=args.trusted_signer_registry,
                    trusted_keys_root=args.trusted_keys_root,
                    receipt_path=args.receipt_out,
                ).run(strict=args.strict)
            except (ExternalVerificationSignatureError, OSError) as exc:
                print(f"EXTERNAL_VERIFICATION_SIGNATURE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "EXTERNAL_VERIFICATION_SIGNATURE_VALID "
                f"status={external_signature_summary.status} "
                f"documents={external_signature_summary.verified_document_count} "
                f"signers={external_signature_summary.verified_signer_count} "
                "identity_authenticated=false independence_authenticated=false "
                "external_receipts_accepted=false scientific_submission_ready=false"
            )
            return 0
        if args.data_command == "audit-provenance":
            from biointerfaceos.empirical_provenance_workflow import (
                EmpiricalProvenanceError,
                EmpiricalProvenanceWorkflow,
            )

            try:
                empirical_provenance_summary = EmpiricalProvenanceWorkflow(root).run(strict=args.strict)
            except (EmpiricalProvenanceError, OSError) as exc:
                print(f"EMPIRICAL_PROVENANCE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "EMPIRICAL_PROVENANCE_VALID "
                f"registry_id={empirical_provenance_summary.registry_id} "
                f"sources={empirical_provenance_summary.source_count} "
                f"laboratories={empirical_provenance_summary.laboratory_count} "
                f"raw_assets={empirical_provenance_summary.raw_asset_count} "
                f"observations={empirical_provenance_summary.observation_count} "
                "empirical_source=true statistical_conclusions=false "
                "independent_validation=false scientific_submission_ready=false"
            )
            return 0
        if not args.fixture:
            print("DATA_FETCH_INVALID: --fixture is required", file=sys.stderr)
            return 2
        if args.data_command == "build-bronze":
            from biointerfaceos.bronze_release import (
                BronzeReleaseBuilder,
                BronzeReleaseError,
            )

            try:
                bronze_summary = BronzeReleaseBuilder(root).build(fixture=True)
            except (BronzeReleaseError, OSError) as exc:
                print(f"BRONZE_BUILD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BRONZE_BUILD_VALID release_id={bronze_summary.release_id} "
                f"manifest_hash={bronze_summary.manifest_hash} "
                f"raw_assets={bronze_summary.raw_assets} "
                f"parsed_assets={bronze_summary.parsed_assets} "
                f"pointer_assets={bronze_summary.pointer_assets} "
                f"license_tiers={bronze_summary.license_tiers} fixture=true"
            )
            return 0
        if args.data_command == "build-silver":
            from biointerfaceos.silver_release import SilverReleaseBuilder, SilverReleaseError

            try:
                silver_summary = SilverReleaseBuilder(root).build(fixture=True)
            except (SilverReleaseError, OSError) as exc:
                print(f"SILVER_BUILD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SILVER_BUILD_VALID release_id={silver_summary.release_id} "
                f"manifest_hash={silver_summary.manifest_hash} "
                f"schema_hash={silver_summary.schema_hash} "
                f"tables={silver_summary.table_count} "
                f"rows={silver_summary.total_rows} "
                f"quarantined_rows={silver_summary.quarantined_rows} fixture=true"
            )
            return 0
        if args.data_command == "build-gold-auto":
            from biointerfaceos.gold_auto import GoldAutoBuilder, GoldAutoError

            try:
                gold_summary = GoldAutoBuilder(root).build(fixture=True)
            except (GoldAutoError, OSError) as exc:
                print(f"GOLD_AUTO_BUILD_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"GOLD_AUTO_BUILD_VALID release_id={gold_summary.release_id} "
                f"manifest_hash={gold_summary.manifest_hash} "
                f"admitted_fields={gold_summary.admitted_fields} "
                f"excluded_fields={gold_summary.excluded_fields} "
                f"agreement_fields={gold_summary.agreement_fields} "
                f"disagreement_fields={gold_summary.disagreement_fields} "
                f"reverse_traces={gold_summary.reverse_traces} fixture=true"
            )
            return 0
        if args.data_command == "validate":
            if args.data_validate_command not in {"silver", "gold-auto"}:
                parser.parse_args(["data", "validate", "--help"])
                return 0
            if args.data_validate_command == "gold-auto":
                from biointerfaceos.gold_auto import GoldAutoBuilder, GoldAutoError

                try:
                    gold_summary = GoldAutoBuilder(root).validate(fixture=True)
                except (GoldAutoError, OSError) as exc:
                    print(f"GOLD_AUTO_VALIDATE_INVALID: {exc}", file=sys.stderr)
                    return 1
                print(
                    f"GOLD_AUTO_VALIDATE_VALID release_id={gold_summary.release_id} "
                    f"manifest_hash={gold_summary.manifest_hash} "
                    f"admitted_fields={gold_summary.admitted_fields} "
                    f"excluded_fields={gold_summary.excluded_fields} "
                    f"reverse_traces={gold_summary.reverse_traces} fixture=true"
                )
                return 0
            from biointerfaceos.silver_release import SilverReleaseBuilder, SilverReleaseError

            try:
                silver_summary = SilverReleaseBuilder(root).validate(fixture=True)
            except (SilverReleaseError, OSError) as exc:
                print(f"SILVER_VALIDATE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SILVER_VALIDATE_VALID release_id={silver_summary.release_id} "
                f"manifest_hash={silver_summary.manifest_hash} "
                f"schema_hash={silver_summary.schema_hash} "
                f"tables={silver_summary.table_count} "
                f"rows={silver_summary.total_rows} "
                f"quarantined_rows={silver_summary.quarantined_rows} fixture=true"
            )
            return 0
        from biointerfaceos.asset_downloader import AssetDownloader, DownloadError
        from biointerfaceos.policy import PolicyConfigError, SourcePolicyEngine

        try:
            data_summary = AssetDownloader(root, SourcePolicyEngine.from_yaml(root)).run()
        except (DownloadError, OSError, PolicyConfigError) as exc:
            print(f"DATA_FETCH_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"DATA_FETCH_VALID promoted={data_summary.promoted} "
            f"quarantined={data_summary.quarantined} "
            f"policy_skipped={data_summary.policy_skipped} "
            f"resumed={data_summary.resumed} "
            f"receipts={data_summary.receipts} bytes={data_summary.bytes} fixture=true"
        )
        return 0
    if args.command == "stats":
        if args.stats_command != "validate-plan":
            parser.parse_args(["stats", "--help"])
            return 0
        from biointerfaceos.empirical_analysis_plan_workflow import (
            EmpiricalAnalysisPlanError,
            EmpiricalAnalysisPlanWorkflow,
        )

        root = find_repository_root()
        if root is None:
            print("EMPIRICAL_ANALYSIS_PLAN_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            empirical_analysis_plan_summary = EmpiricalAnalysisPlanWorkflow(root).run(strict=args.strict)
        except (EmpiricalAnalysisPlanError, OSError) as exc:
            print(f"EMPIRICAL_ANALYSIS_PLAN_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            "EMPIRICAL_ANALYSIS_PLAN_VALID "
            f"plan_id={empirical_analysis_plan_summary.plan_id} "
            f"estimands={empirical_analysis_plan_summary.estimand_count} "
            "development_estimands="
            f"{empirical_analysis_plan_summary.available_development_estimands} "
            f"held_out_estimands_unavailable="
            f"{empirical_analysis_plan_summary.unavailable_held_out_estimands} "
            "outcome_analysis_run=false model_fitted=false "
            "independent_validation=false scientific_submission_ready=false"
        )
        return 0
    if args.command == "assets":
        if args.assets_command != "verify":
            parser.parse_args(["assets", "--help"])
            return 0
        from biointerfaceos.assets import AssetStore, AssetStoreError

        root = find_repository_root()
        if root is None:
            print("ASSETS_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            asset_summary = AssetStore(root).verify()
        except (AssetStoreError, OSError) as exc:
            print(f"ASSETS_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"ASSETS_VALID references={asset_summary.references} "
            f"blobs={asset_summary.unique_blobs} bytes={asset_summary.bytes}"
        )
        return 0
    if args.command == "catalog":
        if args.catalog_command not in {"build", "check"}:
            parser.parse_args(["catalog", "--help"])
            return 0
        from biointerfaceos.catalog import Catalog, CatalogError

        root = find_repository_root()
        if root is None:
            print("CATALOG_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            catalog_summary = Catalog(root).build() if args.catalog_command == "build" else Catalog(root).check()
        except (CatalogError, OSError) as exc:
            print(f"CATALOG_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"CATALOG_VALID schema_version={catalog_summary.schema_version} "
            f"source_rows={catalog_summary.source_rows} "
            f"asset_rows={catalog_summary.asset_rows} "
            f"rejection_rows={catalog_summary.rejection_rows} "
            f"join_rows={catalog_summary.join_rows}"
        )
        return 0
    if args.command == "release":
        if args.release_command not in {
            "audit-public",
            "freeze",
            "freeze-dev",
            "freeze-prelock",
            "verify",
            "verify-prelock",
        }:
            parser.parse_args(["release", "--help"])
            return 0
        if args.release_command == "audit-public":
            root = find_repository_root()
            if root is None:
                print("PUBLIC_RELEASE_AUDIT_INVALID: repository root not found", file=sys.stderr)
                return 1
            from biointerfaceos.public_release_audit_workflow import (
                PublicReleaseAuditError,
                PublicReleaseAuditWorkflow,
            )

            try:
                public_audit = PublicReleaseAuditWorkflow(root).run(strict=args.strict)
            except (PublicReleaseAuditError, OSError) as exc:
                print(f"PUBLIC_RELEASE_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PUBLIC_RELEASE_AUDIT_VALID audit_id={public_audit['audit_id']} "
                f"status={public_audit['status']} assets={public_audit['asset_count']} "
                "historical_fixture_bundle_publicly_released=false "
                "scientific_submission_ready=false"
            )
            return 0 if public_audit["status"] == "PASS_PUBLIC_RELEASE_AUDIT" else 1
        if args.release_command == "freeze-dev":
            root = find_repository_root()
            if root is None:
                print("DEVELOPMENT_RELEASE_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("DEVELOPMENT_RELEASE_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.release_freeze_dev import (
                DevelopmentReleaseFreezeError,
                DevelopmentReleaseFreezeWorkflow,
            )

            try:
                dev_freeze_summary = DevelopmentReleaseFreezeWorkflow(root).run(fixture=True)
            except (DevelopmentReleaseFreezeError, OSError) as exc:
                print(f"DEVELOPMENT_RELEASE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"DEVELOPMENT_RELEASE_VALID release_id={dev_freeze_summary.release_id} "
                f"version={dev_freeze_summary.semantic_version} "
                f"inputs={dev_freeze_summary.input_count} "
                f"data_layers={dev_freeze_summary.data_layers} "
                f"model_layers={dev_freeze_summary.model_layers} "
                f"thresholds={dev_freeze_summary.thresholds} "
                "license_layers_separated="
                f"{str(dev_freeze_summary.license_layers_separated).lower()} "
                "negative_controls_clean="
                f"{str(dev_freeze_summary.negative_controls_clean).lower()} "
                f"resumed={dev_freeze_summary.resumed} target_values_exposed=false"
            )
            return 0
        if args.release_command == "freeze-prelock":
            root = find_repository_root()
            if root is None:
                print("PRELOCK_RELEASE_INVALID: repository root not found", file=sys.stderr)
                return 1
            from biointerfaceos.prelock_release_workflow import (
                PrelockReleaseError,
                PrelockReleaseWorkflow,
            )

            try:
                prelock_summary = PrelockReleaseWorkflow(root).run(fixture=True, strict=args.strict)
            except (PrelockReleaseError, OSError) as exc:
                print(f"PRELOCK_RELEASE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PRELOCK_RELEASE_VALID release_id={prelock_summary.release_id} "
                f"commit={prelock_summary.git_commit[:12]} inputs={prelock_summary.input_count} "
                f"claims={prelock_summary.claim_count} "
                f"manuscripts={prelock_summary.manuscript_count} "
                f"figures={prelock_summary.figure_count} signature={prelock_summary.signature} "
                f"authorization_scope={prelock_summary.authorization_scope} "
                f"lockbox_accessed={str(prelock_summary.lockbox_accessed).lower()} "
                f"resumed={prelock_summary.resumed}"
            )
            return 0
        from biointerfaceos.release import ReleaseError, ReleaseManager

        root = find_repository_root()
        if root is None:
            print("RELEASE_INVALID: repository root not found", file=sys.stderr)
            return 1
        if args.release_command == "verify-prelock":
            from biointerfaceos.prelock_release_workflow import (
                PrelockReleaseError,
                PrelockReleaseWorkflow,
            )

            try:
                prelock_summary = PrelockReleaseWorkflow(root).verify()
            except (PrelockReleaseError, OSError) as exc:
                print(f"PRELOCK_RELEASE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PRELOCK_RELEASE_VERIFIED release_id={prelock_summary.release_id} "
                f"inputs={prelock_summary.input_count} signature={prelock_summary.signature} "
                f"authorization_scope={prelock_summary.authorization_scope} lockbox_accessed=false"
            )
            return 0
        if args.release_command == "verify" and args.release_kind == "bronze":
            from biointerfaceos.bronze_release import (
                BronzeReleaseBuilder,
                BronzeReleaseError,
            )

            try:
                bronze_summary = BronzeReleaseBuilder(root).verify(args.release_id)
            except (BronzeReleaseError, OSError) as exc:
                print(f"BRONZE_RELEASE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"BRONZE_RELEASE_VALID release_id={bronze_summary.release_id} "
                f"manifest_hash={bronze_summary.manifest_hash} "
                f"files={bronze_summary.total_assets} "
                f"raw_assets={bronze_summary.raw_assets} "
                f"parsed_assets={bronze_summary.parsed_assets} "
                f"pointer_assets={bronze_summary.pointer_assets}"
            )
            return 0
        if not args.fixture:
            print("RELEASE_INVALID: --fixture is required", file=sys.stderr)
            return 1
        try:
            release_summary = (
                ReleaseManager(root).freeze(fixture=True)
                if args.release_command == "freeze"
                else ReleaseManager(root).verify(args.release_id)
            )
        except (ReleaseError, OSError) as exc:
            print(f"RELEASE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"RELEASE_VALID id={release_summary.release_id} "
            f"manifest_hash={release_summary.manifest_hash} "
            f"files={release_summary.file_count}"
        )
        return 0
    if args.command == "lockbox":
        if args.lockbox_command == "evaluate-independent":
            from biointerfaceos.independent_evaluation_workflow import (
                IndependentEvaluationError,
                IndependentEvaluationWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("INDEPENDENT_EVALUATION_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                independent_summary = IndependentEvaluationWorkflow(root).run(strict=args.strict)
            except (IndependentEvaluationError, OSError) as exc:
                print(f"INDEPENDENT_EVALUATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                "INDEPENDENT_EVALUATION_VALID "
                f"status={independent_summary.status} "
                f"compatible_targets={independent_summary.compatible_target_count} "
                "external_evaluator_receipt_verified=false "
                f"blocking_reasons={independent_summary.blocking_reason_count} "
                "protected_observations_accessed=false "
                "scientific_submission_ready=false"
            )
            return 0
        if args.lockbox_command == "evaluate":
            from biointerfaceos.lockbox_evaluation_workflow import (
                LockboxEvaluationError,
                LockboxEvaluationWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("LOCKBOX_EVALUATION_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                evaluation_summary = LockboxEvaluationWorkflow(root).run(
                    release=args.release,
                    once=args.once,
                )
            except (LockboxEvaluationError, OSError) as exc:
                print(f"LOCKBOX_EVALUATION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"LOCKBOX_EVALUATION_VALID release_id={evaluation_summary.release_id} "
                f"predictions={evaluation_summary.prediction_count} "
                f"contract_matched={evaluation_summary.contract_matched} "
                f"contract_contradicted={evaluation_summary.contract_contradicted} "
                f"contract_indeterminate={evaluation_summary.contract_indeterminate} "
                f"abstentions={evaluation_summary.abstentions} "
                f"raw_values_written={str(evaluation_summary.raw_values_written).lower()} "
                f"train_calls={evaluation_summary.train_calls} "
                f"tune_calls={evaluation_summary.tune_calls}"
            )
            return 0
        if args.lockbox_command == "audit-results":
            from biointerfaceos.lockbox_audit_workflow import (
                LockboxAuditError,
                LockboxAuditWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("LOCKBOX_AUDIT_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                lockbox_audit_summary = LockboxAuditWorkflow(root).run(strict=args.strict)
            except (LockboxAuditError, OSError) as exc:
                print(f"LOCKBOX_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"LOCKBOX_AUDIT_VALID audit_id={lockbox_audit_summary.audit_id} "
                f"predictions={lockbox_audit_summary.prediction_count} "
                f"replicated={lockbox_audit_summary.replicated} "
                f"refuted={lockbox_audit_summary.refuted} "
                f"inconclusive={lockbox_audit_summary.inconclusive} "
                f"abstentions={lockbox_audit_summary.abstentions} "
                f"claims={lockbox_audit_summary.claim_count} "
                "threshold_changes=0 prediction_rewrites=0 raw_values_written=false"
            )
            return 0
        if args.lockbox_command != "self-test":
            parser.parse_args(["lockbox", "--help"])
            return 0
        from biointerfaceos.lockbox import LockboxError, LockboxFirewall

        root = find_repository_root()
        if root is None:
            print("LOCKBOX_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            firewall = LockboxFirewall(root)
            audit = firewall.self_test(root / "tests/fixtures/lockbox")
            firewall.write_audit(audit)
        except (LockboxError, OSError) as exc:
            print(f"LOCKBOX_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"LOCKBOX_VALID blocked_read={audit['blocked_development_lockbox_read']} "
            f"field_detected={audit['forbidden_field_detected']} "
            f"hash_detected={audit['forbidden_hash_detected']}"
        )
        return 0
    if args.command == "publication":
        if args.publication_command not in {"render", "render-r2", "verify-r2"}:
            parser.parse_args(["publication", "--help"])
            return 0
        if args.publication_command in {"render-r2", "verify-r2"}:
            from biointerfaceos.submission_figure_qa_workflow import (
                SubmissionFigureQAError,
                SubmissionFigureQAWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("R2_FIGURE_QA_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                figure_qa_workflow = SubmissionFigureQAWorkflow(root)
                figure_qa_result = (
                    figure_qa_workflow.run(strict=args.strict)
                    if args.publication_command == "render-r2"
                    else figure_qa_workflow.verify()
                )
            except (SubmissionFigureQAError, OSError) as exc:
                print(f"R2_FIGURE_QA_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"R2_FIGURE_QA_VALID suite_id={figure_qa_result['suite_id']} "
                f"status={figure_qa_result['status']} figures={figure_qa_result['figure_count']} "
                f"withdrawn_historical_figures={figure_qa_result['withdrawn_historical_figure_count']} "
                "field_mapped=true scientific_submission_ready=false"
            )
            return 0
        from biointerfaceos.publication_render_workflow import (
            PublicationRenderError,
            PublicationRenderWorkflow,
        )

        root = find_repository_root()
        if root is None:
            print("PUBLICATION_RENDER_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            publication_result = PublicationRenderWorkflow(root).run(strict=args.strict)
        except (PublicationRenderError, OSError) as exc:
            print(f"PUBLICATION_RENDER_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"PUBLICATION_RENDER_VALID render_id={publication_result['render_id']} "
            f"figures={publication_result['figures']} "
            f"tables={publication_result['tables']} "
            f"source_data_files={publication_result['source_data_files']} "
            f"raster_dpi={publication_result['raster_dpi']} "
            "manual_numeric_edits=0 raw_values_written=false"
        )
        return 0
    if args.command == "reproduce":
        if args.reproduce_command != "release":
            parser.parse_args(["reproduce", "--help"])
            return 0
        from biointerfaceos.r2_release_reproduction_workflow import (
            R2ReleaseReproductionError,
            R2ReleaseReproductionWorkflow,
        )

        root = find_repository_root()
        if root is None:
            print("R2_SOFTWARE_REPLAY_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            replay = R2ReleaseReproductionWorkflow(root).run(strict=args.strict)
        except (R2ReleaseReproductionError, OSError) as exc:
            print(f"R2_SOFTWARE_REPLAY_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"R2_SOFTWARE_REPLAY_VALID repro_id={replay['repro_id']} "
            f"status={replay['status']} source_assets={replay['source_asset_count']} "
            f"rebuilt_protocol_figures={replay['rebuilt_protocol_figures']} "
            "software_replay=true scientific_reproduction=false "
            "scientific_submission_ready=false"
        )
        return 0
    if args.command == "reproduce-clean":
        from biointerfaceos.clean_room_workflow import CleanRoomError, CleanRoomWorkflow

        root = find_repository_root()
        if root is None:
            print("CLEAN_ROOM_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            reproduction_result = CleanRoomWorkflow(root).run(strict=args.strict)
        except (CleanRoomError, OSError) as exc:
            print(f"CLEAN_ROOM_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"CLEAN_ROOM_VALID repro_id={reproduction_result['repro_id']} "
            f"package_sha256={reproduction_result['package_sha256']} "
            f"result_hash={reproduction_result['result_hash']} "
            f"runs={reproduction_result['independent_runs']} "
            f"tests_passed={reproduction_result['benchmark_tests_passed']} "
            "network_accessed=false protected_values_read=false"
        )
        return 0
    if args.command == "agent":
        if args.agent_command == "red-team":
            from biointerfaceos.redteam_agent_workflow import RedTeamError, RedTeamWorkflow

            root = find_repository_root()
            if root is None:
                print("REDTEAM_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                redteam_summary = RedTeamWorkflow(root).run(all_attacks=args.all)
            except (RedTeamError, OSError) as exc:
                print(f"REDTEAM_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"REDTEAM_VALID attacks={redteam_summary.attacks} "
                f"executed={redteam_summary.executed} "
                f"detected={redteam_summary.detected} "
                f"blocked={redteam_summary.blocked} "
                f"critical_findings={redteam_summary.critical_findings} "
                f"remediations={redteam_summary.remediations} "
                f"adverse_results_preserved="
                f"{str(redteam_summary.adverse_results_preserved).lower()} "
                f"release_blocked={str(redteam_summary.release_blocked).lower()} "
                f"selected_pipeline={redteam_summary.selected_pipeline} "
                f"trace_events={redteam_summary.trace_events} "
                f"resumed={redteam_summary.resumed}"
            )
            return 0
        if args.agent_command == "eval" and args.agent_eval_command == "audit":
            from biointerfaceos.resolution_audit_workflow import (
                ResolutionAuditError,
                ResolutionAuditWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("AGENT_AUDIT_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                resolution_audit_summary = ResolutionAuditWorkflow(root).run(fixture=True)
            except (ResolutionAuditError, OSError) as exc:
                print(f"AGENT_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_AUDIT_VALID cases={resolution_audit_summary.cases} "
                f"conflicts={resolution_audit_summary.conflicts} "
                f"detected={resolution_audit_summary.detected} "
                f"quarantined={resolution_audit_summary.quarantined} "
                f"original_assertions_preserved="
                f"{str(resolution_audit_summary.original_assertions_preserved).lower()} "
                f"false_merge_rate={resolution_audit_summary.false_merge_rate:.6f} "
                f"selected_pipeline={resolution_audit_summary.selected_pipeline} "
                f"trace_events={resolution_audit_summary.trace_events} "
                f"resumed={resolution_audit_summary.resumed}"
            )
            return 0
        if args.agent_command == "eval" and args.agent_eval_command == "extraction":
            from biointerfaceos.extraction_agent_workflow import (
                ExtractionAgentError,
                ExtractionAgentWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("AGENT_EXTRACTION_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                extraction_summary = ExtractionAgentWorkflow(root).run(fixture=True)
            except (ExtractionAgentError, OSError) as exc:
                print(f"AGENT_EXTRACTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_EXTRACTION_VALID cases={extraction_summary.cases} "
                f"agent_correct={extraction_summary.agent_correct} "
                f"fixed_correct={extraction_summary.fixed_correct} "
                f"agent_accuracy={extraction_summary.agent_accuracy:.6f} "
                f"fixed_accuracy={extraction_summary.fixed_accuracy:.6f} "
                f"selected_pipeline={extraction_summary.selected_pipeline} "
                f"schema_valid={str(extraction_summary.schema_valid).lower()} "
                f"evidence_grounded={str(extraction_summary.evidence_grounded).lower()} "
                f"trace_events={extraction_summary.trace_events} "
                f"resumed={extraction_summary.resumed}"
            )
            return 0
        if args.agent_command == "eval" and args.agent_eval_command == "source-license":
            from biointerfaceos.source_license_workflow import (
                SourceLicenseError,
                SourceLicenseWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("AGENT_SOURCE_LICENSE_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                source_license_summary = SourceLicenseWorkflow(root).run(fixture=True)
            except (SourceLicenseError, OSError) as exc:
                print(f"AGENT_SOURCE_LICENSE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_SOURCE_LICENSE_VALID cases={source_license_summary.cases} "
                f"recovered={source_license_summary.recovered} "
                f"rejected_or_quarantined={source_license_summary.rejected_or_quarantined} "
                f"evidence_complete={str(source_license_summary.evidence_complete).lower()} "
                f"no_credentials_requested="
                f"{str(source_license_summary.no_credentials_requested).lower()} "
                f"agent_value={source_license_summary.agent_value} "
                f"resumed={source_license_summary.resumed}"
            )
            return 0
        if args.agent_command == "eval" and args.agent_eval_command == "hypothesis":
            from biointerfaceos.hypothesis_agent_workflow import (
                HypothesisAgentError,
                HypothesisAgentWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("AGENT_HYPOTHESIS_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                hypothesis_summary = HypothesisAgentWorkflow(root).run(fixture=True)
            except (HypothesisAgentError, OSError) as exc:
                print(f"AGENT_HYPOTHESIS_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_HYPOTHESIS_VALID proposals={hypothesis_summary.proposals} "
                f"valid={hypothesis_summary.valid_proposals} "
                f"rejected={hypothesis_summary.rejected} "
                f"duplicates={hypothesis_summary.duplicates_rejected} "
                f"falsifiable={hypothesis_summary.falsifiable} "
                f"formalized={hypothesis_summary.formalized} "
                f"evidence_linked={hypothesis_summary.evidence_linked} "
                f"schema_valid={str(hypothesis_summary.schema_valid).lower()} "
                f"lockbox_clean={str(hypothesis_summary.lockbox_clean).lower()} "
                f"claims_auto_accepted="
                f"{str(hypothesis_summary.claims_auto_accepted).lower()} "
                f"selected_pipeline={hypothesis_summary.selected_pipeline} "
                f"trace_events={hypothesis_summary.trace_events} "
                f"resumed={hypothesis_summary.resumed}"
            )
            return 0
        if args.agent_command == "eval" and args.agent_eval_command == "modeling":
            from biointerfaceos.modeling_agent_workflow import (
                ModelingAgentError,
                ModelingAgentWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("AGENT_MODELING_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                modeling_summary = ModelingAgentWorkflow(root).run(fixture=True)
            except (ModelingAgentError, OSError) as exc:
                print(f"AGENT_MODELING_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_MODELING_VALID plans={modeling_summary.plans} "
                f"executable={modeling_summary.executable_plans} "
                f"rejected={modeling_summary.rejected} "
                f"metric_hacking_rejected={modeling_summary.metric_hacking_rejected} "
                f"split_modification_rejected={modeling_summary.split_modification_rejected} "
                f"heldout_tuning_rejected={modeling_summary.heldout_tuning_rejected} "
                f"tests_generated={modeling_summary.tests_generated} "
                f"preregistration_complete="
                f"{str(modeling_summary.preregistration_complete).lower()} "
                f"sandbox_passed={str(modeling_summary.sandbox_passed).lower()} "
                f"splits_unchanged={str(modeling_summary.splits_unchanged).lower()} "
                f"selected_pipeline={modeling_summary.selected_pipeline} "
                f"trace_events={modeling_summary.trace_events} "
                f"resumed={modeling_summary.resumed}"
            )
            return 0
        if args.agent_command == "eval" and args.agent_eval_command == "reproducibility":
            from biointerfaceos.reproducibility_agent_workflow import (
                ReproducibilityAgentError,
                ReproducibilityWorkflow,
            )

            root = find_repository_root()
            if root is None:
                print("AGENT_REPRODUCIBILITY_INVALID: repository root not found", file=sys.stderr)
                return 1
            try:
                reproducibility_summary = ReproducibilityWorkflow(root).run(fixture=True)
            except (ReproducibilityAgentError, OSError) as exc:
                print(f"AGENT_REPRODUCIBILITY_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"AGENT_REPRODUCIBILITY_VALID release_verified="
                f"{str(reproducibility_summary.release_verified).lower()} "
                f"rebuild_clean={str(reproducibility_summary.rebuild_clean).lower()} "
                f"hash_match={str(reproducibility_summary.hash_match).lower()} "
                f"lockbox_activation_blocked="
                f"{str(reproducibility_summary.lockbox_activation_blocked).lower()} "
                f"training_methods_exposed="
                f"{str(reproducibility_summary.training_methods_exposed).lower()} "
                f"selected_pipeline={reproducibility_summary.selected_pipeline} "
                f"trace_events={reproducibility_summary.trace_events} "
                f"resumed={reproducibility_summary.resumed}"
            )
            return 0
        if args.agent_command != "self-test":
            parser.parse_args(["agent", "--help"])
            return 0
        from biointerfaceos.agent_runtime import AgentRuntime, AgentRuntimeError

        root = find_repository_root()
        if root is None:
            print("AGENT_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            agent_summary = AgentRuntime(root).run(fixture=True)
        except (AgentRuntimeError, OSError) as exc:
            print(f"AGENT_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"AGENT_SELF_TEST_VALID agents={agent_summary.agents} tasks={agent_summary.tasks} "
            f"events={agent_summary.events} schema_validated="
            f"{str(agent_summary.schema_validated).lower()} "
            f"tool_allowlist={str(agent_summary.tool_allowlist_passed).lower()} "
            f"budget={str(agent_summary.budget_passed).lower()} "
            f"replay={str(agent_summary.replay_passed).lower()} "
            f"retries={str(agent_summary.retry_passed).lower()} "
            f"trace_sealed={str(agent_summary.trace_sealed).lower()} "
            f"provider_key_required={str(agent_summary.provider_key_required).lower()} "
            f"resumed={agent_summary.resumed}"
        )
        return 0
    if args.command == "ontology":
        if args.ontology_command != "sync":
            parser.parse_args(["ontology", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("ONTOLOGY_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.dry_run:
            print("ONTOLOGY_INVALID: --dry-run is required for this command", file=sys.stderr)
            return 2
        from biointerfaceos.sources.ontology import HOSTS as ontology_hosts
        from biointerfaceos.sources.ontology import SOURCE_NAMES

        print(
            f"ONTOLOGY_SYNC_DRY_RUN sources={len(SOURCE_NAMES)} "
            f"hosts={','.join(ontology_hosts)} network=false binary_assets=0"
        )
        return 0
    if args.command == "search":
        if args.search_command not in {"validate-queries", "run", "expand", "saturation"}:
            parser.parse_args(["search", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("SEARCH_INVALID: repository root not found", file=sys.stderr)
            return 1
        if args.search_command == "validate-queries":
            from biointerfaceos.search_matrix import SearchMatrixError, load_matrix

            try:
                matrix_summary = load_matrix(root / "configs/search_queries.yaml")
            except (SearchMatrixError, OSError) as exc:
                print(f"SEARCH_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SEARCH_QUERIES_VALID queries={matrix_summary.queries} "
                f"axes={len(matrix_summary.axes)} sources={len(matrix_summary.sources)} "
                f"scopes={','.join(matrix_summary.scopes)} sha256={matrix_summary.sha256}"
            )
            return 0
        if args.search_command == "saturation":
            from biointerfaceos.saturation import SaturationAnalyzer, SaturationError

            try:
                report_path, saturation = SaturationAnalyzer(root).write_report()
            except (OSError, SaturationError) as exc:
                print(f"SEARCH_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SEARCH_SATURATION_VALID raw_hits={saturation['search']['raw_hits']} "
                f"unique_candidates={saturation['search']['unique_candidates']} "
                f"raw_edges={saturation['expansion']['raw_edges']} "
                f"unique_targets={saturation['expansion']['unique_targets']} "
                f"open_gaps={saturation['stopping']['open_gap_count']} "
                f"decision={saturation['stopping']['decision']} "
                f"report={report_path.relative_to(root)} fixture=true"
            )
            return 0
        from biointerfaceos.policy import PolicyConfigError, SourcePolicyEngine

        if args.search_command == "run":
            from biointerfaceos.search_runner import SearchRunError, SearchRunner

            try:
                runner = SearchRunner(root, SourcePolicyEngine.from_yaml(root))
                run_summary = runner.run(args.scope)
            except (OSError, PolicyConfigError, SearchRunError) as exc:
                print(f"SEARCH_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SEARCH_RUN_VALID scope={run_summary.scope} "
                f"query_blocks={run_summary.query_blocks} pages={run_summary.pages} "
                f"raw_hits={run_summary.raw_hits} "
                f"unique_candidates={run_summary.unique_candidates} "
                f"admitted={run_summary.admitted} quarantined={run_summary.quarantined} "
                f"fixture=true run_id={run_summary.run_id}"
            )
            return 0

        from biointerfaceos.expansion import ExpansionError, ExpansionRunner

        try:
            expansion = ExpansionRunner(root, SourcePolicyEngine.from_yaml(root))
            expansion_summary = expansion.run(args.scope, args.depth)
        except (OSError, PolicyConfigError, ExpansionError) as exc:
            print(f"SEARCH_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"SEARCH_EXPANSION_VALID scope={expansion_summary.scope} "
            f"depth={expansion_summary.depth} seed_candidates={expansion_summary.seed_candidates} "
            f"raw_edges={expansion_summary.raw_edges} "
            f"unique_targets={expansion_summary.unique_targets} "
            f"admitted={expansion_summary.admitted} "
            f"quarantined={expansion_summary.quarantined} fixture=true "
            f"run_id={expansion_summary.run_id}"
        )
        return 0
    if args.command == "resolve":
        if args.resolve_command not in {
            "paper-families",
            "materials",
            "proteins",
            "protocols",
            "endpoints",
        }:
            parser.parse_args(["resolve", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("RESOLVE_INVALID: repository root not found", file=sys.stderr)
            return 1
        if args.resolve_command == "materials":
            if not args.fixture:
                print("MATERIAL_RESOLUTION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.material_resolution import (
                MaterialResolutionError,
                MaterialResolver,
            )

            try:
                material_summary = MaterialResolver(root).run()
            except (OSError, MaterialResolutionError) as exc:
                print(f"MATERIAL_RESOLUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"MATERIAL_RESOLUTION_VALID mentions={material_summary.mentions} "
                f"resolved_entities={material_summary.resolved_entities} "
                f"ambiguous_mentions={material_summary.ambiguous_mentions} "
                f"formulations={material_summary.formulations} "
                f"valid_formulations={material_summary.valid_formulations} "
                f"graph_edges={material_summary.graph_edges} "
                f"review_items={material_summary.review_items} fixture=true"
            )
            return 0
        if args.resolve_command == "proteins":
            if not args.fixture:
                print("PROTEIN_RESOLUTION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.protein_resolution import ProteinResolutionError, ProteinResolver

            try:
                protein_summary = ProteinResolver(root).run()
            except (OSError, ProteinResolutionError) as exc:
                print(f"PROTEIN_RESOLUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PROTEIN_RESOLUTION_VALID mentions={protein_summary.mentions} "
                f"resolved={protein_summary.resolved} "
                f"ambiguous={protein_summary.ambiguous} "
                f"obsolete_review={protein_summary.obsolete_review} "
                f"orthology_groups={protein_summary.orthology_groups} "
                f"orthology_edges={protein_summary.orthology_edges} "
                f"review_items={protein_summary.review_items} fixture=true"
            )
            return 0
        if args.resolve_command == "protocols":
            if not args.fixture:
                print("PROTOCOL_RESOLUTION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.protocol_resolution import (
                ProtocolResolutionError,
                ProtocolResolver,
            )

            try:
                resolved_protocol_summary = ProtocolResolver(root).run()
            except (OSError, ProtocolResolutionError) as exc:
                print(f"PROTOCOL_RESOLUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"PROTOCOL_RESOLUTION_VALID protocols={resolved_protocol_summary.protocols} "
                f"fields={resolved_protocol_summary.fields} "
                f"observed_fields={resolved_protocol_summary.observed_fields} "
                f"missing_fields={resolved_protocol_summary.missing_fields} "
                f"clusters={resolved_protocol_summary.clusters} "
                f"review_items={resolved_protocol_summary.review_items} fixture=true"
            )
            return 0
        if args.resolve_command == "endpoints":
            if not args.fixture:
                print("ENDPOINT_RESOLUTION_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.endpoint_resolution import (
                EndpointResolutionError,
                EndpointResolver,
            )

            try:
                endpoint_summary = EndpointResolver(root).run()
            except (OSError, EndpointResolutionError) as exc:
                print(f"ENDPOINT_RESOLUTION_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"ENDPOINT_RESOLUTION_VALID endpoints={endpoint_summary.endpoints} "
                f"normalized={endpoint_summary.normalized} "
                f"families={endpoint_summary.families} "
                f"strata={endpoint_summary.strata} "
                f"harmonized_strata={endpoint_summary.harmonized_strata} "
                f"review_items={endpoint_summary.review_items} fixture=true"
            )
            return 0
        from biointerfaceos.family_resolution import FamilyResolutionError, FamilyResolver

        try:
            family_summary = FamilyResolver(root).run()
        except (OSError, FamilyResolutionError) as exc:
            print(f"FAMILY_RESOLUTION_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"FAMILY_RESOLUTION_VALID families={family_summary.family_count} "
            f"member_rows={family_summary.member_rows} "
            f"manual_review={family_summary.manual_review_rows} "
            f"split_safe={family_summary.split_safe} "
            f"parquet={family_summary.parquet_path.relative_to(root)} "
            f"report={family_summary.report_path.relative_to(root)} fixture=true"
        )
        return 0
    if args.command == "repository":
        if args.repository_command != "sync":
            parser.parse_args(["repository", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("REPOSITORY_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.dry_run:
            print("REPOSITORY_INVALID: --dry-run is required for this command", file=sys.stderr)
            return 2
        from biointerfaceos.sources.repositories import HOSTS as repository_hosts
        from biointerfaceos.sources.repositories import PROVIDERS

        print(
            f"REPOSITORY_SYNC_DRY_RUN providers={len(PROVIDERS)} "
            f"hosts={','.join(repository_hosts)} network=false binary_assets=0"
        )
        return 0
    if args.command == "storage":
        if args.storage_command is None:
            parser.parse_args(["storage", "--help"])
            return 0
        from biointerfaceos.storage import (
            StorageConfig,
            StorageError,
            audit_storage,
            write_json_report,
        )

        root = find_repository_root()
        if root is None:
            print("STORAGE_INVALID: repository root not found", file=sys.stderr)
            return 1
        try:
            report = audit_storage(root, StorageConfig.from_yaml(root))
            write_json_report(report, root / "reports/storage_usage.json")
        except (OSError, StorageError) as exc:
            print(f"STORAGE_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"STORAGE_VALID bytes={report.total_bytes} files={report.total_files} "
            f"budget_bytes={report.budget_bytes} duplicates={len(report.duplicates)}"
        )
        return 1 if args.strict and not report.within_budget else 0
    if args.command == "split":
        if args.split_command == "audit":
            root = find_repository_root()
            if root is None:
                print("SPLIT_AUDIT_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("SPLIT_AUDIT_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.split_audit import SplitAuditError, SplitAuditWorkflow

            try:
                split_audit_result = SplitAuditWorkflow(root).run(strict=args.strict, fixture=True)
            except (SplitAuditError, OSError) as exc:
                print(f"SPLIT_AUDIT_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SPLIT_AUDIT_VALID attacks={split_audit_result.attacks} "
                f"detected={split_audit_result.detected} blocked={split_audit_result.blocked} "
                f"critical_findings={split_audit_result.critical_findings} "
                f"clean_scan={split_audit_result.clean_scan} resumed={split_audit_result.resumed}"
            )
            return 0
        if args.split_command == "freeze-dev":
            root = find_repository_root()
            if root is None:
                print("SPLIT_FREEZE_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("SPLIT_FREEZE_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.split_freeze import SplitFreezeError, SplitFreezeWorkflow

            try:
                freeze_summary = SplitFreezeWorkflow(root).run(fixture=True)
            except (SplitFreezeError, OSError) as exc:
                print(f"SPLIT_FREEZE_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"SPLIT_FREEZE_VALID candidates={freeze_summary.candidates} "
                f"train={freeze_summary.train} validation={freeze_summary.validation} "
                f"excluded={freeze_summary.excluded} groups={freeze_summary.groups} "
                f"blacklisted_features={freeze_summary.blacklisted_features} "
                f"resumed={freeze_summary.resumed} outcome_leakage=false lockbox_accessed=false"
            )
            return 0
        if args.split_command == "detect-duplicates":
            root = find_repository_root()
            if root is None:
                print("DUPLICATES_INVALID: repository root not found", file=sys.stderr)
                return 1
            if not args.fixture:
                print("DUPLICATES_INVALID: --fixture is required", file=sys.stderr)
                return 2
            from biointerfaceos.duplicate_workflow import (
                DuplicateDetectionError,
                DuplicateDetectionWorkflow,
            )

            try:
                duplicate_summary = DuplicateDetectionWorkflow(root).run(fixture=True)
            except (DuplicateDetectionError, OSError) as exc:
                print(f"DUPLICATES_INVALID: {exc}", file=sys.stderr)
                return 1
            print(
                f"DUPLICATES_VALID items={duplicate_summary.items} "
                f"edges={duplicate_summary.edges} clusters={duplicate_summary.clusters} "
                f"exact={duplicate_summary.exact_edges} "
                f"composition={duplicate_summary.composition_edges} "
                f"structure={duplicate_summary.structure_edges} "
                f"text={duplicate_summary.text_edges} "
                f"review_edges={duplicate_summary.review_edges} "
                f"cross_split_duplicates={duplicate_summary.cross_split_duplicates} "
                f"resumed={duplicate_summary.resumed} thresholds_tuned_on_split_labels=false"
            )
            return 0
        if args.split_command != "build-groups":
            parser.parse_args(["split", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("GROUP_KEYS_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("GROUP_KEYS_INVALID: --fixture is required", file=sys.stderr)
            return 2
        from biointerfaceos.group_keys import GroupKeysError, GroupKeysWorkflow

        try:
            group_summary = GroupKeysWorkflow(root).run(fixture=True)
        except (GroupKeysError, OSError) as exc:
            print(f"GROUP_KEYS_INVALID: {exc}", file=sys.stderr)
            return 1
        print(
            f"GROUP_KEYS_VALID rows={group_summary.rows} "
            f"unique_study={group_summary.unique_study} "
            f"unique_paper_families={group_summary.unique_paper_families} "
            f"unique_projects={group_summary.unique_projects} "
            f"collisions={group_summary.collisions} "
            f"review_rows={group_summary.review_rows} "
            f"resumed={group_summary.resumed} "
            "outcome_leakage=false split_freeze=false"
        )
        return 0
    if args.command in FUTURE_COMMANDS:
        return not_implemented(args.command)
    parser.print_help()
    return 0
