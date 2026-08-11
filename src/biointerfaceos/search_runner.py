"""Fixture-backed systematic search runner with append-only receipts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.policy import SourceCandidate, SourcePolicyEngine
from biointerfaceos.search_matrix import SearchMatrixError, load_matrix

SOURCE_NAMES = {
    "europe_pmc": "Europe PMC",
    "pmc_oa": "PMC Open Access",
    "pride": "PRIDE",
    "geo": "NCBI GEO/SRA",
    "pubchem": "PubChem",
    "chembl": "ChEMBL",
    "zenodo": "Zenodo",
    "figshare": "Figshare",
    "osf": "Open Science Framework",
}
SOURCE_URLS = {
    "europe_pmc": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
    "pmc_oa": "https://www.ncbi.nlm.nih.gov/pmc/tools/openftlist/",
    "pride": "https://www.ebi.ac.uk/pride/ws/archive/v3/search/projects",
    "geo": "https://www.ncbi.nlm.nih.gov/geo/",
    "pubchem": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/",
    "chembl": "https://www.ebi.ac.uk/chembl/api/data/",
    "zenodo": "https://zenodo.org/api/records",
    "figshare": "https://api.figshare.com/v2/articles",
    "osf": "https://api.osf.io/v2/nodes/",
}


class SearchRunError(RuntimeError):
    """Raised when a fixture-backed search run is malformed or unsafe."""


@dataclass(frozen=True)
class SearchRunSummary:
    """One bounded search-run result."""

    run_id: str
    scope: str
    query_blocks: int
    pages: int
    raw_hits: int
    unique_candidates: int
    admitted: int
    quarantined: int
    response_hashes: tuple[str, ...]


class SearchRunner:
    """Execute matrix blocks against sanitized fixtures and persist receipts."""

    def __init__(
        self,
        root: Path,
        policy: SourcePolicyEngine,
        *,
        matrix_path: Path | None = None,
        fixture_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.policy = policy
        self.matrix_path = matrix_path or self.root / "configs/search_queries.yaml"
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/search/search_results.json"
        )

    @staticmethod
    def _load_fixture(path: Path) -> Mapping[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SearchRunError(f"cannot load search fixture {path}: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "results"}:
            raise SearchRunError("search fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["results"], Mapping):
            raise SearchRunError("search fixture schema is invalid")
        return value

    @staticmethod
    def _load_matrix_records(path: Path) -> tuple[dict[str, Any], ...]:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise SearchRunError(f"cannot load search matrix {path}: {exc}") from exc
        try:
            load_matrix(path)
        except SearchMatrixError as exc:
            raise SearchRunError(str(exc)) from exc
        queries = value.get("queries") if isinstance(value, Mapping) else None
        if not isinstance(queries, list) or not all(isinstance(item, dict) for item in queries):
            raise SearchRunError("search matrix queries are invalid")
        return tuple(queries)

    @staticmethod
    def _page_hash(page: Mapping[str, Any]) -> str:
        payload = (
            json.dumps(page, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _candidate(
        source: str,
        hit: Mapping[str, Any],
    ) -> tuple[SourceCandidate, str]:
        accession = hit.get("accession")
        if not isinstance(accession, str) or not accession.strip():
            raise SearchRunError("search hit requires a stable accession")
        accession = accession.strip()
        license_value = hit.get("license")
        license_identifier = license_value.strip() if isinstance(license_value, str) else None
        candidate = SourceCandidate.from_mapping(
            {
                "source_id": f"{source}:{accession}",
                "source_name": SOURCE_NAMES[source],
                "url": str(hit.get("url") or SOURCE_URLS[source]),
                "accession": accession,
                "license_identifier": license_identifier,
                "license_text": license_identifier,
                "evidence_location": "fixture-backed search hit",
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
        return candidate, accession

    def run(self, scope: str) -> SearchRunSummary:
        """Run one matrix scope and append immutable receipts."""
        if scope not in {"development", "validation"}:
            raise SearchRunError("scope must be development or validation")
        matrix_summary = load_matrix(self.matrix_path)
        target_scope = "train" if scope == "development" else "validation"
        queries = tuple(
            item
            for item in self._load_matrix_records(self.matrix_path)
            if item["scope"] == target_scope
        )
        if not queries:
            raise SearchRunError(f"matrix has no queries for scope {target_scope}")
        fixture = self._load_fixture(self.fixture_path)
        results = fixture["results"]
        timestamp = datetime.now(UTC).isoformat()
        run_id = hashlib.sha256(
            f"{scope}|{matrix_summary.sha256}|{timestamp}".encode()
        ).hexdigest()[:16]
        run_ledger = AppendOnlyJSONL(self.root / "reports/search_runs.jsonl")
        candidate_ledger = AppendOnlyJSONL(self.root / "registry/search_candidates.jsonl")
        run_ledger.initialize()
        candidate_ledger.initialize()
        existing_candidate_ids: set[str] = set()
        if candidate_ledger.path.exists():
            for line in candidate_ledger.path.read_text(encoding="utf-8").splitlines():
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SearchRunError("candidate ledger contains invalid JSON") from exc
                if isinstance(record, Mapping) and isinstance(record.get("candidate_id"), str):
                    existing_candidate_ids.add(record["candidate_id"])
        raw_hits = 0
        pages_seen = 0
        response_hashes: list[str] = []
        candidates: dict[str, dict[str, Any]] = {}
        admitted = 0
        quarantined = 0
        for query in queries:
            query_id = query["id"]
            payload = results.get(query_id)
            if not isinstance(payload, Mapping):
                raise SearchRunError(f"missing fixture result for {query_id}")
            pages = payload.get("pages")
            if not isinstance(pages, list) or not pages:
                raise SearchRunError(f"fixture result has no pages: {query_id}")
            seen_cursors: set[str] = set()
            next_cursor = "*"
            for _page_number, page in enumerate(pages, start=1):
                if not isinstance(page, Mapping):
                    raise SearchRunError(f"fixture page is not an object: {query_id}")
                cursor = page.get("cursor")
                if not isinstance(cursor, str) or cursor != next_cursor:
                    raise SearchRunError(f"cursor mismatch for {query_id}: {cursor}")
                if cursor in seen_cursors:
                    raise SearchRunError(f"cursor repeated for {query_id}: {cursor}")
                seen_cursors.add(cursor)
                page_hash = self._page_hash(page)
                response_hashes.append(page_hash)
                pages_seen += 1
                hits = page.get("hits")
                if not isinstance(hits, list):
                    raise SearchRunError(f"fixture page has no hits: {query_id}")
                raw_hits += len(hits)
                for hit in hits:
                    if not isinstance(hit, Mapping):
                        raise SearchRunError(f"fixture hit is not an object: {query_id}")
                    source = query["source"]
                    candidate, accession = self._candidate(source, hit)
                    key = candidate.source_id
                    decision = self.policy.evaluate(candidate)
                    existing = candidates.get(key)
                    if existing is None:
                        candidates[key] = {
                            "candidate_id": key,
                            "source": source,
                            "accession": accession,
                            "title": hit.get("title"),
                            "license": candidate.license_identifier,
                            "decision": decision.decision,
                            "rejection_code": decision.rejection_code,
                            "query_ids": [query_id],
                            "scopes": [scope],
                            "url": candidate.url,
                            "response_hashes": [page_hash],
                            "run_id": run_id,
                            "locked_test_accessed": False,
                        }
                        if decision.decision == "ADMIT_PUBLIC_REDISTRIBUTABLE":
                            admitted += 1
                        elif decision.decision == "QUARANTINE":
                            quarantined += 1
                    else:
                        if query_id not in existing["query_ids"]:
                            existing["query_ids"].append(query_id)
                        if scope not in existing["scopes"]:
                            existing["scopes"].append(scope)
                        if page_hash not in existing["response_hashes"]:
                            existing["response_hashes"].append(page_hash)
                next_value = page.get("next_cursor")
                if next_value in (None, ""):
                    break
                if not isinstance(next_value, str):
                    raise SearchRunError(f"next_cursor is invalid for {query_id}")
                if next_value in seen_cursors:
                    raise SearchRunError(f"cursor repeated for {query_id}: {next_value}")
                next_cursor = next_value
            else:
                raise SearchRunError(f"fixture pagination exceeded for {query_id}")
            run_ledger.append(
                {
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "scope": scope,
                    "matrix_version": matrix_summary.sha256,
                    "query_id": query_id,
                    "source": query["source"],
                    "axis": query["axis"],
                    "date_from": query["date_from"],
                    "date_to": query["date_to"],
                    "request_url": f"fixture://search/{query_id}",
                    "pages": len(seen_cursors),
                    "response_hashes": response_hashes[-len(seen_cursors) :],
                    "raw_hits": sum(
                        len(page.get("hits", []))
                        for page in pages[: len(seen_cursors)]
                        if isinstance(page, Mapping) and isinstance(page.get("hits"), list)
                    ),
                    "cursor_strategy": query["cursor_strategy"],
                    "fixture": True,
                    "locked_test_accessed": False,
                }
            )
        for record in sorted(candidates.values(), key=lambda item: item["candidate_id"]):
            if record["candidate_id"] not in existing_candidate_ids:
                candidate_ledger.append(record)
        return SearchRunSummary(
            run_id=run_id,
            scope=scope,
            query_blocks=len(queries),
            pages=pages_seen,
            raw_hits=raw_hits,
            unique_candidates=len(candidates),
            admitted=admitted,
            quarantined=quarantined,
            response_hashes=tuple(response_hashes),
        )
