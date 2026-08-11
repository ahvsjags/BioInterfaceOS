"""Standard-library command-line interface for the BioInterfaceOS foundation."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from biointerfaceos import __version__

FUTURE_COMMANDS = (
    "split",
    "benchmark",
    "train",
    "agent",
    "claim",
)

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
                "17 top-level directories present"
                if not missing_dirs
                else f"missing: {', '.join(missing_dirs)}",
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
    source_subparsers.add_parser(
        "audit-specialized", help="validate specialized nanodatabase admission decisions"
    )
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
    freeze_parser.add_argument(
        "--fixture", action="store_true", help="freeze the fixture namespace"
    )
    verify_parser = release_subparsers.add_parser("verify", help="verify an immutable release")
    verify_parser.add_argument(
        "--fixture", action="store_true", help="verify the fixture namespace"
    )
    verify_parser.add_argument("--release-id", default=None, help="specific release identifier")
    lockbox_parser = subparsers.add_parser("lockbox", help="test lockbox firewall")
    lockbox_subparsers = lockbox_parser.add_subparsers(dest="lockbox_command")
    lockbox_subparsers.add_parser("self-test", help="run offline firewall and scanner tests")
    ontology_parser = subparsers.add_parser("ontology", help="resolve public ontology mappings")
    ontology_subparsers = ontology_parser.add_subparsers(dest="ontology_command")
    ontology_sync_parser = ontology_subparsers.add_parser(
        "sync", help="plan a bounded ontology metadata sync"
    )
    ontology_sync_parser.add_argument(
        "--dry-run", action="store_true", help="do not contact official endpoints"
    )
    repository_parser = subparsers.add_parser(
        "repository", help="inspect public repository metadata"
    )
    repository_subparsers = repository_parser.add_subparsers(dest="repository_command")
    repository_sync_parser = repository_subparsers.add_parser(
        "sync", help="plan a bounded repository metadata sync"
    )
    repository_sync_parser.add_argument(
        "--dry-run", action="store_true", help="do not contact public providers"
    )
    search_parser = subparsers.add_parser("search", help="validate and run discovery searches")
    search_subparsers = search_parser.add_subparsers(dest="search_command")
    search_subparsers.add_parser(
        "validate-queries", help="validate the versioned query matrix and date firewall"
    )
    search_run_parser = search_subparsers.add_parser(
        "run", help="run a fixture-backed bounded seed search"
    )
    search_run_parser.add_argument(
        "--scope", choices=("development", "validation"), default="development"
    )
    search_expand_parser = search_subparsers.add_parser(
        "expand", help="expand fixture-backed citation and linked-resource edges"
    )
    search_expand_parser.add_argument("--depth", type=int, choices=(1, 2), default=2)
    search_expand_parser.add_argument(
        "--scope", choices=("development", "validation"), default="development"
    )
    search_subparsers.add_parser(
        "saturation", help="compute fixture-backed search saturation and coverage gaps"
    )

    extract_parser = subparsers.add_parser(
        "extract", help="extract structured experiment semantics"
    )
    extract_subparsers = extract_parser.add_subparsers(dest="extract_command")
    extract_tables_parser = extract_subparsers.add_parser(
        "tables", help="map fixture tables to experiment semantics"
    )
    extract_tables_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized local table fixture"
    )
    extract_figures_parser = extract_subparsers.add_parser(
        "figures", help="detect figure panels, axes, legends, and curve candidates"
    )
    extract_figures_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized local figure fixture"
    )
    extract_figures_parser.add_argument(
        "--digitize",
        action="store_true",
        help="also calibrate eligible curve, bar, and scatter candidates",
    )
    extract_experiment_parser = extract_subparsers.add_parser(
        "experiment", help="run deterministic and local/mock experiment extraction"
    )
    extract_experiment_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized dual-path fixture"
    )
    extract_experiment_parser.add_argument(
        "--dual", action="store_true", help="run both deterministic and local/mock paths"
    )

    evidence_parser = subparsers.add_parser(
        "evidence", help="resolve and reverse-trace evidence locators"
    )
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command")
    evidence_trace_parser = evidence_subparsers.add_parser(
        "trace", help="resolve fixture assertions and build a conflict graph"
    )
    evidence_trace_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized evidence fixture"
    )
    evidence_trace_parser.add_argument(
        "--locator", default=None, help="optionally print reverse-trace match count"
    )

    normalize_parser = subparsers.add_parser("normalize", help="normalize units and uncertainty")
    normalize_subparsers = normalize_parser.add_subparsers(dest="normalize_command")
    normalize_units_parser = normalize_subparsers.add_parser(
        "units", help="normalize fixture quantities through the unit registry"
    )
    normalize_units_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized unit fixture"
    )

    data_parser = subparsers.add_parser("data", help="policy-gated data operations")
    data_subparsers = data_parser.add_subparsers(dest="data_command")
    data_fetch_parser = data_subparsers.add_parser(
        "fetch", help="fetch fixture assets through the policy and CAS gates"
    )
    data_fetch_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized local fixture queue"
    )

    resolve_parser = subparsers.add_parser("resolve", help="resolve paper and study identities")
    resolve_subparsers = resolve_parser.add_subparsers(dest="resolve_command")
    resolve_subparsers.add_parser(
        "paper-families", help="resolve fixture-backed paper families and conflicts"
    )
    resolve_materials_parser = resolve_subparsers.add_parser(
        "materials", help="resolve fixture-backed material entities and formulations"
    )
    resolve_materials_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized material fixture"
    )
    resolve_proteins_parser = resolve_subparsers.add_parser(
        "proteins", help="resolve fixture-backed protein identifiers and orthology"
    )
    resolve_proteins_parser.add_argument(
        "--fixture", action="store_true", help="use the sanitized protein fixture"
    )

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
                audit_summary = load_audit(
                    root / "tests/fixtures/nanodatabases/admission_decisions.json"
                )
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
            trace_matches = (
                len(resolver.reverse_trace(args.locator)) if args.locator is not None else 0
            )
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
    if args.command == "data":
        if args.data_command != "fetch":
            parser.parse_args(["data", "--help"])
            return 0
        root = find_repository_root()
        if root is None:
            print("DATA_FETCH_INVALID: repository root not found", file=sys.stderr)
            return 1
        if not args.fixture:
            print("DATA_FETCH_INVALID: --fixture is required", file=sys.stderr)
            return 2
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
            catalog_summary = (
                Catalog(root).build() if args.catalog_command == "build" else Catalog(root).check()
            )
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
        if args.release_command not in {"freeze", "verify"}:
            parser.parse_args(["release", "--help"])
            return 0
        from biointerfaceos.release import ReleaseError, ReleaseManager

        root = find_repository_root()
        if root is None:
            print("RELEASE_INVALID: repository root not found", file=sys.stderr)
            return 1
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
        if args.resolve_command not in {"paper-families", "materials", "proteins"}:
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
    if args.command in FUTURE_COMMANDS:
        return not_implemented(args.command)
    parser.print_help()
    return 0
