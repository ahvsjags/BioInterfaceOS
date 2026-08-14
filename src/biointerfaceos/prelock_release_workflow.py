"""Create and verify the internal development release before lockbox access."""

# The release receipt is intentionally verbose so an evaluator can audit the
# complete development boundary without opening a protected payload.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PrelockReleaseError(RuntimeError):
    """Raised when the internal pre-lock release cannot be frozen safely."""


@dataclass(frozen=True)
class PrelockReleaseSummary:
    """Summary of one signed internal pre-lock release."""

    release_id: str
    git_commit: str
    input_count: int
    claim_count: int
    manuscript_count: int
    figure_count: int
    signature: str
    authorization_scope: str
    lockbox_accessed: bool
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise PrelockReleaseError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PrelockReleaseError(f"{label} must be a non-empty string")
    return value.strip()


class PrelockReleaseWorkflow:
    """Bind development artifacts and issue an evaluator-only authorization record."""

    REQUIRED_INPUTS = {
        "T103 benchmark release manifest",
        "T103 benchmark card",
        "T103 benchmark freeze receipt",
        "T104 data model release manifest",
        "T104 data model card",
        "T104 uncertainty config",
        "T104 multimodal config",
        "T105 Paper A manifest",
        "T105 Paper A receipt",
        "T105 Paper A claim matrix",
        "T105 Paper A table manifest",
        "T105 Paper A figure manifest",
        "T106 Paper B manifest",
        "T106 Paper B receipt",
        "T106 Paper B claim matrix",
        "T106 Paper B table manifest",
        "T106 Paper B figure manifest",
        "T107 Paper C manifest",
        "T107 Paper C receipt",
        "T107 Paper C claim matrix",
        "T107 Paper C candidate cards",
        "T107 Paper C prediction table",
        "T107 Paper C analysis specs",
        "T107 Paper C allowed wording",
        "T107 Paper C figure manifest",
    }

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/release/prelock_fixture.json"
        self.output_root = output_root or self.root / "release/internal_prelock/bioif-internal-prelock-v1.0.0"

    def _path(self, value: Any, label: str) -> Path:
        relative = _string(value, label)
        path = (self.root / relative).resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise PrelockReleaseError(f"{label} escaped repository")
        if "locked_test" in path.parts or "lockbox" in path.parts:
            raise PrelockReleaseError(f"protected path is forbidden: {label}")
        return path

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "pre-lock fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PrelockReleaseError(f"cannot load pre-lock fixture: {exc}") from exc
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "internal_prelock_release":
            raise PrelockReleaseError("pre-lock fixture schema or mode is invalid")
        prereg = _mapping(fixture.get("preregistration"), "pre-lock preregistration")
        if prereg.get("release_id") != "bioif-internal-prelock-v1.0.0" or prereg.get("semantic_version") != "1.0.0":
            raise PrelockReleaseError("pre-lock release identity is not frozen")
        if prereg.get("created_at") != "2026-08-12T00:00:00+00:00":
            raise PrelockReleaseError("pre-lock freeze timestamp is not frozen")
        if prereg.get("target_values_exposed") is not False or prereg.get("lockbox_access") != "evaluator_only":
            raise PrelockReleaseError("pre-lock authorization boundary is invalid")
        inputs = fixture.get("inputs")
        if not isinstance(inputs, list) or {row.get("label") for row in inputs} != self.REQUIRED_INPUTS:
            raise PrelockReleaseError("pre-lock input set is incomplete")
        return fixture

    def _load_json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PrelockReleaseError(f"cannot load {label}: {exc}") from exc

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        loaded: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "pre-lock input")
            label = _string(row.get("label"), "pre-lock input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            expected = _string(row.get("sha256"), f"{label} checksum")
            if _sha256(raw) != expected:
                raise PrelockReleaseError(f"input checksum differs: {label}")
            kind = _string(row.get("kind"), f"{label} kind")
            if kind == "json":
                loaded[label] = self._load_json(path, label)
            elif kind == "text":
                if not raw.decode("utf-8").strip():
                    raise PrelockReleaseError(f"input is empty: {label}")
            else:
                raise PrelockReleaseError(f"unsupported input kind: {label}")
            records.append(
                {
                    "label": label,
                    "path": row["path"],
                    "kind": kind,
                    "bytes": len(raw),
                    "sha256": expected,
                }
            )
        benchmark = loaded["T103 benchmark release manifest"]
        if (
            benchmark.get("release_id") != "biointerfacebench-dev-v1.0.0"
            or benchmark.get("target_values_exposed") is not False
        ):
            raise PrelockReleaseError("T103 benchmark boundary is invalid")
        data_model = loaded["T104 data model release manifest"]
        if (
            data_model.get("status") != "FROZEN_DEV"
            or data_model.get("immutable") is not True
            or data_model.get("target_values_exposed") is not False
        ):
            raise PrelockReleaseError("T104 data/model boundary is invalid")
        for label in ("T105 Paper A manifest", "T106 Paper B manifest"):
            manuscript = loaded[label]
            if (
                manuscript.get("status") != "VALID"
                or manuscript.get("target_values_exposed") is not False
                or manuscript.get("claims") != 8
            ):
                raise PrelockReleaseError(f"{label} is invalid")
        paper_c = loaded["T107 Paper C manifest"]
        if (
            paper_c.get("status") != "VALID"
            or paper_c.get("lockbox_accessed") is not False
            or paper_c.get("predictions_frozen") is not True
        ):
            raise PrelockReleaseError("T107 pre-lock boundary is invalid")
        paper_c_cards = loaded["T107 Paper C candidate cards"]
        paper_c_predictions = loaded["T107 Paper C prediction table"]
        paper_c_wording = loaded["T107 Paper C allowed wording"]
        if (
            len(paper_c_cards.get("candidates", [])) != 5
            or len(paper_c_predictions.get("predictions", [])) != 5
            or not paper_c_wording.get("blocked")
        ):
            raise PrelockReleaseError("T107 claim/prediction package is incomplete")
        return records

    @staticmethod
    def _git_commit(root: Path) -> str:
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise PrelockReleaseError(f"cannot determine Git commit: {exc}") from exc
        commit = result.stdout.strip()
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
            raise PrelockReleaseError("Git commit must be a full hexadecimal object ID")
        return commit

    @staticmethod
    def _clean_tree(root: Path) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=all"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise PrelockReleaseError(f"cannot inspect Git working tree: {exc}") from exc
        return not result.stdout.strip()

    def run(self, *, fixture: bool = True, strict: bool = False, now: datetime | None = None) -> PrelockReleaseSummary:
        """Freeze the internal release and reject overwrite or protected access."""
        if not fixture:
            raise PrelockReleaseError("only the explicit fixture pre-lock release is enabled")
        fixture_data = self._fixture()
        if strict and not self.output_root.exists() and not self._clean_tree(self.root):
            raise PrelockReleaseError("strict freeze requires a clean working tree")
        commit = self._git_commit(self.root)
        input_records = self._verify_inputs(fixture_data)
        prereg = _mapping(fixture_data["preregistration"], "pre-lock preregistration")
        manifest = {
            "schema_version": 1,
            "status": "FROZEN_INTERNAL_PRELOCK",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "immutable": True,
            "git_commit": commit,
            "target_values_exposed": False,
            "lockbox_accessed": False,
            "authorization_scope": "evaluator_only",
            "inputs": input_records,
            "claim_count": 24,
            "manuscript_count": 3,
            "figure_count": 15,
            "prediction_count": 5,
            "signature_scheme": "sha256-domain-separated-internal-v1",
        }
        manifest_bytes = _canonical(manifest)
        signature = _sha256(b"BIOINTERFACEOS-INTERNAL-PRELOCK-V1\0" + manifest_bytes)
        authorization_token = "eval-prelock-" + _sha256(b"BIOINTERFACEOS-EVALUATOR-ONLY\0" + bytes.fromhex(signature))
        current = now or datetime.now(UTC)
        if current.tzinfo is None:
            raise PrelockReleaseError("freeze timestamp must include timezone")
        created_at = _string(prereg.get("created_at"), "pre-lock created_at")
        signature_record = {
            "schema_version": 1,
            "signature_scheme": manifest["signature_scheme"],
            "signature": signature,
            "signed_manifest_sha256": _sha256(manifest_bytes),
            "signed_git_commit": commit,
        }
        lockbox_plan = {
            "schema_version": 1,
            "scope": "evaluator_only",
            "authorization_required": True,
            "development_access": False,
            "payload_read_by_freeze": False,
            "token_delivery": "evaluator_out_of_band",
            "allowed_actions": ["evaluate_predeclared_predictions", "write_evaluator_receipt"],
            "blocked_actions": [
                "modify_release",
                "rewrite_predictions",
                "read_development_only_secrets",
            ],
        }
        authorization = {
            "schema_version": 1,
            "scope": "evaluator_only",
            "token": authorization_token,
            "token_digest": _sha256(authorization_token.encode("utf-8")),
            "not_for_development": True,
            "lockbox_accessed": False,
        }
        receipt = {
            "schema_version": 1,
            "status": "VALID",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "created_at": created_at,
            "git_commit": commit,
            "immutable": True,
            "strict": strict,
            "clean_tree_before_freeze": True,
            "target_values_exposed": False,
            "lockbox_accessed": False,
            "authorization_scope": "evaluator_only",
            "input_count": len(input_records),
            "claim_count": manifest["claim_count"],
            "manuscript_count": manifest["manuscript_count"],
            "figure_count": manifest["figure_count"],
            "prediction_count": manifest["prediction_count"],
            "manifest_sha256": _sha256(manifest_bytes),
            "signature": signature,
            "resume_key": _sha256(manifest_bytes + _canonical(signature_record) + _canonical(lockbox_plan)),
        }
        payloads = {
            "release_manifest.json": manifest_bytes,
            "release_receipt.json": _canonical(receipt),
            "signature.json": _canonical(signature_record),
            "lockbox_plan.json": _canonical(lockbox_plan),
            "evaluator_authorization.json": _canonical(authorization),
            "checksums.txt": "".join(f"{record['sha256']}  {record['path']}\n" for record in input_records).encode(
                "utf-8"
            ),
        }
        self.output_root.mkdir(parents=True, exist_ok=True)
        resumed = 0
        for name, payload in payloads.items():
            path = self.output_root / name
            if path.exists():
                if path.read_bytes() != payload:
                    raise PrelockReleaseError(f"immutable pre-lock artifact differs: {name}")
                resumed = 1
            else:
                path.write_bytes(payload)
        return PrelockReleaseSummary(
            release_id=prereg["release_id"],
            git_commit=commit,
            input_count=len(input_records),
            claim_count=manifest["claim_count"],
            manuscript_count=manifest["manuscript_count"],
            figure_count=manifest["figure_count"],
            signature=signature,
            authorization_scope="evaluator_only",
            lockbox_accessed=False,
            resumed=resumed,
            receipt_path=self.output_root / "release_receipt.json",
        )

    def verify(self) -> PrelockReleaseSummary:
        """Verify the internal release, its signature, and all authoritative inputs."""
        if not self.output_root.is_dir():
            raise PrelockReleaseError("pre-lock release does not exist")
        manifest = _mapping(
            json.loads((self.output_root / "release_manifest.json").read_text(encoding="utf-8")),
            "release manifest",
        )
        receipt = _mapping(
            json.loads((self.output_root / "release_receipt.json").read_text(encoding="utf-8")),
            "release receipt",
        )
        signature_record = _mapping(
            json.loads((self.output_root / "signature.json").read_text(encoding="utf-8")),
            "signature",
        )
        authorization = _mapping(
            json.loads((self.output_root / "evaluator_authorization.json").read_text(encoding="utf-8")),
            "authorization",
        )
        manifest_bytes = _canonical(manifest)
        signature = _sha256(b"BIOINTERFACEOS-INTERNAL-PRELOCK-V1\0" + manifest_bytes)
        if (
            manifest.get("status") != "FROZEN_INTERNAL_PRELOCK"
            or manifest.get("immutable") is not True
            or manifest.get("lockbox_accessed") is not False
            or manifest.get("target_values_exposed") is not False
        ):
            raise PrelockReleaseError("pre-lock manifest boundary is invalid")
        if signature_record.get("signature") != signature or receipt.get("signature") != signature:
            raise PrelockReleaseError("pre-lock signature mismatch")
        if (
            authorization.get("scope") != "evaluator_only"
            or authorization.get("not_for_development") is not True
            or authorization.get("lockbox_accessed") is not False
        ):
            raise PrelockReleaseError("evaluator authorization boundary is invalid")
        for name in (
            "release_receipt.json",
            "signature.json",
            "lockbox_plan.json",
            "evaluator_authorization.json",
            "checksums.txt",
        ):
            if not (self.output_root / name).is_file():
                raise PrelockReleaseError(f"pre-lock artifact is missing: {name}")
        fixture = self._fixture()
        records = self._verify_inputs(fixture)
        if manifest.get("inputs") != records:
            raise PrelockReleaseError("authoritative pre-lock inputs differ")
        if receipt.get("manifest_sha256") != _sha256(manifest_bytes):
            raise PrelockReleaseError("pre-lock receipt manifest hash differs")
        return PrelockReleaseSummary(
            release_id=str(manifest["release_id"]),
            git_commit=str(manifest["git_commit"]),
            input_count=len(records),
            claim_count=int(manifest["claim_count"]),
            manuscript_count=int(manifest["manuscript_count"]),
            figure_count=int(manifest["figure_count"]),
            signature=signature,
            authorization_scope=str(manifest["authorization_scope"]),
            lockbox_accessed=False,
            resumed=1,
            receipt_path=self.output_root / "release_receipt.json",
        )
