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
    "data",
    "extract",
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
        if args.search_command not in {"validate-queries", "run", "expand"}:
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
