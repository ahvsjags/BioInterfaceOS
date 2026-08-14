"""Policy-gated fixture asset downloader with CAS promotion and quarantine."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.assets import AssetStore, AssetStoreError
from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.lockbox import LockboxAccessError, LockboxFirewall
from biointerfaceos.manifest import ManifestRegistry, SourceRecord
from biointerfaceos.policy import (
    RejectionRegistry,
    SourceCandidate,
    SourcePolicyEngine,
)


class DownloadError(RuntimeError):
    """Raised when a fixture download queue is invalid or unsafe."""


@dataclass(frozen=True)
class DownloadSummary:
    """Counts from one idempotent fixture download run."""

    promoted: int
    quarantined: int
    policy_skipped: int
    resumed: int
    receipts: int
    bytes: int


class AssetDownloader:
    """Download only policy-admitted fixture assets into the CAS."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        *,
        queue_path: Path | None = None,
        receipt_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.policy = policy
        self.queue_path = queue_path or (self.root / "tests/fixtures/downloads/download_queue.json")
        self.receipt_path = receipt_path or self.root / "reports/download_receipts.jsonl"
        self.firewall = LockboxFirewall(self.root)
        self.manifest = ManifestRegistry(self.root)
        self.store = AssetStore(self.root)
        self.rejection = RejectionRegistry(self.root)

    @staticmethod
    def _content_type(data: bytes) -> str:
        stripped = data.lstrip()
        if stripped.startswith((b"{", b"[")):
            try:
                json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            else:
                return "application/json"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "application/octet-stream"
        if all(char in "\t\n\r" or ord(char) >= 32 for char in text):
            return "text/plain"
        return "application/octet-stream"

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _fixture_path(self, value: Any) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise DownloadError("fixture_path is required for an admitted item")
        candidate = (self.root / value).resolve(strict=False)
        if candidate != self.root and self.root not in candidate.parents:
            raise DownloadError("fixture path escapes repository")
        if "locked_test" in candidate.parts or "lockbox" in candidate.parts:
            raise DownloadError("fixture path enters lockbox namespace")
        return self.firewall.assert_development_read_allowed(candidate)

    @staticmethod
    def _load_queue(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DownloadError(f"cannot load download queue: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "items"}:
            raise DownloadError("download queue envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["items"], list):
            raise DownloadError("download queue schema is invalid")
        items: list[dict[str, Any]] = []
        required = {
            "queue_id",
            "candidate",
            "fixture_path",
            "expected_sha256",
            "expected_size_bytes",
            "expected_content_type",
            "max_size_bytes",
            "locked_test_accessed",
        }
        seen: set[str] = set()
        for raw in value["items"]:
            if not isinstance(raw, Mapping) or set(raw) != required:
                raise DownloadError("download queue item fields are invalid")
            item = dict(raw)
            queue_id = item["queue_id"]
            if not isinstance(queue_id, str) or not queue_id or queue_id in seen:
                raise DownloadError("download queue IDs must be unique non-empty strings")
            seen.add(queue_id)
            if not isinstance(item["candidate"], Mapping):
                raise DownloadError(f"candidate is invalid for {queue_id}")
            if item["locked_test_accessed"] is not False:
                raise DownloadError(f"locked-test flag is not clean for {queue_id}")
            if not isinstance(item["max_size_bytes"], int) or item["max_size_bytes"] <= 0:
                raise DownloadError(f"max_size_bytes is invalid for {queue_id}")
            items.append(item)
        return items

    @staticmethod
    def _candidate(value: Mapping[str, Any]) -> SourceCandidate:
        try:
            return SourceCandidate.from_mapping(value)
        except (TypeError, ValueError) as exc:
            raise DownloadError(f"queue candidate is invalid: {exc}") from exc

    @staticmethod
    def _existing_receipts(ledger: AppendOnlyJSONL) -> dict[str, dict[str, Any]]:
        if not ledger.path.exists():
            return {}
        records: dict[str, dict[str, Any]] = {}
        for line in ledger.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DownloadError("download receipt ledger contains invalid JSON") from exc
            if not isinstance(value, Mapping) or not isinstance(value.get("queue_id"), str):
                raise DownloadError("download receipt is missing queue_id")
            records[str(value["queue_id"])] = dict(value)
        return records

    def _manifest_record(self, candidate: SourceCandidate, item: Mapping[str, Any]) -> SourceRecord:
        expected_sha = item["expected_sha256"]
        expected_size = item["expected_size_bytes"]
        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise DownloadError(f"expected_sha256 is invalid for {item['queue_id']}")
        if not isinstance(expected_size, int) or expected_size < 0:
            raise DownloadError(f"expected_size_bytes is invalid for {item['queue_id']}")
        return SourceRecord.create(
            source_id=candidate.source_id,
            source_name=candidate.source_name,
            url=candidate.url,
            access="admitted",
            status="admitted",
            accession=candidate.accession,
            retrieved_at="2026-08-12T00:00:00+00:00",
            sha256=expected_sha,
            size_bytes=expected_size,
            license=candidate.license_identifier,
            redistribution="allowed",
            download_status="pending",
        )

    def _register_manifest(self, record: SourceRecord) -> None:
        existing = {item.asset_id: item for item in self.manifest.records()}
        current = existing.get(record.asset_id)
        if current is not None:
            if current.sha256 != record.sha256 or current.source_id != record.source_id:
                raise DownloadError(f"manifest identity conflict: {record.source_id}")
            if current.status != "admitted":
                raise DownloadError(f"manifest record is not admitted: {record.source_id}")
            return
        self.manifest.register(record)

    def _quarantine_manifest(self, record: SourceRecord, reason: str) -> None:
        quarantined = SourceRecord.create(
            source_id=record.source_id,
            source_name=record.source_name,
            url=record.url,
            access="admitted",
            status="quarantined",
            accession=record.accession,
            retrieved_at=record.retrieved_at,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            license=record.license,
            redistribution="manifest_only",
            download_status="quarantined",
            rejection_reason=reason,
        )
        current = [item for item in self.manifest.records() if item.asset_id != quarantined.asset_id]
        current.append(quarantined)
        self.manifest.write(current)

    def _quarantine_bytes(self, data: bytes, queue_id: str, digest: str, reason: str) -> Path:
        target_dir = self.root / "data/quarantine"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{queue_id}.{reason}.{digest}.part"
        if target.exists():
            return target
        descriptor, name = tempfile.mkstemp(prefix=f".{queue_id}.", suffix=".part", dir=target_dir)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def _receipt(
        self,
        item: Mapping[str, Any],
        candidate: SourceCandidate,
        decision: str,
        code: str | None,
        status: str,
        *,
        actual_sha256: str | None = None,
        actual_content_type: str | None = None,
        size_bytes: int | None = None,
        asset_id: str | None = None,
        quarantine_path: str | None = None,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "queue_id": item["queue_id"],
            "source_id": candidate.source_id,
            "url": candidate.url,
            "decision": decision,
            "rejection_code": code,
            "status": status,
            "expected_sha256": item["expected_sha256"],
            "actual_sha256": actual_sha256,
            "expected_content_type": item["expected_content_type"],
            "actual_content_type": actual_content_type,
            "expected_size_bytes": item["expected_size_bytes"],
            "size_bytes": size_bytes,
            "asset_id": asset_id,
            "quarantine_path": quarantine_path,
            "reason": reason,
            "locked_test_accessed": False,
            "fixture": True,
        }

    def run(self) -> DownloadSummary:
        """Process each queue item once, preserving receipts and resumable outcomes."""
        items = self._load_queue(self.queue_path)
        ledger = AppendOnlyJSONL(self.receipt_path)
        ledger.initialize()
        existing = self._existing_receipts(ledger)
        promoted = quarantined = policy_skipped = resumed = total_bytes = 0
        for item in items:
            queue_id = str(item["queue_id"])
            prior = existing.get(queue_id)
            if prior is not None and prior.get("status") in {
                "PROMOTED",
                "QUARANTINED",
                "POLICY_SKIPPED",
            }:
                resumed += 1
                if prior.get("status") == "PROMOTED":
                    total_bytes += int(prior.get("size_bytes") or 0)
                continue
            candidate = self._candidate(item["candidate"])
            decision = self.policy.evaluate(candidate)
            if decision.decision != "ADMIT_PUBLIC_REDISTRIBUTABLE":
                if decision.decision in {"REJECT", "QUARANTINE"}:
                    self.rejection.register(candidate, decision)
                status = "POLICY_SKIPPED"
                policy_skipped += 1
                ledger.append(
                    self._receipt(
                        item,
                        candidate,
                        decision.decision,
                        decision.rejection_code,
                        status,
                        reason=decision.reason,
                    )
                )
                continue
            try:
                fixture_path = self._fixture_path(item["fixture_path"])
                max_size = int(item["max_size_bytes"])
                if fixture_path.stat().st_size > max_size:
                    raise DownloadError("fixture exceeds maximum size")
                data = fixture_path.read_bytes()
                if len(data) > max_size:
                    raise DownloadError("payload exceeds maximum size")
                actual_sha = self._sha256(data)
                actual_type = self._content_type(data)
                record = self._manifest_record(candidate, item)
                self._register_manifest(record)
                expected_type = item["expected_content_type"]
                if actual_type != expected_type:
                    reason = f"content_type_mismatch:{actual_type}"
                    path = self._quarantine_bytes(data, queue_id, actual_sha, "content-type")
                    self._quarantine_manifest(record, reason)
                    status = "QUARANTINED"
                    quarantined += 1
                    ledger.append(
                        self._receipt(
                            item,
                            candidate,
                            decision.decision,
                            decision.rejection_code,
                            status,
                            actual_sha256=actual_sha,
                            actual_content_type=actual_type,
                            size_bytes=len(data),
                            asset_id=record.asset_id,
                            quarantine_path=path.relative_to(self.root).as_posix(),
                            reason=reason,
                        )
                    )
                    continue
                if actual_sha != item["expected_sha256"]:
                    reason = f"sha256_mismatch:{actual_sha}"
                    path = self._quarantine_bytes(data, queue_id, actual_sha, "hash")
                    self._quarantine_manifest(record, reason)
                    status = "QUARANTINED"
                    quarantined += 1
                    ledger.append(
                        self._receipt(
                            item,
                            candidate,
                            decision.decision,
                            decision.rejection_code,
                            status,
                            actual_sha256=actual_sha,
                            actual_content_type=actual_type,
                            size_bytes=len(data),
                            asset_id=record.asset_id,
                            quarantine_path=path.relative_to(self.root).as_posix(),
                            reason=reason,
                        )
                    )
                    continue
                reference = self.store.put_bytes(data, record)
                promoted += 1
                total_bytes += reference.size_bytes
                ledger.append(
                    self._receipt(
                        item,
                        candidate,
                        decision.decision,
                        decision.rejection_code,
                        "PROMOTED",
                        actual_sha256=actual_sha,
                        actual_content_type=actual_type,
                        size_bytes=reference.size_bytes,
                        asset_id=reference.asset_id,
                        reason="verified and promoted to CAS",
                    )
                )
            except (AssetStoreError, DownloadError, LockboxAccessError, OSError) as exc:
                quarantined += 1
                ledger.append(
                    self._receipt(
                        item,
                        candidate,
                        decision.decision,
                        decision.rejection_code,
                        "QUARANTINED",
                        reason=str(exc),
                    )
                )
        return DownloadSummary(
            promoted=promoted,
            quarantined=quarantined,
            policy_skipped=policy_skipped,
            resumed=resumed,
            receipts=len(existing) + promoted + quarantined + policy_skipped,
            bytes=total_bytes,
        )
