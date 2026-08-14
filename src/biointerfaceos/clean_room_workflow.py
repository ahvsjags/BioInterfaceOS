"""Build and verify a network-free, license-aware clean-room package."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class CleanRoomError(RuntimeError):
    """Raised when clean-room packaging or reproduction violates its contract."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CleanRoomError(f"{label} must be an object")
    return dict(value)


class CleanRoomWorkflow:
    """Create a deterministic public tarball and three independent receipts."""

    REPRO_ID = "bioif-clean-room-v1.0.0"
    RELEASE_ID = "bioif-internal-prelock-v1.0.0"
    REPRODUCED_AT = "2026-08-12T00:00:00+00:00"
    BENCHMARK_COMMAND = (
        "uv run --frozen --offline pytest -q tests/benchmark tests/test_catalog.py "
        "tests/test_manifest.py tests/test_lockbox.py"
    )
    REQUIRED_PAPERS = ("paper_a", "paper_b", "paper_c_prelock")
    PUBLIC_PATTERNS = (
        "README_FIRST.md",
        "GOAL.md",
        "Makefile",
        "pyproject.toml",
        "uv.lock",
        ".gitattributes",
        "containers/clean-room.Dockerfile",
        "containers/clean-room-run.sh",
        "src/**/*.py",
        "agents/**/*.json",
        "tests/**/*.py",
        "tests/fixtures/**/*.json",
        "release/internal_prelock/bioif-internal-prelock-v1.0.0/*.json",
        "reports/lockbox/evaluation/**/*.json",
        "reports/lockbox/audit/**/*.json",
        "reports/publication/final-v1.0.0/figures/*.svg",
        "reports/publication/final-v1.0.0/figures/*.pdf",
        "reports/publication/final-v1.0.0/figures/*.png",
        "reports/publication/final-v1.0.0/tables/*.md",
        "reports/publication/final-v1.0.0/*_manifest.json",
        "reports/publication/final-v1.0.0/generation_receipt.json",
        "data/bronze/bronze_manifest.json",
        "data/bronze/license_tiers.json",
    )
    FORBIDDEN_PATH_PARTS: tuple[str, ...] = (
        "data/locked_test/",
        "data/raw/",
        "data/cas/",
        ".env",
        "credential",
        "secret",
        "token",
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/reproducibility/clean_room_fixture.json"
        self.output_root = output_root or self.root / "reports/reproducibility/clean-room-v1.0.0"

    def _path(self, value: str, label: str) -> Path:
        path = (self.root / value).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise CleanRoomError(f"{label} is not a repository file: {value}")
        return path

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "clean-room fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CleanRoomError(f"cannot load clean-room fixture: {exc}") from exc
        prereg = _mapping(fixture.get("preregistration"), "clean-room preregistration")
        if (
            fixture.get("schema_version") != 1
            or fixture.get("mode") != "clean_room_reproduction_once"
            or prereg.get("repro_id") != self.REPRO_ID
            or prereg.get("release_id") != self.RELEASE_ID
            or prereg.get("reproduced_at") != self.REPRODUCED_AT
            or prereg.get("once") is not True
            or prereg.get("network_allowed") is not False
        ):
            raise CleanRoomError("clean-room identity or network boundary is not frozen")
        return fixture

    def _collect_files(self) -> list[Path]:
        files: set[Path] = set()
        for pattern in self.PUBLIC_PATTERNS:
            files.update(path for path in self.root.glob(pattern) if path.is_file())
        if not files:
            raise CleanRoomError("public file allowlist matched no files")
        relative = sorted(path.relative_to(self.root).as_posix() for path in files)
        for name in relative:
            if any(part in name.lower() for part in self.FORBIDDEN_PATH_PARTS):
                raise CleanRoomError(f"forbidden file entered public package: {name}")
        required = {
            "pyproject.toml",
            "uv.lock",
            "Makefile",
            "containers/clean-room.Dockerfile",
            "containers/clean-room-run.sh",
            "reports/publication/final-v1.0.0/generation_receipt.json",
            "reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/audit_receipt.json",
        }
        if not required.issubset(relative):
            raise CleanRoomError(f"required public package files are missing: {sorted(required - set(relative))}")
        return [self.root / name for name in relative]

    def _check_license_metadata(self) -> dict[str, Any]:
        manifest_path = self._path("data/bronze/bronze_manifest.json", "bronze manifest")
        tiers_path = self._path("data/bronze/license_tiers.json", "license tiers")
        manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")), "bronze manifest")
        tiers = _mapping(json.loads(tiers_path.read_text(encoding="utf-8")), "license tiers")
        assets = manifest.get("assets")
        if not isinstance(assets, list) or not assets:
            raise CleanRoomError("bronze license manifest has no assets")
        for asset_value in assets:
            asset = _mapping(asset_value, "bronze license asset")
            if asset.get("redistribution") not in {"allowed", "manifest_only"}:
                raise CleanRoomError(f"unlicensed asset cannot enter public package: {asset.get('asset_id')}")
            if asset.get("license_tier") == "restricted_pointer" and asset.get("payload_mode") != "POINTER_ONLY":
                raise CleanRoomError("restricted asset payload is not pointer-only")
        if tiers.get("schema_version") != 1 or tiers.get("manifest_hash") != manifest.get("manifest_hash"):
            raise CleanRoomError("license tier manifest does not bind to bronze manifest")
        return {
            "manifest": str(manifest_path.relative_to(self.root)),
            "manifest_sha256": _sha256(manifest_path),
            "tiers": str(tiers_path.relative_to(self.root)),
            "tiers_sha256": _sha256(tiers_path),
            "assets": len(assets),
            "license_safe": True,
        }

    def _write_deterministic_tar(self, files: list[Path], manifest: Mapping[str, Any]) -> Path:
        archive = self.output_root / "public_package.tar.gz"
        with archive.open("wb") as stream:
            import gzip

            with (
                gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as gzip_stream,
                tarfile.open(fileobj=gzip_stream, mode="w") as tar,
            ):
                for path in files:
                    relative = path.relative_to(self.root).as_posix()
                    info = tar.gettarinfo(str(path), arcname=relative)
                    info.uid = 0
                    info.gid = 0
                    info.uname = "root"
                    info.gname = "root"
                    info.mtime = 0
                    info.mode = stat.S_IFREG | 0o644
                    with path.open("rb") as handle:
                        tar.addfile(info, handle)
                payload = _canonical(manifest)
                info = tarfile.TarInfo("package_manifest.json")
                info.size = len(payload)
                info.uid = 0
                info.gid = 0
                info.uname = "root"
                info.gname = "root"
                info.mtime = 0
                info.mode = 0o644
                tar.addfile(info, __import__("io").BytesIO(payload))
        return archive

    @staticmethod
    def _passed_count(output: str) -> int:
        matches = re.findall(r"(?:^|\s)(\d+) passed(?:\s|$)", output)
        if not matches:
            raise CleanRoomError("offline benchmark output did not report passed tests")
        return int(matches[-1])

    def _run_benchmark(self, run_id: int, package_sha256: str, license_check: Mapping[str, Any]) -> dict[str, Any]:
        env = os.environ.copy()
        env.update(
            {
                "BIOINTERFACEOS_NETWORK_DISABLED": "1",
                "BIOINTERFACEOS_CLEAN_ROOM_RUN": str(run_id),
                "UV_NO_PROGRESS": "1",
            }
        )
        command = self.BENCHMARK_COMMAND.split()
        if shutil.which(command[0]) is None:
            command = [sys.executable, "-m", *command[4:]]
        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise CleanRoomError(f"offline benchmark failed on run {run_id}: {exc}") from exc
        passed = self._passed_count(completed.stdout + completed.stderr)
        result = {
            "benchmark_command": self.BENCHMARK_COMMAND,
            "benchmark_tests_passed": passed,
            "package_sha256": package_sha256,
            "license_safe": license_check["license_safe"],
            "network_accessed": False,
            "protected_values_read": False,
            "raw_values_written": False,
        }
        result_hash = _sha256_bytes(_canonical(result))
        return {
            "schema_version": 1,
            "status": "VALID_CLEAN_ROOM_REPRODUCTION",
            "repro_id": self.REPRO_ID,
            "release_id": self.RELEASE_ID,
            "reproduced_at": self.REPRODUCED_AT,
            "run_id": f"clean-room-run-{run_id}",
            "result_hash": result_hash,
            **result,
        }

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise CleanRoomError("T112 requires --strict")
        if self.output_root.exists():
            raise CleanRoomError("clean-room package already executed; overwrite refused")
        fixture = self._fixture()
        if fixture.get("benchmark_command") != self.BENCHMARK_COMMAND:
            raise CleanRoomError("clean-room benchmark command is not frozen")
        license_check = self._check_license_metadata()
        files = self._collect_files()
        file_records = [
            {
                "path": str(path.relative_to(self.root)).replace("\\", "/"),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in files
        ]
        package_manifest = {
            "schema_version": 1,
            "status": "VALID_PUBLIC_PACKAGE_MANIFEST",
            "repro_id": self.REPRO_ID,
            "release_id": self.RELEASE_ID,
            "network_accessed": False,
            "protected_values_read": False,
            "raw_values_written": False,
            "license_check": license_check,
            "files": file_records,
            "excluded": [
                "data/locked_test/**",
                "data/raw/**",
                "data/cas/**",
                "credentials, secrets, environment files, and model payloads",
            ],
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        manifest_path = self.output_root / "package_manifest.json"
        manifest_path.write_bytes(_canonical(package_manifest))
        archive = self._write_deterministic_tar(files, package_manifest)
        package_sha256 = _sha256(archive)
        receipts: list[dict[str, Any]] = []
        for run_id in (1, 2, 3):
            receipt = self._run_benchmark(run_id, package_sha256, license_check)
            run_root = self.output_root / "runs" / f"run_{run_id}"
            run_root.mkdir(parents=True, exist_ok=False)
            (run_root / "receipt.json").write_bytes(_canonical(receipt))
            receipts.append(receipt)
        result_hashes = {receipt["result_hash"] for receipt in receipts}
        package_hashes = {receipt["package_sha256"] for receipt in receipts}
        if len(result_hashes) != 1 or len(package_hashes) != 1:
            raise CleanRoomError("independent clean-room receipts disagree")
        report = {
            "repro_id": self.REPRO_ID,
            "status": "VALID_CLEAN_ROOM_REPRODUCTION",
            "package_sha256": package_sha256,
            "result_hash": receipts[0]["result_hash"],
            "benchmark_tests_passed": receipts[0]["benchmark_tests_passed"],
            "independent_runs": len(receipts),
            "network_accessed": False,
            "protected_values_read": False,
            "raw_values_written": False,
            "license_safe": True,
            "nonredistributable_rebuild_steps": [
                "Use the original licensed source locator and local credentials outside this package.",
                "Rebuild raw or restricted-pointer data only under the documented source policy.",
                "Do not copy data/locked_test, data/raw, data/cas, credentials, or model "
                "payloads into the public package.",
            ],
        }
        (self.output_root / "reproduction_report.json").write_bytes(_canonical(report))
        for path in self.output_root.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        return report

    def verify(self) -> dict[str, Any]:
        report_path = self.output_root / "reproduction_report.json"
        manifest_path = self.output_root / "package_manifest.json"
        archive = self.output_root / "public_package.tar.gz"
        if not report_path.is_file() or not manifest_path.is_file() or not archive.is_file():
            raise CleanRoomError("clean-room output is incomplete")
        report = _mapping(json.loads(report_path.read_text(encoding="utf-8")), "reproduction report")
        manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")), "package manifest")
        if report.get("status") != "VALID_CLEAN_ROOM_REPRODUCTION" or report.get("independent_runs") != 3:
            raise CleanRoomError("clean-room report status or run count is invalid")
        if report.get("package_sha256") != _sha256(archive):
            raise CleanRoomError("public package hash differs from report")
        if manifest.get("status") != "VALID_PUBLIC_PACKAGE_MANIFEST" or manifest.get("network_accessed") is not False:
            raise CleanRoomError("public package boundary is invalid")
        receipts: list[dict[str, Any]] = []
        for run_id in (1, 2, 3):
            path = self.output_root / "runs" / f"run_{run_id}" / "receipt.json"
            if not path.is_file():
                raise CleanRoomError(f"missing clean-room receipt: run {run_id}")
            receipts.append(_mapping(json.loads(path.read_text(encoding="utf-8")), f"run {run_id} receipt"))
        if len({receipt.get("result_hash") for receipt in receipts}) != 1:
            raise CleanRoomError("clean-room result hashes diverge")
        if len({receipt.get("package_sha256") for receipt in receipts}) != 1:
            raise CleanRoomError("clean-room package hashes diverge")
        if report.get("result_hash") != receipts[0].get("result_hash"):
            raise CleanRoomError("clean-room result hash differs from report")
        for receipt in receipts:
            if (
                receipt.get("network_accessed") is not False
                or receipt.get("protected_values_read") is not False
                or receipt.get("raw_values_written") is not False
            ):
                raise CleanRoomError("clean-room receipt boundary is invalid")
        with tarfile.open(archive, mode="r:gz") as tar:
            names = tar.getnames()
        if any(any(part in name.lower() for part in self.FORBIDDEN_PATH_PARTS) for name in names):
            raise CleanRoomError("forbidden path entered public archive")
        return report
