"""Tamper-evident append-only JSONL ledgers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class LedgerIntegrityError(ValueError):
    """Raised when ledger bytes do not match their atomic seal."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Mapping[str, Any]) -> bytes:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return serialized.encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class AppendOnlyJSONL:
    """A JSONL file backed by an atomic byte-exact snapshot and seal."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.seal_path = path.with_name(f"{path.name}.seal.json")
        self.snapshot_path = path.with_name(f"{path.name}.snapshot")

    def initialize(self) -> None:
        """Create absent storage, preserving all existing ledger bytes."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(exist_ok=False)
        if self.seal_path.exists() or self.snapshot_path.exists():
            if not (self.seal_path.exists() and self.snapshot_path.exists()):
                raise LedgerIntegrityError("ledger metadata is incomplete")
            self.validate()
            return
        self._seal(self.path.read_bytes())

    def _seal(self, data: bytes) -> None:
        _atomic_write(self.snapshot_path, data)
        seal = {
            "bytes": len(data),
            "sha256": _sha256(data),
            "snapshot_sha256": _sha256(data),
            "version": 1,
        }
        _atomic_write(self.seal_path, _canonical(seal) + b"\n")

    def _read_seal(self) -> Mapping[str, Any]:
        try:
            value = json.loads(self.seal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise LedgerIntegrityError(f"invalid ledger seal: {exc}") from exc
        if not isinstance(value, dict):
            raise LedgerIntegrityError("invalid ledger seal object")
        return value

    def validate(self) -> None:
        """Detect truncation, rewrites, malformed JSON, and broken new-record chains."""
        if not self.path.exists() or not self.seal_path.exists() or not self.snapshot_path.exists():
            raise LedgerIntegrityError("ledger or metadata is missing")
        data = self.path.read_bytes()
        snapshot = self.snapshot_path.read_bytes()
        seal = self._read_seal()
        if seal.get("bytes") != len(data) or seal.get("sha256") != _sha256(data):
            raise LedgerIntegrityError("ledger bytes do not match seal")
        if seal.get("snapshot_sha256") != _sha256(snapshot) or snapshot != data:
            raise LedgerIntegrityError("ledger snapshot does not match seal")
        previous_hash: str | None = None
        expected_sequence = 1
        for number, raw_line in enumerate(data.splitlines(), 1):
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise LedgerIntegrityError(f"invalid JSON on line {number}") from exc
            if not isinstance(record, dict):
                raise LedgerIntegrityError(f"line {number} is not a JSON object")
            metadata = record.get("_ledger")
            if metadata is None:
                previous_hash = _sha256(raw_line)
                continue
            if not isinstance(metadata, dict):
                raise LedgerIntegrityError(f"invalid metadata on line {number}")
            payload = dict(record)
            del payload["_ledger"]
            material = {
                "payload": payload,
                "previous_hash": metadata.get("previous_hash"),
                "sequence": metadata.get("sequence"),
            }
            if metadata.get("sequence") != expected_sequence:
                raise LedgerIntegrityError(f"invalid sequence on line {number}")
            if metadata.get("previous_hash") != previous_hash:
                raise LedgerIntegrityError(f"broken hash chain on line {number}")
            if metadata.get("record_hash") != _sha256(_canonical(material)):
                raise LedgerIntegrityError(f"invalid record hash on line {number}")
            previous_hash = metadata["record_hash"]
            expected_sequence += 1

    def append(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Append one canonical record and atomically advance snapshot and seal."""
        self.initialize()
        self.validate()
        if "_ledger" in record:
            raise ValueError("_ledger is reserved integrity metadata")
        data = self.path.read_bytes()
        lines = data.splitlines()
        sequence = 1
        previous_hash = _sha256(lines[-1]) if lines else None
        if lines:
            last = json.loads(lines[-1])
            if isinstance(last, dict) and isinstance(last.get("_ledger"), dict):
                sequence = int(last["_ledger"]["sequence"]) + 1
                previous_hash = str(last["_ledger"]["record_hash"])
        payload = dict(record)
        material = {"payload": payload, "previous_hash": previous_hash, "sequence": sequence}
        metadata = {
            "sequence": sequence,
            "previous_hash": previous_hash,
            "record_hash": _sha256(_canonical(material)),
        }
        stored = {**payload, "_ledger": metadata}
        separator = b"" if not data or data.endswith(b"\n") else b"\n"
        with self.path.open("ab") as stream:
            stream.write(separator + _canonical(stored) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._seal(self.path.read_bytes())
        return stored

    def recover(self) -> Path:
        """Quarantine corrupt bytes and restore the last sealed snapshot."""
        try:
            self.validate()
        except LedgerIntegrityError:
            pass
        else:
            raise LedgerIntegrityError("recovery refused: ledger is valid")
        if not self.snapshot_path.exists() or not self.seal_path.exists():
            raise LedgerIntegrityError("no sealed snapshot is available")
        snapshot = self.snapshot_path.read_bytes()
        seal = self._read_seal()
        if seal.get("snapshot_sha256") != _sha256(snapshot):
            raise LedgerIntegrityError("sealed snapshot is corrupt")
        quarantine = self.path.with_name(f"{self.path.name}.corrupt.{uuid.uuid4().hex}")
        if self.path.exists():
            shutil.copyfile(self.path, quarantine)
        else:
            _atomic_write(quarantine, b"")
        _atomic_write(self.path, snapshot)
        self.validate()
        return quarantine


def initialize_standard_ledgers(root: Path) -> tuple[AppendOnlyJSONL, ...]:
    """Idempotently initialize decision, blocker, and experiment ledgers."""
    ledgers = tuple(
        AppendOnlyJSONL(root / relative)
        for relative in (
            "reports/decision_ledger.jsonl",
            "reports/blocker_ledger.jsonl",
            "registry/experiment_ledger.jsonl",
        )
    )
    for ledger in ledgers:
        ledger.initialize()
    return ledgers
