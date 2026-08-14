"""Deterministic blinded consensus and expert-review packet export."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.gold_auto import GoldAutoBuilder, GoldAutoError

REVIEW_ROOT = Path("reports/review_packets")
REVIEW_FIXTURE = Path("tests/fixtures/review/review_expectations.json")


class ReviewPacketError(RuntimeError):
    """Raised when review packet inputs or outputs violate their contract."""


@dataclass(frozen=True)
class ReviewSummary:
    """Counts and output paths from one review packet export."""

    packets: int
    strata: int
    unsigned_packets: int
    signed_packets: int
    packets_path: Path
    guide_path: Path
    signoff_path: Path
    coverage_path: Path
    receipt_path: Path


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReviewPacketError(f"invalid review JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReviewPacketError(f"review JSON must be an object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ReviewPacketError(f"review ledger is missing: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ReviewPacketError(f"review ledger row is not an object: {path}")
        rows.append(value)
    return rows


class ReviewPacketBuilder:
    """Export stratified, unsigned packets without promoting expert labels."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / REVIEW_FIXTURE
        self.output_root = output_root or self.root / REVIEW_ROOT

    def _load_fixture(self) -> tuple[str, int, int]:
        try:
            value = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReviewPacketError(f"cannot load review fixture: {exc}") from exc
        if not isinstance(value, dict) or set(value) != {
            "schema_version",
            "sample_strategy",
            "expected_packets",
            "expected_strata",
        }:
            raise ReviewPacketError("review fixture envelope is invalid")
        if (
            value["schema_version"] != 1
            or value["sample_strategy"] != "stratified"
            or not isinstance(value["expected_packets"], int)
            or not isinstance(value["expected_strata"], int)
        ):
            raise ReviewPacketError("review fixture schema is invalid")
        return (
            str(value["sample_strategy"]),
            int(value["expected_packets"]),
            int(value["expected_strata"]),
        )

    @staticmethod
    def _candidate_fields(
        candidates: dict[str, Any],
    ) -> dict[tuple[str, str], list[dict[str, Any]]]:
        output: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for record in candidates["records"]:
            for path_name in ("rule_path", "mock_path"):
                path = record[path_name]
                for field in path["fields"]:
                    key = (str(field["record_id"]), str(field["field_name"]))
                    output.setdefault(key, []).append(
                        {
                            "candidate_id": f"{path_name}:{field['field_name']}",
                            "label": "RULE_PATH" if path_name == "rule_path" else "MOCK_PATH",
                            "value": field["value"],
                            "unit": field["unit"],
                            "confidence": field["confidence"],
                            "evidence_locators": field["evidence_locators"],
                        }
                    )
        return output

    @staticmethod
    def _packet(
        *,
        packet_id: str,
        stratum: str,
        reason: str,
        record_id: str,
        field_name: str,
        question: str,
        candidates: list[dict[str, Any]],
        evidence_locators: list[str],
    ) -> dict[str, Any]:
        locators = sorted(set(evidence_locators))
        if not locators or any(not locator.startswith("asset:") for locator in locators):
            raise ReviewPacketError(f"packet lacks valid evidence locators: {packet_id}")
        return {
            "packet_id": packet_id,
            "stratum": stratum,
            "reason_code": reason,
            "blinded_context": {
                "source_label": "BLINDED_SOURCE",
                "record_label": f"BLINDED_RECORD_{record_id}",
                "field_label": f"BLINDED_FIELD_{field_name}",
            },
            "question": question,
            "record_id": record_id,
            "field_name": field_name,
            "candidate_values": candidates,
            "evidence_locators": locators,
            "annotation_status": "UNSIGNED",
            "signoff": {
                "reviewer_id": None,
                "decision": None,
                "rationale": None,
                "signed_at": None,
                "signature": None,
            },
            "expert_gold_promotion": False,
        }

    def _prepare(self, sample: str) -> dict[str, Any]:
        strategy, expected_packets, expected_strata = self._load_fixture()
        if sample != strategy:
            raise ReviewPacketError(f"unsupported review sampling strategy: {sample}")
        try:
            GoldAutoBuilder(self.root).validate()
        except (GoldAutoError, OSError) as exc:
            raise ReviewPacketError(f"Gold-auto prerequisite is invalid: {exc}") from exc
        exclusions = _read_json(self.root / "data/gold_auto/gold_auto_exclusions.json")
        candidates = _read_json(self.root / "registry/experiment_candidates.json")
        evidence = _read_json(self.root / "registry/evidence_table.json")
        _read_jsonl(self.root / "registry/consensus_review_queue.jsonl")
        evidence_reviews = _read_jsonl(self.root / "registry/evidence_review_queue.jsonl")
        candidate_fields = self._candidate_fields(candidates)
        consensus_exclusions = {
            (str(item["record_id"]), str(item["field_name"])): item
            for item in exclusions["rows"]
            if "CONSENSUS_DISAGREEMENT_OR_REVIEW" in item["reasons"]
            or "NO_RESOLVED_EVIDENCE_ASSERTION" in item["reasons"]
        }
        packets: list[dict[str, Any]] = []
        for key, item in sorted(consensus_exclusions.items()):
            record_id, field_name = key
            candidate_values = candidate_fields.get(key, [])
            if not candidate_values:
                candidate_values = [
                    {
                        "candidate_id": "CONSENSUS",
                        "label": "CONSENSUS_VALUE",
                        "value": None,
                        "unit": None,
                        "confidence": item["confidence"],
                        "evidence_locators": item["evidence_locators"],
                    }
                ]
            if "CONSENSUS_DISAGREEMENT_OR_REVIEW" in item["reasons"]:
                packets.append(
                    self._packet(
                        packet_id=f"review:consensus:{record_id}:{field_name}",
                        stratum="CONSENSUS_DISAGREEMENT",
                        reason="DUAL_PATH_FIELD_DISAGREEMENT",
                        record_id=record_id,
                        field_name=field_name,
                        question=("Which candidate value is supported, or should this field remain unresolved?"),
                        candidates=candidate_values,
                        evidence_locators=item["evidence_locators"],
                    )
                )
            else:
                packets.append(
                    self._packet(
                        packet_id=f"review:evidence:{record_id}:{field_name}",
                        stratum="MISSING_EVIDENCE",
                        reason="NO_RESOLVED_EVIDENCE_ASSERTION",
                        record_id=record_id,
                        field_name=field_name,
                        question=("Can a resolved evidence assertion be linked to this candidate field?"),
                        candidates=candidate_values,
                        evidence_locators=item["evidence_locators"],
                    )
                )
        evidence_by_id = {str(row["assertion_id"]): row for row in evidence["rows"]}
        for review in evidence_reviews:
            assertion_id = str(review["assertion_id"])
            row = evidence_by_id.get(assertion_id)
            if row is None:
                raise ReviewPacketError(f"evidence review assertion is missing: {assertion_id}")
            packets.append(
                self._packet(
                    packet_id=f"review:locator:{assertion_id}",
                    stratum="BROKEN_LOCATOR",
                    reason="BROKEN_OR_MISSING_EVIDENCE_LOCATOR",
                    record_id=str(row["record_id"]),
                    field_name=str(row["field_name"]),
                    question=(
                        "Can this locator be repaired from an allowed source, or should "
                        "the assertion remain quarantined?"
                    ),
                    candidates=[
                        {
                            "candidate_id": assertion_id,
                            "label": "QUARANTINED_ASSERTION",
                            "value": row["value"],
                            "unit": row["unit"],
                            "confidence": row["confidence"],
                            "evidence_locators": [row["locator"]],
                        }
                    ],
                    evidence_locators=[row["locator"]],
                )
            )
        packets.sort(key=lambda packet: packet["packet_id"])
        actual_strata = len({p["stratum"] for p in packets})
        if len(packets) != expected_packets or actual_strata != expected_strata:
            raise ReviewPacketError(f"review expectations differ: packets={len(packets)} strata={actual_strata}")
        if any(packet["annotation_status"] != "UNSIGNED" for packet in packets):
            raise ReviewPacketError("review export contains signed packets")
        required_fields = [
            "reviewer_id",
            "decision",
            "rationale",
            "signed_at",
            "signature",
        ]
        guide = {
            "schema_version": 1,
            "allowed_decisions": [
                "ACCEPT_RULE",
                "ACCEPT_MOCK",
                "ENTER_REVISED_VALUE",
                "UNRESOLVED",
                "NOT_APPLICABLE",
            ],
            "required_fields": required_fields,
            "blinding": ("Source and record labels are blinded; exact evidence locators remain visible for audit."),
        }
        signoff = {
            "schema_version": 1,
            "status": "UNSIGNED_IMPORT_REQUIRED",
            "expert_gold_promotion": "FORBIDDEN_UNTIL_SIGNED_IMPORT",
            "required": ["packet_id", *required_fields],
        }
        coverage = {
            "schema_version": 1,
            "sample_strategy": strategy,
            "strata": sorted({packet["stratum"] for packet in packets}),
            "packet_count": len(packets),
            "unsigned_packets": len(packets),
            "signed_packets": 0,
            "expert_gold_promoted": 0,
            "locked_test_accessed": False,
            "real_network_accessed": False,
        }
        return {
            "packets": packets,
            "guide": guide,
            "signoff": signoff,
            "coverage": coverage,
        }

    def export(self, *, sample: str = "stratified") -> ReviewSummary:
        """Export deterministic unsigned review packets."""
        payload = self._prepare(sample)
        self.output_root.mkdir(parents=True, exist_ok=True)
        files = {
            "packets.json": {"schema_version": 1, "packets": payload["packets"]},
            "annotation_guide.json": payload["guide"],
            "signoff_schema.json": payload["signoff"],
            "coverage_report.json": payload["coverage"],
        }
        serialized = {name: _canonical(value) for name, value in files.items()}
        export_hash = _sha256_bytes(_canonical({name: _sha256_bytes(value) for name, value in serialized.items()}))
        receipt = {
            "schema_version": 1,
            "sample_strategy": sample,
            "export_hash": export_hash,
            "packet_count": len(payload["packets"]),
            "unsigned_packets": len(payload["packets"]),
            "signed_packets": 0,
            "expert_gold_promoted": 0,
            "locked_test_accessed": False,
        }
        serialized["review_export_receipt.json"] = _canonical(receipt)
        for name, content in serialized.items():
            (self.output_root / name).write_bytes(content)
        return self._summary(payload, serialized)

    def _summary(self, payload: dict[str, Any], serialized: dict[str, bytes]) -> ReviewSummary:
        return ReviewSummary(
            packets=len(payload["packets"]),
            strata=len(payload["coverage"]["strata"]),
            unsigned_packets=int(payload["coverage"]["unsigned_packets"]),
            signed_packets=int(payload["coverage"]["signed_packets"]),
            packets_path=self.output_root / "packets.json",
            guide_path=self.output_root / "annotation_guide.json",
            signoff_path=self.output_root / "signoff_schema.json",
            coverage_path=self.output_root / "coverage_report.json",
            receipt_path=self.output_root / "review_export_receipt.json",
        )

    def validate(self, *, sample: str = "stratified") -> ReviewSummary:
        """Validate packet schema, deterministic bytes, strata, and unsigned status."""
        payload = self._prepare(sample)
        required = (
            "packets.json",
            "annotation_guide.json",
            "signoff_schema.json",
            "coverage_report.json",
            "review_export_receipt.json",
        )
        if any(not (self.output_root / name).is_file() for name in required):
            raise ReviewPacketError("review export is incomplete")
        packets = _read_json(self.output_root / "packets.json")
        if packets.get("packets") != payload["packets"]:
            raise ReviewPacketError("review packets differ from deterministic export")
        coverage = _read_json(self.output_root / "coverage_report.json")
        if coverage != payload["coverage"]:
            raise ReviewPacketError("review coverage differs from deterministic export")
        if coverage["signed_packets"] != 0 or coverage["expert_gold_promoted"] != 0:
            raise ReviewPacketError("signed or expert-gold rows appeared in export")
        return self._summary(payload, {})
