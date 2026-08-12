"""Build and verify the R2 public software-replay release without scientific claims."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from biointerfaceos.public_release_audit_workflow import PublicReleaseAuditWorkflow


class R2ReleaseReproductionError(RuntimeError):
    """Raised when an R2 software-release replay is incomplete or unsafe."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise R2ReleaseReproductionError(f"{label} must be an object")
    return value


class R2ReleaseReproductionWorkflow:
    """Create a default-deny, self-reconstructing R2 software replay record."""

    REPRO_ID = "bioif-r2-software-replay-v1.1.0"
    REPRODUCED_AT = "2026-08-12T00:00:00+00:00"
    OUTPUT_RELATIVE = "reports/review_round_2/reproducibility/r2_software_replay/v1.1.0"
    REQUIRED_PUBLIC_PATHS = {
        "LICENSE",
        "NOTICE",
        "CITATION.cff",
        "docs/figures/R2_FIGURE_SPECS.json",
        "docs/figures/R2_PROTOCOL_FIGURE_DATA.json",
        "docs/figures/R2_LEGACY_WITHDRAWAL_LEDGER_SOURCE.json",
        "containers/r2-software-replay.Dockerfile",
        "containers/r2-software-replay-run.sh",
        "src/biointerfaceos/submission_figure_qa_workflow.py",
        "src/biointerfaceos/r2_release_reproduction_workflow.py",
    }
    FORBIDDEN_PUBLIC_PREFIXES = ("data/", "registry/", "reports/", "release/")
    REQUIRED_OUTPUTS = (
        "source_manifest.json",
        "sbom.json",
        "release_manifest.json",
        "r2_public_source.tar.gz",
        "clean_replay.json",
        "junit.xml",
        "generation_receipt.json",
    )
    CONTAINER_NETWORK_REQUIREMENT = "docker build --network=none; docker run --network=none"

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    def _public_inventory(self) -> list[dict[str, Any]]:
        """Reuse the R2 default-deny registry without emitting a second audit receipt."""
        audit = PublicReleaseAuditWorkflow(self.root)
        _, entries = audit._load_registry()
        inventory, findings = audit._inventory(entries)
        findings.extend(audit._readme_findings())
        if findings:
            raise R2ReleaseReproductionError(
                "public-release boundary is not auditable: " + "; ".join(sorted(findings))
            )
        public = [row for row in inventory if row["redistribution"] == "PUBLIC"]
        paths = {str(row["path"]) for row in public}
        missing = self.REQUIRED_PUBLIC_PATHS - paths
        if missing:
            raise R2ReleaseReproductionError(
                "required R2 public source is not registered: " + ", ".join(sorted(missing))
            )
        unsafe = [
            str(row["path"])
            for row in public
            if str(row["path"]).startswith(self.FORBIDDEN_PUBLIC_PREFIXES)
        ]
        if unsafe:
            raise R2ReleaseReproductionError(
                "fixture, data, registry, report, or legacy release entered R2 source scope: "
                + ", ".join(sorted(unsafe))
            )
        return public

    @staticmethod
    def _copy_public_source(root: Path, inventory: list[dict[str, Any]], destination: Path) -> None:
        for row in inventory:
            relative = Path(str(row["path"]))
            source = root / relative
            if not source.is_file():
                raise R2ReleaseReproductionError(f"public source disappeared: {relative}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def _source_manifest(self, inventory: list[dict[str, Any]]) -> dict[str, Any]:
        sources = [
            {
                "path": str(row["path"]),
                "sha256": str(row["sha256"]),
                "license_expression": str(row["license_expression"]),
                "asset_id": str(row["asset_id"]),
                "evidence_status": str(row["evidence_status"]),
            }
            for row in inventory
        ]
        return {
            "schema_version": 1,
            "repro_id": self.REPRO_ID,
            "scope": "R2_PUBLIC_SOFTWARE_REPLAY_SOURCE",
            "files": sources,
            "excluded_prefixes": list(self.FORBIDDEN_PUBLIC_PREFIXES),
            "software_replay": True,
            "scientific_reproduction": False,
            "scientific_submission_ready": False,
        }

    def _sbom(self, source_manifest_path: Path) -> dict[str, Any]:
        pyproject_path = self.root / "pyproject.toml"
        lock_path = self.root / "uv.lock"
        try:
            pyproject = _mapping(
                tomllib.loads(pyproject_path.read_text(encoding="utf-8")), "pyproject"
            )
            lock = _mapping(tomllib.loads(lock_path.read_text(encoding="utf-8")), "uv lock")
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise R2ReleaseReproductionError("cannot read pinned Python environment") from exc
        project = _mapping(pyproject.get("project"), "project metadata")
        packages = lock.get("package")
        if not isinstance(packages, list):
            raise R2ReleaseReproductionError("uv lock does not contain packages")
        components: list[dict[str, str]] = []
        for item in packages:
            row = _mapping(item, "uv package")
            name = row.get("name")
            version = row.get("version")
            if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
                raise R2ReleaseReproductionError("uv package name or version is invalid")
            components.append(
                {
                    "name": name,
                    "version": version,
                    "source": "uv.lock",
                    "license_expression": "NOASSERTION",
                }
            )
        components.sort(key=lambda item: (item["name"], item["version"]))
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "serialNumber": f"urn:uuid:{self.REPRO_ID}",
            "version": 1,
            "metadata": {
                "component": {
                    "name": str(project.get("name")),
                    "version": str(project.get("version")),
                    "type": "application",
                },
                "python_requires": str(project.get("requires-python")),
                "pyproject_sha256": _sha256(pyproject_path),
                "uv_lock_sha256": _sha256(lock_path),
                "source_manifest_sha256": _sha256(source_manifest_path),
            },
            "components": components,
            "scope": "software dependency inventory; not a data or scientific-evidence inventory",
        }

    @staticmethod
    def _tar_info(name: str, size: int) -> tarfile.TarInfo:
        info = tarfile.TarInfo(name)
        info.size = size
        info.uid = 0
        info.gid = 0
        info.uname = "root"
        info.gname = "root"
        info.mtime = 0
        info.mode = 0o644
        return info

    def _write_source_archive(self, source_root: Path, manifest_path: Path) -> Path:
        archive = self.output_root / "r2_public_source.tar.gz"
        with (
            archive.open("wb") as raw,
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
            tarfile.open(fileobj=compressed, mode="w") as tar,
        ):
            for path in sorted(item for item in source_root.rglob("*") if item.is_file()):
                relative = path.relative_to(source_root).as_posix()
                with path.open("rb") as stream:
                    tar.addfile(self._tar_info(f"source/{relative}", path.stat().st_size), stream)
            payload = manifest_path.read_bytes()
            tar.addfile(self._tar_info("source_manifest.json", len(payload)), io.BytesIO(payload))
        return archive

    def _clean_replay(self, inventory: list[dict[str, Any]]) -> dict[str, Any]:
        """Run the public CLI in a temporary source-only worktree."""
        with tempfile.TemporaryDirectory(prefix="bioif-r2-public-") as temporary:
            source_root = Path(temporary) / "source"
            self._copy_public_source(self.root, inventory, source_root)
            environment = os.environ.copy()
            environment["BIOINTERFACEOS_NETWORK_DISABLED"] = "1"
            environment["PYTHONPATH"] = (
                str(source_root / "src") + os.pathsep + environment.get("PYTHONPATH", "")
            )
            command = [sys.executable, "-m", "biointerfaceos", "reproduce", "release", "--strict"]
            try:
                completed = subprocess.run(
                    command,
                    cwd=source_root,
                    env=environment,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise R2ReleaseReproductionError("clean public-source replay failed") from exc
            nested_receipt_path = source_root / self.OUTPUT_RELATIVE / "generation_receipt.json"
            try:
                nested_receipt = _mapping(
                    json.loads(nested_receipt_path.read_text(encoding="utf-8")),
                    "clean replay receipt",
                )
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise R2ReleaseReproductionError(
                    "clean replay did not write a valid receipt"
                ) from exc
            if (
                nested_receipt.get("status") != "PASS_R2_SOFTWARE_REPLAY"
                or nested_receipt.get("software_replay") is not True
                or nested_receipt.get("scientific_reproduction") is not False
                or nested_receipt.get("scientific_submission_ready") is not False
            ):
                raise R2ReleaseReproductionError("clean replay crossed its evidence boundary")
            return {
                "command": "python -m biointerfaceos reproduce release --strict",
                "python_executable": sys.executable,
                "source_mode": "temporary_public_source_only",
                "network_policy": (
                    "BIOINTERFACEOS_NETWORK_DISABLED=1; container command requires --network=none"
                ),
                "return_code": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
                "nested_receipt_sha256": _sha256(nested_receipt_path),
                "nested_status": nested_receipt["status"],
                "rebuilt_protocol_figures": 3,
                "software_replay": True,
                "scientific_reproduction": False,
            }

    @staticmethod
    def _junit(clean_replay: Mapping[str, Any]) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<testsuite name="biointerfaceos.r2_software_replay" tests="1" '
            'failures="0" errors="0">\n'
            '  <testcase classname="biointerfaceos.reproducibility" '
            'name="public_source_clean_replay">\n'
            "    <system-out>"
            + str(clean_replay["command"])
            + " | "
            + str(clean_replay["nested_status"])
            + "</system-out>\n"
            "  </testcase>\n"
            "</testsuite>\n"
        )

    @staticmethod
    def _make_read_only(directory: Path) -> None:
        for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        directory.chmod(0o555)

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise R2ReleaseReproductionError("T118 requires --strict")
        if self.output_root.exists():
            raise R2ReleaseReproductionError(
                "R2 software replay already executed; overwrite refused"
            )
        inventory = self._public_inventory()
        self.output_root.mkdir(parents=True, exist_ok=False)
        source_manifest_path = self.output_root / "source_manifest.json"
        self._write(source_manifest_path, self._source_manifest(inventory))
        sbom_path = self.output_root / "sbom.json"
        self._write(sbom_path, self._sbom(source_manifest_path))
        source_root = self.output_root / "source_bundle"
        self._copy_public_source(self.root, inventory, source_root)
        archive_path = self._write_source_archive(source_root, source_manifest_path)
        clean_replay = self._clean_replay(inventory)
        clean_replay_path = self.output_root / "clean_replay.json"
        self._write(clean_replay_path, clean_replay)
        junit_path = self.output_root / "junit.xml"
        junit_path.write_text(self._junit(clean_replay), encoding="utf-8")
        release_manifest_path = self.output_root / "release_manifest.json"
        release_manifest = {
            "schema_version": 1,
            "repro_id": self.REPRO_ID,
            "reproduced_at": self.REPRODUCED_AT,
            "source_asset_count": len(inventory),
            "source_manifest_sha256": _sha256(source_manifest_path),
            "sbom_sha256": _sha256(sbom_path),
            "archive_sha256": _sha256(archive_path),
            "container_recipe": "containers/r2-software-replay.Dockerfile",
            "container_run_script": "containers/r2-software-replay-run.sh",
            "container_network_requirement": self.CONTAINER_NETWORK_REQUIREMENT,
            "software_replay": True,
            "scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        self._write(release_manifest_path, release_manifest)
        output_hashes = {
            path.name: _sha256(path)
            for path in (
                source_manifest_path,
                sbom_path,
                release_manifest_path,
                archive_path,
                clean_replay_path,
                junit_path,
            )
        }
        receipt = {
            "schema_version": 1,
            "repro_id": self.REPRO_ID,
            "status": "PASS_R2_SOFTWARE_REPLAY",
            "reproduced_at": self.REPRODUCED_AT,
            "source_asset_count": len(inventory),
            "rebuilt_protocol_figures": 3,
            "software_replay": True,
            "scientific_reproduction": False,
            "scientific_submission_ready": False,
            "network_isolation": "container recipe requires Docker --network=none",
            "output_hashes": output_hashes,
        }
        self._write(self.output_root / "generation_receipt.json", receipt)
        self._make_read_only(self.output_root)
        return receipt

    def verify(self) -> dict[str, Any]:
        required = {name: self.output_root / name for name in self.REQUIRED_OUTPUTS}
        if not all(path.is_file() for path in required.values()):
            raise R2ReleaseReproductionError("R2 software replay outputs are missing")
        try:
            receipt = _mapping(
                json.loads(required["generation_receipt.json"].read_text(encoding="utf-8")),
                "R2 generation receipt",
            )
            source_manifest = _mapping(
                json.loads(required["source_manifest.json"].read_text(encoding="utf-8")),
                "R2 source manifest",
            )
            release_manifest = _mapping(
                json.loads(required["release_manifest.json"].read_text(encoding="utf-8")),
                "R2 release manifest",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R2ReleaseReproductionError("R2 software replay metadata is invalid") from exc
        if (
            receipt.get("repro_id") != self.REPRO_ID
            or receipt.get("status") != "PASS_R2_SOFTWARE_REPLAY"
            or receipt.get("software_replay") is not True
            or receipt.get("scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
            or source_manifest.get("scope") != "R2_PUBLIC_SOFTWARE_REPLAY_SOURCE"
            or release_manifest.get("container_network_requirement")
            != self.CONTAINER_NETWORK_REQUIREMENT
        ):
            raise R2ReleaseReproductionError("R2 software replay evidence boundary is invalid")
        files = source_manifest.get("files")
        if not isinstance(files, list) or not files:
            raise R2ReleaseReproductionError("R2 source manifest has no public files")
        for row in files:
            entry = _mapping(row, "R2 source file")
            path = entry.get("path")
            if not isinstance(path, str) or path.startswith(self.FORBIDDEN_PUBLIC_PREFIXES):
                raise R2ReleaseReproductionError("forbidden path entered R2 source manifest")
        hashes = _mapping(receipt.get("output_hashes"), "R2 replay output hashes")
        for name, expected in hashes.items():
            path = self.output_root / str(name)
            if not isinstance(expected, str) or not path.is_file() or _sha256(path) != expected:
                raise R2ReleaseReproductionError(f"R2 software replay output hash differs: {name}")
        if not all(
            not bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            for path in self.output_root.rglob("*")
        ):
            raise R2ReleaseReproductionError("R2 software replay output is writable")
        return receipt
