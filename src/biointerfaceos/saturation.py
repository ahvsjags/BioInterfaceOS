"""Fixture-backed saturation and coverage-gap analysis."""

from __future__ import annotations

import html
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from biointerfaceos.search_matrix import SearchMatrixError, load_matrix


class SaturationError(RuntimeError):
    """Raised when saturation inputs violate their reproducibility contract."""


class SaturationAnalyzer:
    """Compute deterministic metrics from sealed search and expansion receipts."""

    def __init__(
        self,
        root: Path,
        *,
        matrix_path: Path | None = None,
        run_path: Path | None = None,
        candidate_path: Path | None = None,
        expansion_run_path: Path | None = None,
        edge_path: Path | None = None,
        expectations_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.matrix_path = matrix_path or self.root / "configs/search_queries.yaml"
        self.run_path = run_path or self.root / "reports/search_runs.jsonl"
        self.candidate_path = candidate_path or self.root / "registry/search_candidates.jsonl"
        self.expansion_run_path = expansion_run_path or self.root / "reports/expansion_runs.jsonl"
        self.edge_path = edge_path or self.root / "registry/expansion_edges.jsonl"
        self.expectations_path = expectations_path or (
            self.root / "tests/fixtures/search/saturation_expectations.json"
        )

    @staticmethod
    def _jsonl(path: Path) -> list[dict[str, Any]]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise SaturationError(f"cannot read {path}: {exc}") from exc
        records: list[dict[str, Any]] = []
        for number, line in enumerate(lines, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SaturationError(f"invalid JSON in {path} line {number}") from exc
            if not isinstance(value, Mapping):
                raise SaturationError(f"{path} line {number} is not an object")
            records.append(dict(value))
        return records

    @staticmethod
    def _expectations(path: Path) -> Mapping[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SaturationError(f"cannot load expectations {path}: {exc}") from exc
        if not isinstance(value, Mapping) or value.get("schema_version") != 1:
            raise SaturationError("saturation expectations schema is invalid")
        return value

    @staticmethod
    def _queries(path: Path) -> tuple[dict[str, Any], ...]:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8"))
            load_matrix(path)
        except (OSError, UnicodeError, yaml.YAMLError, SearchMatrixError) as exc:
            raise SaturationError(f"cannot load valid matrix {path}: {exc}") from exc
        records = value.get("queries") if isinstance(value, Mapping) else None
        if not isinstance(records, list) or not all(isinstance(item, Mapping) for item in records):
            raise SaturationError("matrix queries are invalid")
        return tuple(dict(item) for item in records)

    @staticmethod
    def _max_consecutive(values: list[bool]) -> int:
        current = maximum = 0
        for value in values:
            current = current + 1 if value else 0
            maximum = max(maximum, current)
        return maximum

    @staticmethod
    def _observed(queries: tuple[dict[str, Any], ...], axes: set[str], terms: list[str]) -> bool:
        corpus = " ".join(
            str(query["query"]).lower() for query in queries if query.get("axis") in axes
        )
        return any(term.lower() in corpus for term in terms)

    def analyze(self) -> dict[str, Any]:
        """Compute batch yield, axis yield, coverage gaps, and stopping criteria."""
        matrix = load_matrix(self.matrix_path)
        queries = self._queries(self.matrix_path)
        runs = self._jsonl(self.run_path)
        candidates = self._jsonl(self.candidate_path)
        expansion_runs = self._jsonl(self.expansion_run_path)
        edges = self._jsonl(self.edge_path)
        expectations = self._expectations(self.expectations_path)
        if not runs or not candidates:
            raise SaturationError("search run and candidate ledgers must be non-empty")
        all_records = runs + candidates + expansion_runs + edges
        if any(row.get("fixture") is not True for row in runs + expansion_runs):
            raise SaturationError("saturation requires fixture-backed receipts")
        if any(row.get("locked_test_accessed") is not False for row in all_records):
            raise SaturationError("locked-test access flag is not clean")

        run_query_ids: list[str] = []
        for row in runs:
            value = row.get("query_id")
            if not isinstance(value, str) or not value:
                raise SaturationError("search receipts require query_id")
            run_query_ids.append(value)
        if len(run_query_ids) != len(set(run_query_ids)):
            raise SaturationError("search receipts contain duplicate query IDs")
        query_by_id = {str(query["id"]): query for query in queries}
        unknown = sorted(set(run_query_ids) - set(query_by_id))
        if unknown:
            raise SaturationError(f"search receipts contain unknown queries: {unknown}")

        candidate_by_id: dict[str, dict[str, Any]] = {}
        for row in candidates:
            candidate_id = row.get("candidate_id")
            query_ids = row.get("query_ids")
            if not isinstance(candidate_id, str) or not isinstance(query_ids, list):
                raise SaturationError("candidate row lacks candidate_id or query_ids")
            if candidate_id in candidate_by_id:
                raise SaturationError(f"duplicate candidate ID: {candidate_id}")
            candidate_by_id[candidate_id] = row
        positions = {query_id: index for index, query_id in enumerate(run_query_ids)}
        first_position: dict[str, int] = {}
        for candidate_id, row in candidate_by_id.items():
            matches = [positions[qid] for qid in row["query_ids"] if qid in positions]
            if not matches:
                raise SaturationError(f"candidate {candidate_id} is not linked to a run")
            first_position[candidate_id] = min(matches)

        batches: list[dict[str, Any]] = []
        cumulative = 0
        for position, row in enumerate(runs):
            query_id = str(row["query_id"])
            query = query_by_id[query_id]
            novel = [
                candidate_id for candidate_id, first in first_position.items() if first == position
            ]
            eligible = sum(
                candidate_by_id[candidate_id].get("decision") == "ADMIT_PUBLIC_REDISTRIBUTABLE"
                for candidate_id in novel
            )
            quarantined = sum(
                candidate_by_id[candidate_id].get("decision") == "QUARANTINE"
                for candidate_id in novel
            )
            cumulative += eligible
            raw_hits = int(row.get("raw_hits", 0))
            batches.append(
                {
                    "batch": position + 1,
                    "query_id": query_id,
                    "scope": row["scope"],
                    "source": query["source"],
                    "axis": query["axis"],
                    "raw_hits": raw_hits,
                    "novel_candidates": len(novel),
                    "novel_eligible": eligible,
                    "novel_quarantined": quarantined,
                    "duplicate_or_cross_query_hits": max(0, raw_hits - len(novel)),
                    "cumulative_novel_eligible": cumulative,
                }
            )

        totals: dict[str, dict[str, Any]] = {}
        for batch in batches:
            axis = str(batch["axis"])
            total = totals.setdefault(
                axis,
                {
                    "axis": axis,
                    "query_blocks": 0,
                    "raw_hits": 0,
                    "novel_candidates": 0,
                    "novel_eligible": 0,
                    "novel_quarantined": 0,
                },
            )
            total["query_blocks"] += 1
            for field in ("raw_hits", "novel_candidates", "novel_eligible", "novel_quarantined"):
                total[field] += batch[field]

        edge_keys = [row.get("target_key") for row in edges]
        if any(not isinstance(key, str) or not key for key in edge_keys):
            raise SaturationError("expansion edge target_key is missing")
        if len(edge_keys) != len(set(edge_keys)):
            raise SaturationError("expansion edge targets are not deduplicated")

        gaps: list[dict[str, Any]] = []
        proposals: list[dict[str, Any]] = []
        executed_scopes = {str(row["scope"]) for row in runs}
        validation_queries = [query for query in queries if query["scope"] == "validation"]
        if validation_queries and "validation" not in executed_scopes:
            gaps.append(
                {
                    "id": "validation-2024-not-executed",
                    "kind": "year_scope",
                    "status": "OPEN",
                    "evidence": "Frozen 2024 validation blocks have no search receipts.",
                    "missing_interval": "2024-01-01..2024-12-31",
                    "query_ids": [query["id"] for query in validation_queries],
                }
            )
            proposals.append(
                {
                    "id": "run-validation-2024",
                    "kind": "year_scope",
                    "query": "Execute the frozen 2024 validation scope across all seven axes.",
                    "source_queries": [query["id"] for query in validation_queries],
                }
            )

        for family in expectations["material_families"]:
            family_id = str(family["id"])
            terms = [str(term) for term in family["terms"]]
            if not self._observed(queries, {"material"}, terms):
                gaps.append(
                    {
                        "id": f"material-{family_id}",
                        "kind": "material",
                        "status": "OPEN",
                        "evidence": "No material-axis query contains the required vocabulary.",
                        "missing_terms": terms,
                    }
                )
                proposals.append(
                    {
                        "id": f"query-material-{family_id}",
                        "kind": "material",
                        "query": str(family["proposal"]),
                        "source_queries": [],
                    }
                )

        for family in expectations["endpoint_families"]:
            family_id = str(family["id"])
            terms = [str(term) for term in family["terms"]]
            if not self._observed(queries, {"endpoint", "assay"}, terms):
                gaps.append(
                    {
                        "id": f"endpoint-{family_id}",
                        "kind": "endpoint",
                        "status": "OPEN",
                        "evidence": "No endpoint/assay query contains the required vocabulary.",
                        "missing_terms": terms,
                    }
                )
                proposals.append(
                    {
                        "id": f"query-endpoint-{family_id}",
                        "kind": "endpoint",
                        "query": str(family["proposal"]),
                        "source_queries": [],
                    }
                )

        validation_sources = {str(query["source"]) for query in validation_queries}
        observed_validation_sources = {
            str(row["source"]) for row in runs if row["scope"] == "validation"
        }
        missing_sources = sorted(validation_sources - observed_validation_sources)
        if missing_sources:
            gaps.append(
                {
                    "id": "validation-sources-not-executed",
                    "kind": "source",
                    "status": "OPEN",
                    "evidence": "Validation provider blocks have no validation receipts.",
                    "missing_sources": missing_sources,
                }
            )

        eligible_yields = [int(batch["novel_eligible"]) for batch in batches]
        threshold = float(expectations["stopping"]["low_yield_threshold"])
        low_yield = [
            bool(batch["raw_hits"]) and batch["novel_eligible"] / batch["raw_hits"] < threshold
            for batch in batches
        ]
        max_zero = self._max_consecutive([yield_value == 0 for yield_value in eligible_yields])
        max_low = self._max_consecutive(low_yield)
        zero_limit = int(expectations["stopping"]["consecutive_zero_batches"])
        low_limit = int(expectations["stopping"]["consecutive_low_yield_batches"])
        stopping = {
            "consecutive_zero_batches": max_zero,
            "zero_batch_limit": zero_limit,
            "consecutive_low_yield_batches": max_low,
            "low_yield_limit": low_limit,
            "low_yield_threshold": threshold,
            "validation_scope_complete": "validation" in executed_scopes,
            "open_gap_count": len(gaps),
            "decision": (
                "STOP"
                if max_zero >= zero_limit
                and max_low >= low_limit
                and "validation" in executed_scopes
                and not gaps
                else "CONTINUE"
            ),
            "rationale": (
                "Continue until validation, declared coverage gaps, and "
                "diminishing-return criteria are satisfied."
            ),
        }
        return {
            "schema_version": 1,
            "fixture": True,
            "locked_test_accessed": False,
            "matrix_sha256": matrix.sha256,
            "search": {
                "run_rows": len(runs),
                "query_blocks": len(batches),
                "raw_hits": sum(batch["raw_hits"] for batch in batches),
                "unique_candidates": len(candidates),
                "admitted_candidates": sum(
                    row.get("decision") == "ADMIT_PUBLIC_REDISTRIBUTABLE" for row in candidates
                ),
                "quarantined_candidates": sum(
                    row.get("decision") == "QUARANTINE" for row in candidates
                ),
            },
            "expansion": {
                "run_rows": len(expansion_runs),
                "raw_edges": sum(int(row.get("edge_count", 0)) for row in expansion_runs),
                "unique_targets": len(edges),
                "admitted_targets": sum(
                    row.get("decision") == "ADMIT_PUBLIC_REDISTRIBUTABLE" for row in edges
                ),
                "quarantined_targets": sum(row.get("decision") == "QUARANTINE" for row in edges),
                "max_depth": max((int(row.get("min_depth", 1)) for row in edges), default=0),
            },
            "batches": batches,
            "axis_totals": [totals[key] for key in sorted(totals)],
            "coverage_gaps": gaps,
            "gap_query_proposals": proposals,
            "stopping": stopping,
        }

    def write_report(self, path: Path | None = None) -> tuple[Path, dict[str, Any]]:
        """Write a self-contained HTML report."""
        output = path or self.root / "reports/search_saturation.html"
        metrics = self.analyze()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.render_html(metrics), encoding="utf-8")
        return output, metrics

    @staticmethod
    def render_html(metrics: Mapping[str, Any]) -> str:
        """Render metrics as a compact self-contained HTML report."""

        def td(value: Any) -> str:
            return f"<td>{html.escape(str(value))}</td>"

        batch_fields = (
            "batch",
            "query_id",
            "axis",
            "raw_hits",
            "novel_candidates",
            "novel_eligible",
            "duplicate_or_cross_query_hits",
            "cumulative_novel_eligible",
        )
        batch_rows = "".join(
            "<tr>" + "".join(td(batch[field]) for field in batch_fields) + "</tr>"
            for batch in metrics["batches"]
        )
        axis_fields = (
            "axis",
            "query_blocks",
            "raw_hits",
            "novel_candidates",
            "novel_eligible",
            "novel_quarantined",
        )
        axis_rows = "".join(
            "<tr>" + "".join(td(total[field]) for field in axis_fields) + "</tr>"
            for total in metrics["axis_totals"]
        )
        gap_rows = "".join(
            "<tr>"
            + td(gap["id"])
            + td(gap["kind"])
            + td(gap["status"])
            + td(gap["evidence"])
            + "</tr>"
            for gap in metrics["coverage_gaps"]
        )
        search = metrics["search"]
        expansion = metrics["expansion"]
        stopping = metrics["stopping"]
        payload = html.escape(json.dumps(metrics, sort_keys=True, indent=2))
        proposals = "".join(
            f"<li>{html.escape(str(item['id']))}: {html.escape(str(item['query']))}</li>"
            for item in metrics["gap_query_proposals"]
        )
        search_summary = (
            f"Search: {search['raw_hits']} raw hits, "
            f"{search['unique_candidates']} unique candidates, "
            f"{search['admitted_candidates']} admitted, "
            f"{search['quarantined_candidates']} quarantined."
        )
        expansion_summary = (
            f"Expansion: {expansion['raw_edges']} raw edges, "
            f"{expansion['unique_targets']} unique targets, "
            f"{expansion['admitted_targets']} admitted, "
            f"{expansion['quarantined_targets']} quarantined."
        )
        stopping_summary = (
            f"Stopping decision: {stopping['decision']}; open gaps={stopping['open_gap_count']}."
        )
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8">
<title>BioInterfaceOS Search Saturation</title>
<style>
body {{ font-family: sans-serif; margin: 2rem; color: #1f2937; }}
table {{ border-collapse: collapse; margin: 1rem 0 2rem; width: 100%; }}
th, td {{ border: 1px solid #cbd5e1; padding: .35rem; text-align: left; }}
th {{ background: #e2e8f0; }}
</style></head>
<body>
<h1>BioInterfaceOS Search Saturation and Coverage Gaps</h1>
<p>Fixture-backed report; no live endpoints or locked-test payloads were accessed.</p>
<p>Matrix SHA-256: {html.escape(str(metrics["matrix_sha256"]))}</p>
<h2>Summary</h2>
<ul>
<li>{html.escape(search_summary)}</li>
<li>{html.escape(expansion_summary)}</li>
<li>{html.escape(stopping_summary)}</li>
</ul>
<h2>Novel eligible-study yield by batch</h2>
<table>
<thead><tr>
<th>Batch</th><th>Query</th><th>Axis</th><th>Raw hits</th>
<th>Novel candidates</th><th>Novel eligible</th>
<th>Duplicate/cross-query</th><th>Cumulative eligible</th>
</tr></thead><tbody>{batch_rows}</tbody></table>
<h2>Yield by axis</h2>
<table>
<thead><tr>
<th>Axis</th><th>Query blocks</th><th>Raw hits</th>
<th>Novel candidates</th><th>Novel eligible</th><th>Novel quarantined</th>
</tr></thead><tbody>{axis_rows}</tbody></table>
<h2>Coverage gaps</h2>
<table>
<thead><tr><th>ID</th><th>Kind</th><th>Status</th><th>Evidence</th></tr></thead>
<tbody>{gap_rows}</tbody></table>
<h2>Gap query proposals</h2>
<ul>{proposals}</ul>
<h2>Stopping criteria</h2>
<pre>{html.escape(json.dumps(stopping, sort_keys=True, indent=2))}</pre>
<script type="application/json" id="saturation-data">{payload}</script>
</body></html>
"""
