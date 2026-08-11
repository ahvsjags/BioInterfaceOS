"""Validation and hashing for the versioned BioInterfaceOS search matrix."""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ALLOWED_AXES = frozenset(
    {"material", "corona", "endpoint", "protocol", "species", "assay", "data_code"}
)
ALLOWED_SOURCES = frozenset(
    {"europe_pmc", "pmc_oa", "pride", "geo", "pubchem", "chembl", "zenodo", "figshare", "osf"}
)
ALLOWED_SCOPES = frozenset({"train", "validation"})
ALLOWED_CURSORS = frozenset(
    {"cursorMark", "page", "offset", "accession_seed", "provider_release", "single"}
)
QUERY_FIELDS = frozenset(
    {
        "id",
        "source",
        "axis",
        "scope",
        "query",
        "date_from",
        "date_to",
        "cursor_strategy",
        "rationale",
    }
)


class SearchMatrixError(ValueError):
    """Raised when a search matrix violates its reproducibility contract."""


@dataclass(frozen=True)
class SearchMatrixSummary:
    """Validated query-matrix summary and byte hash."""

    queries: int
    axes: tuple[str, ...]
    sources: tuple[str, ...]
    scopes: tuple[str, ...]
    sha256: str


def _iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise SearchMatrixError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SearchMatrixError(f"{field} must be an ISO date: {value}") from exc


def _require_text(item: dict[str, Any], field: str, identifier: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SearchMatrixError(f"query {identifier} field {field} is required")
    return value.strip()


def _canonical_query(value: str) -> str:
    return " ".join(value.lower().split())


def validate_matrix(value: Any) -> None:
    """Validate matrix structure, axes, date firewall, and exact duplicates."""
    if not isinstance(value, dict) or set(value) != {
        "schema_version",
        "matrix_version",
        "date_firewall",
        "queries",
    }:
        raise SearchMatrixError(
            "matrix must contain schema_version, matrix_version, date_firewall, queries"
        )
    if value["schema_version"] != 1:
        raise SearchMatrixError("schema_version must be 1")
    _require_text(value, "matrix_version", "matrix")
    firewall = value["date_firewall"]
    if not isinstance(firewall, dict) or set(firewall) != {
        "train_end",
        "validation_start",
        "validation_end",
        "lockbox_start",
        "lockbox_end",
    }:
        raise SearchMatrixError("date_firewall fields are invalid")
    train_end = _iso_date(firewall["train_end"], "train_end")
    validation_start = _iso_date(firewall["validation_start"], "validation_start")
    validation_end = _iso_date(firewall["validation_end"], "validation_end")
    lockbox_start = _iso_date(firewall["lockbox_start"], "lockbox_start")
    lockbox_end = _iso_date(firewall["lockbox_end"], "lockbox_end")
    if not train_end < validation_start <= validation_end < lockbox_start <= lockbox_end:
        raise SearchMatrixError("date_firewall intervals are not ordered")
    queries = value["queries"]
    if not isinstance(queries, list) or not queries:
        raise SearchMatrixError("queries must be a non-empty list")
    identifiers: list[str] = []
    duplicate_keys: list[tuple[str, str, str, str]] = []
    axes: list[str] = []
    sources: list[str] = []
    scopes: list[str] = []
    for item in queries:
        if not isinstance(item, dict):
            raise SearchMatrixError("each query must be an object")
        if set(item) != QUERY_FIELDS:
            raise SearchMatrixError("query fields are invalid")
        identifier = _require_text(item, "id", "query")
        if identifier in identifiers:
            raise SearchMatrixError(f"duplicate query id: {identifier}")
        identifiers.append(identifier)
        source = _require_text(item, "source", identifier)
        axis = _require_text(item, "axis", identifier)
        scope = _require_text(item, "scope", identifier)
        cursor = _require_text(item, "cursor_strategy", identifier)
        query_text = _require_text(item, "query", identifier)
        rationale = _require_text(item, "rationale", identifier)
        if not rationale:
            raise SearchMatrixError(f"query {identifier} rationale is empty")
        if source not in ALLOWED_SOURCES:
            raise SearchMatrixError(f"query {identifier} source is unsupported: {source}")
        if axis not in ALLOWED_AXES:
            raise SearchMatrixError(f"query {identifier} axis is unsupported: {axis}")
        if scope not in ALLOWED_SCOPES:
            raise SearchMatrixError(f"query {identifier} scope is unsupported: {scope}")
        if cursor not in ALLOWED_CURSORS:
            raise SearchMatrixError(f"query {identifier} cursor is unsupported: {cursor}")
        date_from = _iso_date(item["date_from"], f"{identifier}.date_from")
        date_to = _iso_date(item["date_to"], f"{identifier}.date_to")
        if date_from > date_to:
            raise SearchMatrixError(f"query {identifier} date range is reversed")
        if date_to >= lockbox_start or date_from >= lockbox_start:
            raise SearchMatrixError(f"query {identifier} intersects the lockbox date range")
        if date_to > validation_end:
            raise SearchMatrixError(f"query {identifier} exceeds validation date boundary")
        if scope == "train" and date_to != train_end:
            raise SearchMatrixError(f"query {identifier} train scope must end at train_end")
        if scope == "validation" and (date_from != validation_start or date_to != validation_end):
            raise SearchMatrixError(
                f"query {identifier} validation scope must use the frozen 2024 interval"
            )
        if "lockbox" in query_text.lower() or "2025-01-01" in query_text:
            raise SearchMatrixError(f"query {identifier} contains forbidden lockbox text")
        key = (source, axis, scope, _canonical_query(query_text))
        duplicate_keys.append(key)
        axes.append(axis)
        sources.append(source)
        scopes.append(scope)
    duplicates = [key for key, count in Counter(duplicate_keys).items() if count > 1]
    if duplicates:
        raise SearchMatrixError(f"duplicate query definitions: {duplicates[0]}")
    if set(axes) != ALLOWED_AXES:
        missing = sorted(ALLOWED_AXES - set(axes))
        raise SearchMatrixError(f"matrix is missing axes: {', '.join(missing)}")
    if set(scopes) != ALLOWED_SCOPES:
        missing_scopes = sorted(ALLOWED_SCOPES - set(scopes))
        raise SearchMatrixError(
            f"matrix must include train and validation scopes; missing={missing_scopes}"
        )


def load_matrix(path: Path) -> SearchMatrixSummary:
    """Load, validate, and hash one YAML matrix."""
    try:
        raw = path.read_bytes()
        value = yaml.safe_load(raw.decode("utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SearchMatrixError(f"cannot load search matrix {path}: {exc}") from exc
    validate_matrix(value)
    if not raw.endswith(b"\n"):
        raise SearchMatrixError("search matrix must end with a newline")
    parsed = value["queries"]
    assert isinstance(parsed, list)
    return SearchMatrixSummary(
        queries=len(parsed),
        axes=tuple(sorted({item["axis"] for item in parsed})),
        sources=tuple(sorted({item["source"] for item in parsed})),
        scopes=tuple(sorted({item["scope"] for item in parsed})),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
