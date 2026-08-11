"""Schema and validation helpers for specialized nanodatabase admission audits."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

AUDIT_STATUSES = frozenset({"ADMIT_PUBLIC_SUBSTITUTE", "METADATA_ONLY", "QUARANTINE", "REJECT"})
REQUIRED_FIELDS = (
    "id",
    "name",
    "official_url",
    "anonymous_access",
    "api_or_export",
    "license_signal",
    "schema_relevance",
    "decision",
    "decision_code",
    "evidence_urls",
    "next_step",
)


class NanodatabaseAuditError(ValueError):
    """Raised when the specialized-database audit is malformed."""


@dataclass(frozen=True)
class AuditSummary:
    """Validated candidate decision counts."""

    candidates: int
    admitted_substitutes: int
    metadata_only: int
    quarantined: int
    rejected: int


def _validate_url(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NanodatabaseAuditError(f"{field} must be a non-empty URL")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise NanodatabaseAuditError(f"{field} must be an absolute HTTP(S) URL")
    return value


def validate_audit(value: Any) -> AuditSummary:
    """Validate a JSON audit decision envelope and return decision counts."""
    if not isinstance(value, dict) or set(value) != {"schema_version", "decisions"}:
        raise NanodatabaseAuditError("audit must contain schema_version and decisions")
    if value["schema_version"] != 1:
        raise NanodatabaseAuditError("audit schema_version must be 1")
    decisions = value["decisions"]
    if not isinstance(decisions, list) or not decisions:
        raise NanodatabaseAuditError("audit decisions must be a non-empty list")
    identifiers: list[str] = []
    statuses: list[str] = []
    for index, item in enumerate(decisions):
        if not isinstance(item, dict) or set(item) != set(REQUIRED_FIELDS):
            raise NanodatabaseAuditError(f"decision {index} fields are invalid")
        identifier = item["id"]
        if not isinstance(identifier, str) or not identifier.strip():
            raise NanodatabaseAuditError(f"decision {index} id is invalid")
        identifiers.append(identifier)
        for field in (
            "name",
            "anonymous_access",
            "api_or_export",
            "license_signal",
            "schema_relevance",
            "decision_code",
            "next_step",
        ):
            if not isinstance(item[field], str) or not item[field].strip():
                raise NanodatabaseAuditError(f"decision {identifier} field {field} is invalid")
        _validate_url(item["official_url"], f"decision {identifier} official_url")
        evidence_urls = item["evidence_urls"]
        if not isinstance(evidence_urls, list) or not evidence_urls:
            raise NanodatabaseAuditError(f"decision {identifier} needs evidence_urls")
        for evidence_url in evidence_urls:
            _validate_url(evidence_url, f"decision {identifier} evidence_url")
        decision = item["decision"]
        if decision not in AUDIT_STATUSES:
            raise NanodatabaseAuditError(f"decision {identifier} status is invalid: {decision}")
        statuses.append(decision)
    duplicate_ids = sorted(
        identifier for identifier, count in Counter(identifiers).items() if count > 1
    )
    if duplicate_ids:
        raise NanodatabaseAuditError(f"duplicate audit ids: {', '.join(duplicate_ids)}")
    counts = Counter(statuses)
    return AuditSummary(
        candidates=len(decisions),
        admitted_substitutes=counts["ADMIT_PUBLIC_SUBSTITUTE"],
        metadata_only=counts["METADATA_ONLY"],
        quarantined=counts["QUARANTINE"],
        rejected=counts["REJECT"],
    )


def load_audit(path: Path) -> AuditSummary:
    """Load and validate one JSON admission decision file."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NanodatabaseAuditError(f"cannot load audit {path}: {exc}") from exc
    return validate_audit(value)
