"""Bounded citation, dataset, supplement, and code-link expansion."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine


class ExpansionError(RuntimeError):
    """Raised when a bounded expansion graph is malformed."""


@dataclass(frozen=True)
class ExpansionSummary:
    """One bounded expansion result."""

    run_id: str
    scope: str
    depth: int
    seed_candidates: int
    raw_edges: int
    unique_targets: int
    admitted: int
    quarantined: int


class ExpansionRunner:
    """Expand a synthetic public metadata graph with append-only receipts."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        *,
        seed_path: Path | None = None,
        fixture_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.policy = policy
        self.seed_path = seed_path or self.root / "registry/search_candidates.jsonl"
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/expansion/expansion_results.json"
        )

    @staticmethod
    def _load_json(path: Path) -> Mapping[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExpansionError(f"cannot load expansion fixture {path}: {exc}") from exc
        if not isinstance(value, Mapping):
            raise ExpansionError(f"expansion payload is not an object: {path}")
        return value

    @staticmethod
    def _load_seed_ids(path: Path) -> tuple[str, ...]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ExpansionError(f"cannot load seed registry {path}") from exc
        identifiers: list[str] = []
        for line in lines:
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExpansionError("seed registry contains invalid JSON") from exc
            if not isinstance(value, Mapping):
                raise ExpansionError("seed registry row is not an object")
            candidate_id = value.get("candidate_id")
            if isinstance(candidate_id, str) and candidate_id not in identifiers:
                identifiers.append(candidate_id)
        if not identifiers:
            raise ExpansionError("seed registry has no candidate IDs")
        return tuple(identifiers)

    @staticmethod
    def _target_key(edge: Mapping[str, Any]) -> str:
        doi = edge.get("doi")
        if isinstance(doi, str) and doi.strip():
            return f"doi:{doi.strip().lower().removeprefix('https://doi.org/')}"
        accession = edge.get("accession")
        source = edge.get("source")
        if isinstance(accession, str) and accession.strip() and isinstance(source, str):
            return f"{source.strip().lower()}:{accession.strip()}"
        url = edge.get("url")
        if isinstance(url, str) and urlsplit(url).scheme in {"http", "https"}:
            return f"url:{url.rstrip('/').lower()}"
        raise ExpansionError("expansion edge needs DOI, source/accession, or HTTP URL")

    @staticmethod
    def _edge_hash(edge: Mapping[str, Any]) -> str:
        payload = (
            json.dumps(edge, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _candidate(edge: Mapping[str, Any], target_key: str) -> SourceCandidate:
        source = edge.get("source")
        if not isinstance(source, str) or not source.strip():
            source = "expansion"
        source = source.strip().lower()
        url = edge.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ExpansionError(f"target {target_key} has no URL")
        license_value = edge.get("license")
        license_identifier = license_value.strip() if isinstance(license_value, str) else None
        accession = edge.get("accession")
        accession_value = accession.strip() if isinstance(accession, str) else target_key
        return SourceCandidate.from_mapping(
            {
                "source_id": f"expansion:{target_key}",
                "source_name": source,
                "url": url,
                "accession": accession_value,
                "license_identifier": license_identifier,
                "license_text": license_identifier,
                "evidence_location": "fixture-backed expansion edge",
                "registration_required": False,
                "login_required": False,
                "api_key_required": False,
                "application_required": False,
                "approval_required": False,
                "institution_required": False,
                "data_use_agreement_required": False,
                "paid_required": False,
            }
        )

    def run(self, scope: str, depth: int = 2) -> ExpansionSummary:
        """Expand seed candidates to a bounded depth."""
        if scope != "development":
            raise ExpansionError("fixture expansion currently supports development scope only")
        if not 0 < depth <= 2:
            raise ExpansionError("depth must be between 1 and 2")
        seeds = self._load_seed_ids(self.seed_path)
        fixture = self._load_json(self.fixture_path)
        if fixture.get("schema_version") != 1:
            raise ExpansionError("expansion fixture schema_version must be 1")
        edges_by_parent = fixture.get("edges")
        if not isinstance(edges_by_parent, Mapping):
            raise ExpansionError("expansion fixture edges must be an object")
        timestamp = datetime.now(UTC).isoformat()
        run_id = hashlib.sha256(f"{scope}|{depth}|{timestamp}".encode()).hexdigest()[:16]
        run_ledger = AppendOnlyJSONL(self.root / "reports/expansion_runs.jsonl")
        edge_ledger = AppendOnlyJSONL(self.root / "registry/expansion_edges.jsonl")
        run_ledger.initialize()
        edge_ledger.initialize()
        existing_targets: set[str] = set()
        for line in edge_ledger.path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExpansionError("expansion edge ledger contains invalid JSON") from exc
            if isinstance(value, Mapping) and isinstance(value.get("target_key"), str):
                existing_targets.add(value["target_key"])
        frontier: list[tuple[str, int]] = [(seed, 0) for seed in seeds]
        expanded: set[tuple[str, int]] = set()
        target_records: dict[str, dict[str, Any]] = {}
        raw_edges = 0
        admitted = 0
        quarantined = 0
        while frontier:
            parent_id, parent_depth = frontier.pop(0)
            marker = (parent_id, parent_depth)
            if marker in expanded or parent_depth >= depth:
                continue
            expanded.add(marker)
            raw = edges_by_parent.get(parent_id)
            if raw is None:
                continue
            if not isinstance(raw, list):
                raise ExpansionError(f"edges for {parent_id} must be a list")
            response_hash = self._edge_hash({"parent": parent_id, "edges": raw})
            run_ledger.append(
                {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "scope": scope,
                    "depth": parent_depth + 1,
                    "parent_id": parent_id,
                    "edge_count": len(raw),
                    "response_sha256": response_hash,
                    "fixture": True,
                    "locked_test_accessed": False,
                }
            )
            for edge in raw:
                if not isinstance(edge, Mapping):
                    raise ExpansionError(f"edge for {parent_id} is not an object")
                edge_type = edge.get("edge_type")
                if not isinstance(edge_type, str) or not edge_type.strip():
                    raise ExpansionError(f"edge for {parent_id} has no edge_type")
                target_key = self._target_key(edge)
                raw_edges += 1
                candidate = self._candidate(edge, target_key)
                decision = self.policy.evaluate(candidate)
                record = target_records.get(target_key)
                if record is None:
                    record = {
                        "target_key": target_key,
                        "target_source": edge.get("source"),
                        "accession": edge.get("accession"),
                        "doi": edge.get("doi"),
                        "url": edge.get("url"),
                        "title": edge.get("title"),
                        "edge_types": [edge_type],
                        "parent_ids": [parent_id],
                        "min_depth": parent_depth + 1,
                        "license": candidate.license_identifier,
                        "decision": decision.decision,
                        "rejection_code": decision.rejection_code,
                        "response_sha256": response_hash,
                        "run_id": run_id,
                        "locked_test_accessed": False,
                    }
                    target_records[target_key] = record
                    if decision.decision == "ADMIT_PUBLIC_REDISTRIBUTABLE":
                        admitted += 1
                    elif decision.decision == "QUARANTINE":
                        quarantined += 1
                    if parent_depth + 1 < depth:
                        frontier.append((target_key, parent_depth + 1))
                else:
                    if edge_type not in record["edge_types"]:
                        record["edge_types"].append(edge_type)
                    if parent_id not in record["parent_ids"]:
                        record["parent_ids"].append(parent_id)
        for target_key, record in sorted(target_records.items()):
            if target_key not in existing_targets:
                edge_ledger.append(record)
        return ExpansionSummary(
            run_id=run_id,
            scope=scope,
            depth=depth,
            seed_candidates=len(seeds),
            raw_edges=raw_edges,
            unique_targets=len(target_records),
            admitted=admitted,
            quarantined=quarantined,
        )
