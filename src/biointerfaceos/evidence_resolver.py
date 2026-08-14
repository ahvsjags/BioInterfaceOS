"""Evidence resolution and reverse tracing for experiment assertions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class EvidenceResolutionError(ValueError):
    """Raised when evidence assertions or source locators are invalid."""


@dataclass(frozen=True)
class EvidenceRow:
    """One forward-resolved or quarantined evidence assertion."""

    assertion_id: str
    record_id: str
    field_name: str
    value: Any
    unit: str | None
    path: str
    locator: str
    resolution_status: str
    source_asset_id: str | None
    confidence: float


@dataclass(frozen=True)
class EvidenceTraceSummary:
    """Counts and output paths from one evidence trace run."""

    assertions: int
    resolved: int
    quarantined: int
    conflict_nodes: int
    conflict_edges: int
    review_items: int
    evidence_path: Path
    conflict_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _walk_locators(value: Any, output: set[str]) -> None:
    if isinstance(value, str) and value.startswith("asset:"):
        output.add(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            _walk_locators(item, output)
    elif isinstance(value, list):
        for item in value:
            _walk_locators(item, output)


class EvidenceResolver:
    """Resolve fixture assertions against extracted evidence artifacts."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        evidence_path: Path | None = None,
        conflict_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/evidence/trace_cases.json")
        self.evidence_path = evidence_path or self.root / "registry/evidence_table.json"
        self.conflict_path = conflict_path or (self.root / "registry/evidence_conflict_graph.json")
        self.review_path = review_path or (self.root / "registry/evidence_review_queue.jsonl")
        self.report_path = report_path or self.root / "reports/evidence_trace.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EvidenceResolutionError(f"cannot load evidence fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "assertions"}:
            raise EvidenceResolutionError("evidence fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["assertions"], list):
            raise EvidenceResolutionError("evidence fixture schema is invalid")
        assertions: list[dict[str, Any]] = []
        required = {
            "assertion_id",
            "record_id",
            "field_name",
            "value",
            "unit",
            "path",
            "locator",
            "confidence",
        }
        for raw in value["assertions"]:
            if not isinstance(raw, Mapping) or set(raw) != required:
                raise EvidenceResolutionError("evidence assertion fields are invalid")
            assertions.append(dict(raw))
        return assertions

    def _known_locators(self) -> set[str]:
        known: set[str] = set()
        for relative in (
            "registry/experiment_table_semantics.json",
            "registry/digitized_figure_points.json",
        ):
            path = self.root / relative
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise EvidenceResolutionError(f"cannot load evidence artifact: {relative}") from exc
            _walk_locators(payload, known)
        if not known:
            raise EvidenceResolutionError("no exact source locators are available")
        return known

    @staticmethod
    def _row(raw: Mapping[str, Any], known: set[str]) -> EvidenceRow:
        assertion_id = _text(raw["assertion_id"])
        record_id = _text(raw["record_id"])
        field_name = _text(raw["field_name"])
        path = _text(raw["path"])
        locator = _text(raw["locator"])
        unit = None if raw["unit"] is None else _text(raw["unit"])
        if not assertion_id or not record_id or not field_name or not path:
            raise EvidenceResolutionError("assertion identifiers and path are required")
        if not locator.startswith("asset:"):
            raise EvidenceResolutionError(f"invalid locator for {assertion_id}")
        try:
            confidence = float(raw["confidence"])
        except (TypeError, ValueError) as exc:
            raise EvidenceResolutionError(f"invalid confidence for {assertion_id}") from exc
        if not 0.0 <= confidence <= 1.0:
            raise EvidenceResolutionError(f"confidence out of range for {assertion_id}")
        resolved = locator in known
        source_asset_id = locator.split("/", 1)[0].removeprefix("asset:") if resolved else None
        return EvidenceRow(
            assertion_id=assertion_id,
            record_id=record_id,
            field_name=field_name,
            value=raw["value"],
            unit=unit,
            path=path,
            locator=locator,
            resolution_status="RESOLVED" if resolved else "QUARANTINED",
            source_asset_id=source_asset_id,
            confidence=confidence,
        )

    @staticmethod
    def _conflicts(rows: list[EvidenceRow]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        resolved = [row for row in rows if row.resolution_status == "RESOLVED"]
        nodes = [asdict(row) for row in resolved]
        edges: list[dict[str, Any]] = []
        for index, left in enumerate(resolved):
            for right in resolved[index + 1 :]:
                if (
                    left.record_id == right.record_id
                    and left.field_name == right.field_name
                    and (left.value != right.value or left.unit != right.unit)
                ):
                    edges.append(
                        {
                            "edge_id": f"conflict:{left.assertion_id}:{right.assertion_id}",
                            "kind": "VALUE_CONFLICT",
                            "record_id": left.record_id,
                            "field_name": left.field_name,
                            "from_assertion": left.assertion_id,
                            "to_assertion": right.assertion_id,
                        }
                    )
        return nodes, edges

    def reverse_trace(self, locator: str) -> list[dict[str, Any]]:
        """Return all forward rows that resolve to one exact locator."""
        if not self.evidence_path.is_file():
            self.run()
        try:
            payload = json.loads(self.evidence_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise EvidenceResolutionError("evidence table is unreadable") from exc
        rows = payload.get("rows")
        if not isinstance(rows, list):
            raise EvidenceResolutionError("evidence table rows are invalid")
        return [dict(row) for row in rows if isinstance(row, Mapping) and row.get("locator") == locator]

    def run(self) -> EvidenceTraceSummary:
        """Resolve assertions, build conflict graph, and write review evidence."""
        assertions = self._load_fixture(self.fixture_path)
        known = self._known_locators()
        rows = [self._row(assertion, known) for assertion in assertions]
        review_items = [
            {
                "review_id": f"broken-locator:{row.assertion_id}",
                "reason": "BROKEN_OR_MISSING_EVIDENCE_LOCATOR",
                "assertion_id": row.assertion_id,
                "record_id": row.record_id,
                "field_name": row.field_name,
                "locator": row.locator,
                "resolution": "QUARANTINED",
            }
            for row in rows
            if row.resolution_status == "QUARANTINED"
        ]
        nodes, edges = self._conflicts(rows)
        evidence_payload = {
            "schema_version": 1,
            "fixture": True,
            "known_locator_count": len(known),
            "rows": [asdict(row) for row in rows],
            "summary": {
                "assertions": len(rows),
                "resolved": sum(row.resolution_status == "RESOLVED" for row in rows),
                "quarantined": sum(row.resolution_status == "QUARANTINED" for row in rows),
            },
        }
        conflict_node_ids = {
            node["assertion_id"]
            for node in nodes
            if any(
                edge["from_assertion"] == node["assertion_id"] or edge["to_assertion"] == node["assertion_id"]
                for edge in edges
            )
        }
        conflict_node_count = len(conflict_node_ids)
        conflict_payload = {
            "schema_version": 1,
            "fixture": True,
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "conflict_nodes": conflict_node_count,
                "conflict_edges": len(edges),
            },
        }
        self.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_path.write_text(
            json.dumps(evidence_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.conflict_path.parent.mkdir(parents=True, exist_ok=True)
        self.conflict_path.write_text(
            json.dumps(conflict_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        review_ledger = AppendOnlyJSONL(self.review_path)
        review_ledger.initialize()
        existing = {
            json.loads(line).get("review_id")
            for line in review_ledger.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for review in review_items:
            if review["review_id"] not in existing:
                review_ledger.append(review)

        report = (
            "\n".join(
                [
                    "# Evidence Resolver and Reverse Trace Report",
                    "",
                    "Forward evidence resolution and reverse tracing are fixture-backed and locator exact.",
                    "",
                    f"- assertions: {len(rows)}",
                    f"- resolved: {sum(row.resolution_status == 'RESOLVED' for row in rows)}",
                    f"- quarantined: {sum(row.resolution_status == 'QUARANTINED' for row in rows)}",
                    f"- conflict nodes: {conflict_node_count}",
                    f"- conflict edges: {len(edges)}",
                    f"- review items: {len(review_items)}",
                    "",
                    "Conflicting assertions remain separate; broken locators are quarantined.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        conflict_nodes = conflict_node_count
        return EvidenceTraceSummary(
            assertions=len(rows),
            resolved=sum(row.resolution_status == "RESOLVED" for row in rows),
            quarantined=sum(row.resolution_status == "QUARANTINED" for row in rows),
            conflict_nodes=conflict_nodes,
            conflict_edges=len(edges),
            review_items=len(review_items),
            evidence_path=self.evidence_path,
            conflict_path=self.conflict_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
