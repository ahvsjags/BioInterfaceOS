"""Default-deny anonymous-access and license policy engine."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import pyarrow as pa
import pyarrow.parquet as pq
import yaml  # type: ignore[import-untyped]

POLICY_PATH = Path("configs/source_policy.yaml")
REJECTION_PATH = Path("registry/rejected_sources.parquet")
CANDIDATE_FIELDS = (
    "source_id",
    "source_name",
    "url",
    "accession",
    "license_identifier",
    "license_text",
    "evidence_location",
    "registration_required",
    "login_required",
    "api_key_required",
    "application_required",
    "approval_required",
    "institution_required",
    "data_use_agreement_required",
    "paid_required",
)
REJECTION_FIELDS = (
    "source_id",
    "source_name",
    "url",
    "accession",
    "decision",
    "rejection_code",
    "reason",
    "evidence_location",
    "license_identifier",
    "license_text",
    "checked_at",
)
_BOOL_FIELDS = frozenset(
    {
        "registration_required",
        "login_required",
        "api_key_required",
        "application_required",
        "approval_required",
        "institution_required",
        "data_use_agreement_required",
        "paid_required",
    }
)
_REJECTION_SCHEMA = pa.schema(
    [
        pa.field("source_id", pa.string(), nullable=False),
        pa.field("source_name", pa.string(), nullable=False),
        pa.field("url", pa.string(), nullable=False),
        pa.field("accession", pa.string(), nullable=True),
        pa.field("decision", pa.string(), nullable=False),
        pa.field("rejection_code", pa.string(), nullable=False),
        pa.field("reason", pa.string(), nullable=False),
        pa.field("evidence_location", pa.string(), nullable=True),
        pa.field("license_identifier", pa.string(), nullable=True),
        pa.field("license_text", pa.string(), nullable=True),
        pa.field("checked_at", pa.string(), nullable=False),
    ]
)


class PolicyError(ValueError):
    """Base error for policy configuration, candidate, and registry failures."""


class PolicyConfigError(PolicyError):
    """Raised when source policy configuration is malformed."""


class CandidateError(PolicyError):
    """Raised when a candidate is incomplete or unsafe."""


@dataclass(frozen=True)
class PolicyConfig:
    """Validated default-deny policy."""

    access_fields: tuple[str, ...]
    public_licenses: frozenset[str]
    analysis_only_licenses: frozenset[str]
    restricted_phrases: tuple[str, ...]
    unknown_action: str

    @classmethod
    def load(cls, root: Path, path: Path | str = POLICY_PATH) -> PolicyConfig:
        candidate = Path(path)
        config_path = (candidate if candidate.is_absolute() else root / candidate).resolve(
            strict=False
        )
        repository = root.resolve(strict=True)
        if config_path != repository and repository not in config_path.parents:
            raise PolicyConfigError("policy config is outside repository")
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise PolicyConfigError(f"cannot load policy config: {exc}") from exc
        if not isinstance(raw, dict) or set(raw) != {
            "schema_version",
            "access_requirements",
            "license_policy",
        }:
            raise PolicyConfigError("policy config keys are invalid")
        if raw["schema_version"] != 1:
            raise PolicyConfigError("schema_version must be 1")
        access = raw["access_requirements"]
        license_policy = raw["license_policy"]
        if not isinstance(access, dict) or set(access) != set(cls._default_access_fields()):
            raise PolicyConfigError("access_requirements keys are invalid")
        if not all(isinstance(access[name], bool) for name in access):
            raise PolicyConfigError("access requirement values must be boolean")
        licenses = {
            "public_licenses",
            "analysis_only_licenses",
            "restricted_phrases",
            "unknown_action",
        }
        if not isinstance(license_policy, dict) or set(license_policy) != licenses:
            raise PolicyConfigError("license_policy keys are invalid")
        public = cls._normalize_list(license_policy["public_licenses"])
        analysis = cls._normalize_list(license_policy["analysis_only_licenses"])
        restricted = tuple(cls._normalize_list(license_policy["restricted_phrases"]))
        unknown = license_policy["unknown_action"]
        if unknown not in {"QUARANTINE", "REJECT"}:
            raise PolicyConfigError("unknown_action must be QUARANTINE or REJECT")
        return cls(
            access_fields=tuple(cls._default_access_fields()),
            public_licenses=frozenset(public),
            analysis_only_licenses=frozenset(analysis),
            restricted_phrases=restricted,
            unknown_action=unknown,
        )

    @staticmethod
    def _default_access_fields() -> tuple[str, ...]:
        return (
            "registration_required",
            "login_required",
            "api_key_required",
            "application_required",
            "approval_required",
            "institution_required",
            "data_use_agreement_required",
            "paid_required",
        )

    @staticmethod
    def _normalize_list(value: object) -> list[str]:
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, str) for item in value)
        ):
            raise PolicyConfigError("license lists must be non-empty string arrays")
        return [_normalize(item) for item in value]


@dataclass(frozen=True)
class SourceCandidate:
    """Candidate source metadata used by the policy engine."""

    source_id: str
    source_name: str
    url: str
    accession: str | None
    license_identifier: str | None
    license_text: str | None
    evidence_location: str | None
    registration_required: bool
    login_required: bool
    api_key_required: bool
    application_required: bool
    approval_required: bool
    institution_required: bool
    data_use_agreement_required: bool
    paid_required: bool

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.source_name.strip():
            raise CandidateError("source_id and source_name are required")
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise CandidateError("candidate url must be absolute HTTP(S)")
        if parsed.username is not None or parsed.password is not None:
            raise CandidateError("candidate URL credentials are forbidden")
        if not self.license_identifier and not self.license_text:
            return
        if self.license_identifier is not None and not self.license_identifier.strip():
            raise CandidateError("license_identifier cannot be empty")
        if self.license_text is not None and not self.license_text.strip():
            raise CandidateError("license_text cannot be empty")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> SourceCandidate:
        if set(value) != set(CANDIDATE_FIELDS):
            missing = sorted(set(CANDIDATE_FIELDS) - set(value))
            extra = sorted(set(value) - set(CANDIDATE_FIELDS))
            raise CandidateError(f"candidate fields mismatch; missing={missing}, extra={extra}")
        for name in _BOOL_FIELDS:
            if not isinstance(value[name], bool):
                raise CandidateError(f"{name} must be boolean")
        return cls(**{name: value[name] for name in CANDIDATE_FIELDS})  # type: ignore[arg-type]


@dataclass(frozen=True)
class PolicyDecision:
    """A deterministic policy result with auditable reason."""

    decision: str
    rejection_code: str | None
    reason: str
    source_id: str
    evidence_location: str | None
    normalized_license: str | None


@dataclass(frozen=True)
class RejectionRecord:
    """One rejected or quarantined candidate in the registry."""

    source_id: str
    source_name: str
    url: str
    accession: str | None
    decision: str
    rejection_code: str
    reason: str
    evidence_location: str | None
    license_identifier: str | None
    license_text: str | None
    checked_at: str

    def to_mapping(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "url": self.url,
            "accession": self.accession,
            "decision": self.decision,
            "rejection_code": self.rejection_code,
            "reason": self.reason,
            "evidence_location": self.evidence_location,
            "license_identifier": self.license_identifier,
            "license_text": self.license_text,
            "checked_at": self.checked_at,
        }


class SourcePolicyEngine:
    """Evaluate candidates without any network or environment credential lookup."""

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config

    @classmethod
    def from_yaml(cls, root: Path, path: Path | str = POLICY_PATH) -> SourcePolicyEngine:
        return cls(PolicyConfig.load(root, path))

    def evaluate(self, candidate: SourceCandidate) -> PolicyDecision:
        """Apply access gates before conservative license classification."""
        blocked = [
            field_name
            for field_name in self.config._default_access_fields()
            if field_name in self.config.access_fields and getattr(candidate, field_name)
        ]
        if blocked:
            return PolicyDecision(
                decision="REJECT",
                rejection_code="REJECTED_CREDENTIALLED",
                reason=f"access prerequisite is not anonymous: {blocked[0]}",
                source_id=candidate.source_id,
                evidence_location=candidate.evidence_location,
                normalized_license=_classify_license(candidate, self.config),
            )
        normalized = _classify_license(candidate, self.config)
        if normalized is None:
            decision = self.config.unknown_action
            if decision == "REJECT":
                return PolicyDecision(
                    "REJECT",
                    "REJECTED_RESTRICTED_LICENSE",
                    "license is missing or unsupported",
                    candidate.source_id,
                    candidate.evidence_location,
                    None,
                )
            return PolicyDecision(
                "QUARANTINE",
                "LICENSE_UNCLEAR",
                "license is missing or unsupported; no redistribution assumption made",
                candidate.source_id,
                candidate.evidence_location,
                None,
            )
        if normalized in self.config.public_licenses:
            return PolicyDecision(
                "ADMIT_PUBLIC_REDISTRIBUTABLE",
                None,
                "explicit configured public redistribution license",
                candidate.source_id,
                candidate.evidence_location,
                normalized,
            )
        if normalized in self.config.analysis_only_licenses:
            return PolicyDecision(
                "ADMIT_ANALYSIS_ONLY",
                None,
                "explicit configured analysis-only license",
                candidate.source_id,
                candidate.evidence_location,
                normalized,
            )
        if normalized in self.config.restricted_phrases:
            return PolicyDecision(
                "REJECT",
                "REJECTED_RESTRICTED_LICENSE",
                "license text explicitly restricts redistribution",
                candidate.source_id,
                candidate.evidence_location,
                normalized,
            )
        decision = self.config.unknown_action
        return PolicyDecision(
            "REJECT" if decision == "REJECT" else "QUARANTINE",
            "REJECTED_RESTRICTED_LICENSE" if decision == "REJECT" else "LICENSE_UNCLEAR",
            "license identifier is not in the configured allowlist",
            candidate.source_id,
            candidate.evidence_location,
            normalized,
        )

    def self_test(self, fixture_dir: Path, registry: RejectionRegistry) -> tuple[int, int]:
        """Run local YAML fixtures and persist all reject/quarantine evidence."""
        passed = 0
        rejected = 0
        for path in sorted(fixture_dir.glob("*.yaml")):
            try:
                value = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as exc:
                raise PolicyError(f"cannot load fixture {path}: {exc}") from exc
            if not isinstance(value, dict) or set(value) != {
                "candidate",
                "expected_decision",
                "expected_code",
            }:
                raise PolicyError(f"invalid policy fixture envelope: {path}")
            candidate_value = value["candidate"]
            if not isinstance(candidate_value, dict):
                raise PolicyError(f"fixture candidate must be a mapping: {path}")
            candidate = SourceCandidate.from_mapping(candidate_value)
            expected_decision = value["expected_decision"]
            expected_code = value["expected_code"]
            if not isinstance(expected_decision, str) or not isinstance(expected_code, str):
                raise PolicyError(f"fixture expectations must be strings: {path}")
            result = self.evaluate(candidate)
            if (
                result.decision != expected_decision
                or (result.rejection_code or "") != expected_code
            ):
                raise PolicyError(
                    f"fixture mismatch {path.name}: got {result.decision}/{result.rejection_code}, "
                    f"expected {expected_decision}/{expected_code}"
                )
            if result.decision in {"REJECT", "QUARANTINE"}:
                registry.register(candidate, result)
                rejected += 1
            passed += 1
        return passed, rejected


def _normalize(value: str) -> str:
    return re.sub(r"[\s_-]+", " ", value.strip().upper()).strip()


def _classify_license(candidate: SourceCandidate, config: PolicyConfig) -> str | None:
    values = [
        value
        for value in (candidate.license_identifier, candidate.license_text)
        if value is not None
    ]
    normalized_values = [_normalize(value) for value in values]
    for value in normalized_values:
        if any(phrase in value for phrase in config.restricted_phrases):
            return next(phrase for phrase in config.restricted_phrases if phrase in value)
    for value in normalized_values:
        if value in config.public_licenses or value in config.analysis_only_licenses:
            return value
        if "CC BY NC" in value:
            return "CC BY NC"
        if "CC BY" in value:
            return "CC BY"
        if "CC0" in value or "CREATIVE COMMONS ZERO" in value:
            return "CC0"
        if "PUBLIC DOMAIN" in value:
            return "PUBLIC DOMAIN"
    return None


class RejectionRegistry:
    """Atomic Parquet registry for rejected and quarantined sources."""

    def __init__(self, root: Path, path: Path | str = REJECTION_PATH) -> None:
        self.root = root.resolve(strict=True)
        candidate = Path(path)
        self.path = (candidate if candidate.is_absolute() else self.root / candidate).resolve(
            strict=False
        )
        if self.path == self.root or self.root not in self.path.parents:
            raise PolicyError("rejection registry path escapes repository")

    def records(self) -> tuple[RejectionRecord, ...]:
        if not self.path.exists():
            return ()
        try:
            table = pq.read_table(self.path)
        except Exception as exc:
            raise PolicyError(f"cannot read rejection registry: {exc}") from exc
        if tuple(table.column_names) != REJECTION_FIELDS:
            raise PolicyError("rejection registry columns mismatch")
        return tuple(RejectionRecord(**row) for row in table.to_pylist())

    def write(self, records: Sequence[RejectionRecord]) -> None:
        seen: set[tuple[str, str, str]] = set()
        normalized = []
        for record in records:
            key = (record.source_id, record.url, record.rejection_code)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(record.to_mapping())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(normalized, schema=_REJECTION_SCHEMA)
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            os.close(descriptor)
            pq.write_table(table, temporary_name, compression="zstd")
            os.replace(temporary_name, self.path)
            temporary_name = None
        except Exception as exc:
            raise PolicyError(f"cannot write rejection registry: {exc}") from exc
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    def register(self, candidate: SourceCandidate, decision: PolicyDecision) -> None:
        if decision.decision not in {"REJECT", "QUARANTINE"} or decision.rejection_code is None:
            raise PolicyError("only rejected or quarantined decisions belong in rejection registry")
        current = list(self.records())
        current.append(
            RejectionRecord(
                source_id=candidate.source_id,
                source_name=candidate.source_name,
                url=candidate.url,
                accession=candidate.accession,
                decision=decision.decision,
                rejection_code=decision.rejection_code,
                reason=decision.reason,
                evidence_location=candidate.evidence_location,
                license_identifier=candidate.license_identifier,
                license_text=candidate.license_text,
                checked_at=datetime.now(UTC).isoformat(),
            )
        )
        self.write(current)

    def validate(self) -> int:
        return len(self.records())
