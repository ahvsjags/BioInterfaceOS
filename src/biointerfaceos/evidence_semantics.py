"""Fail-closed vocabulary and metadata rules for scientific evidence classes."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any


class EvidenceSemanticsError(ValueError):
    """Raised when an artifact crosses an evidence-class boundary."""


class EvidenceClass(StrEnum):
    """Non-interchangeable sources of support for a scientific statement."""

    FIXTURE_TEST = "FIXTURE_TEST"
    SOFTWARE_REPLAY = "SOFTWARE_REPLAY"
    DEVELOPMENT_OBSERVATION = "DEVELOPMENT_OBSERVATION"
    LOCKED_EVALUATION = "LOCKED_EVALUATION"
    EXTERNAL_REPRODUCTION = "EXTERNAL_REPRODUCTION"


class AllowedClaimLevel(StrEnum):
    """Strongest statement an artifact can support without extra evidence."""

    CONTRACT_TEST = "CONTRACT_TEST"
    SOFTWARE_REPLAY = "SOFTWARE_REPLAY"
    EXPLORATORY = "EXPLORATORY"
    EVALUATOR_BACKED = "EVALUATOR_BACKED"
    EXTERNALLY_REPRODUCED = "EXTERNALLY_REPRODUCED"


ALLOWED_CLAIM_LEVEL = {
    EvidenceClass.FIXTURE_TEST: AllowedClaimLevel.CONTRACT_TEST,
    EvidenceClass.SOFTWARE_REPLAY: AllowedClaimLevel.SOFTWARE_REPLAY,
    EvidenceClass.DEVELOPMENT_OBSERVATION: AllowedClaimLevel.EXPLORATORY,
    EvidenceClass.LOCKED_EVALUATION: AllowedClaimLevel.EVALUATOR_BACKED,
    EvidenceClass.EXTERNAL_REPRODUCTION: AllowedClaimLevel.EXTERNALLY_REPRODUCED,
}

CONTRACT_STATUSES = frozenset(
    {
        "CONTRACT_EXPECTATION_MET",
        "CONTRACT_EXPECTATION_CONTRADICTED",
        "CONTRACT_EVIDENCE_INDETERMINATE",
    }
)

LEGACY_FIXTURE_STATUS_MAP = {
    "REPLICATED": "CONTRACT_EXPECTATION_MET",
    "REFUTED": "CONTRACT_EXPECTATION_CONTRADICTED",
    "INCONCLUSIVE": "CONTRACT_EVIDENCE_INDETERMINATE",
}

PROHIBITED_PATTERNS = {
    EvidenceClass.FIXTURE_TEST: (
        r"\bempirical(?:ly)?\b",
        r"\bexperimental validation\b",
        r"\bindependent stud(?:y|ies)\b",
        r"\bscientific replication\b",
        r"\breplicated\b",
        r"\brefuted\b",
        r"\blaw discovery\b",
        r"\buniversal law\b",
        r"\bexternal OOD validation\b",
    ),
    EvidenceClass.SOFTWARE_REPLAY: (
        r"\bscientific replication\b",
        r"\bindependent replication\b",
        r"\bempirical validation\b",
    ),
    EvidenceClass.DEVELOPMENT_OBSERVATION: (
        r"\bexternally validated\b",
        r"\breplicated\b",
    ),
    EvidenceClass.LOCKED_EVALUATION: (r"\buniversal law\b",),
    EvidenceClass.EXTERNAL_REPRODUCTION: (r"\buniversal(?:ly)?\b",),
}


def metadata_for(evidence_class: EvidenceClass) -> dict[str, str]:
    """Return required, explicit metadata for a newly generated artifact."""

    return {
        "evidence_class": evidence_class.value,
        "allowed_claim_level": ALLOWED_CLAIM_LEVEL[evidence_class].value,
    }


def require_metadata(value: Any, label: str) -> tuple[EvidenceClass, AllowedClaimLevel]:
    """Reject absent, unknown, or over-permissive evidence metadata."""

    if not isinstance(value, dict):
        raise EvidenceSemanticsError(f"{label} evidence metadata must be an object")
    try:
        evidence_class = EvidenceClass(value["evidence_class"])
        claim_level = AllowedClaimLevel(value["allowed_claim_level"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceSemanticsError(f"{label} evidence metadata is missing or invalid") from exc
    expected = ALLOWED_CLAIM_LEVEL[evidence_class]
    if claim_level is not expected:
        raise EvidenceSemanticsError(f"{label} claim level {claim_level.value} exceeds {evidence_class.value}")
    return evidence_class, claim_level


def forbidden_terms(text: str, evidence_class: EvidenceClass) -> list[str]:
    """Return prohibited scientific-language tokens for an evidence class."""

    lowered = text.lower()
    return [
        pattern for pattern in PROHIBITED_PATTERNS[evidence_class] if re.search(pattern, lowered, flags=re.IGNORECASE)
    ]


def require_safe_text(text: str, evidence_class: EvidenceClass, label: str) -> None:
    """Fail before a fixture or replay artifact can emit stronger wording."""

    findings = forbidden_terms(text, evidence_class)
    if findings:
        raise EvidenceSemanticsError(f"{label} crosses evidence boundary: {findings}")


def normalize_contract_status(status: Any) -> str:
    """Map legacy fixture labels only while reading old artifacts, never while writing new ones."""

    if not isinstance(status, str) or not status:
        raise EvidenceSemanticsError("contract status must be a non-empty string")
    if status in CONTRACT_STATUSES:
        return status
    if status in LEGACY_FIXTURE_STATUS_MAP:
        return LEGACY_FIXTURE_STATUS_MAP[status]
    raise EvidenceSemanticsError(f"unknown fixture contract status: {status}")
