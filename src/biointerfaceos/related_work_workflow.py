"""Fail-closed external literature, comparator, and terminology audit for R2."""

from __future__ import annotations

import hashlib
import json
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RelatedWorkError(RuntimeError):
    """Raised when the R2 external-evidence packet is incomplete or unsafe."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RelatedWorkError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise RelatedWorkError(f"{label} must be an array")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RelatedWorkError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RelatedWorkError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class RelatedWorkSummary:
    """Compact accounting for the R2 related-work evidence packet."""

    citation_count: int
    comparator_count: int
    manuscript_scope_count: int
    glossary_term_count: int
    receipt_path: Path


class RelatedWorkWorkflow:
    """Validate the external evidence required before the R2 manuscript rebuild."""

    AUDIT_ID = "bioif-r2-related-work-audit-v1.1.0"
    AUDITED_AT = "2026-08-12T00:00:00+00:00"
    REGISTRY_RELATIVE = "docs/literature/R2_EXTERNAL_EVIDENCE.json"
    MAP_RELATIVE = "docs/literature/R2_MANUSCRIPT_COMPARATOR_MAP.json"
    GLOSSARY_RELATIVE = "docs/literature/R2_OPERATIONAL_GLOSSARY.md"
    OUTPUT_RELATIVE = "reports/review_round_2/related_work/v1.1.0"
    REQUIRED_GLOSSARY_TERMS = frozenset(
        {
            "material",
            "biology",
            "protocol",
            "outcome",
            "independent_unit",
            "evidence_locator",
            "ood_group",
        }
    )
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "registry_id",
        "retrieved_at",
        "search_protocol",
        "references",
    }
    REQUIRED_REFERENCE_FIELDS = {
        "citation_key",
        "citation",
        "title",
        "year",
        "source_kind",
        "peer_reviewed",
        "doi",
        "landing_url",
        "roles",
        "use_boundary",
    }
    REQUIRED_MAP_FIELDS = {"schema_version", "map_id", "manuscript_scopes", "comparators"}
    REQUIRED_SCOPE_FIELDS = {
        "scope_id",
        "target_document",
        "position",
        "citation_keys",
        "comparator_ids",
        "required_glossary_terms",
        "claim_constraints",
    }
    REQUIRED_COMPARATOR_FIELDS = {
        "comparator_id",
        "citation_keys",
        "comparison_axis",
        "r2_position",
        "non_equivalence",
    }
    REQUIRED_SCOPE_IDS = frozenset({"R2_PAPER_AB_REAL_BENCHMARK_METHOD", "R2_PAPER_C_PREREGISTERED_PROTOCOL"})

    def __init__(
        self,
        root: Path,
        *,
        registry_path: Path | None = None,
        map_path: Path | None = None,
        glossary_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.map_path = map_path or self.root / self.MAP_RELATIVE
        self.glossary_path = glossary_path or self.root / self.GLOSSARY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RelatedWorkError(f"cannot parse {label}") from exc

    def _relative(self, path: Path, label: str) -> str:
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise RelatedWorkError(f"{label} is missing or outside the repository")
        return resolved.relative_to(self.root).as_posix()

    @staticmethod
    def _string_list(value: Any, label: str, *, minimum: int = 1) -> list[str]:
        raw = _list(value, label)
        if len(raw) < minimum:
            raise RelatedWorkError(f"{label} has too few entries")
        values = [_string(item, label) for item in raw]
        if len(set(values)) != len(values):
            raise RelatedWorkError(f"{label} contains duplicates")
        return values

    def _structured_references(self) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        registry = self._json(self.registry_path, "R2 external-evidence registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise RelatedWorkError("external-evidence registry fields or schema are invalid")
        _string(registry.get("registry_id"), "external-evidence registry ID")
        _string(registry.get("retrieved_at"), "external-evidence retrieval timestamp")
        search_protocol = _mapping(registry.get("search_protocol"), "external-evidence search protocol")
        required_protocol_fields = {
            "question",
            "sources_searched",
            "inclusion",
            "exclusion",
            "limitation",
        }
        if set(search_protocol) != required_protocol_fields:
            raise RelatedWorkError("external-evidence search protocol fields are invalid")
        _string(search_protocol.get("question"), "external-evidence search question")
        _string(search_protocol.get("limitation"), "external-evidence search limitation")
        for field in ("sources_searched", "inclusion", "exclusion"):
            self._string_list(search_protocol.get(field), f"external-evidence protocol {field}")

        raw_references = _list(registry.get("references"), "external-evidence references")
        if len(raw_references) < 12:
            raise RelatedWorkError("external-evidence registry has too few references")
        records: dict[str, dict[str, Any]] = {}
        for value in raw_references:
            reference = _mapping(value, "external-evidence reference")
            if set(reference) != self.REQUIRED_REFERENCE_FIELDS:
                raise RelatedWorkError("external-evidence reference fields are invalid")
            key = _string(reference.get("citation_key"), "external-evidence citation key")
            if key in records:
                raise RelatedWorkError("external-evidence citation key is duplicated")
            for field in ("citation", "title", "source_kind", "landing_url", "use_boundary"):
                _string(reference.get(field), f"external-evidence reference {field}")
            _integer(reference.get("year"), "external-evidence reference year", minimum=1900)
            if reference.get("peer_reviewed") is not True:
                raise RelatedWorkError("external-evidence references must be peer reviewed")
            doi = reference.get("doi")
            if doi is not None and (not isinstance(doi, str) or not doi.startswith("10.")):
                raise RelatedWorkError("external-evidence DOI is invalid")
            if not str(reference["landing_url"]).startswith("https://"):
                raise RelatedWorkError("external-evidence landing URL must use HTTPS")
            self._string_list(reference.get("roles"), "external-evidence reference roles")
            if any(
                token in " ".join(str(reference[field]) for field in ("citation_key", "citation", "title")).lower()
                for token in ("fixture", "synthetic", "mock")
            ):
                raise RelatedWorkError("fixture-like citation entered the external-evidence packet")
            records[key] = reference
        return registry, records

    def _map(
        self, references: dict[str, dict[str, Any]]
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        mapping = self._json(self.map_path, "R2 manuscript comparator map")
        if set(mapping) != self.REQUIRED_MAP_FIELDS or mapping.get("schema_version") != 1:
            raise RelatedWorkError("manuscript comparator-map fields or schema are invalid")
        _string(mapping.get("map_id"), "manuscript comparator-map ID")

        scopes_value = _list(mapping.get("manuscript_scopes"), "manuscript scopes")
        scopes: list[dict[str, Any]] = []
        scope_ids: set[str] = set()
        for value in scopes_value:
            scope = _mapping(value, "manuscript scope")
            if set(scope) != self.REQUIRED_SCOPE_FIELDS:
                raise RelatedWorkError("manuscript scope fields are invalid")
            scope_id = _string(scope.get("scope_id"), "manuscript scope ID")
            if scope_id in scope_ids:
                raise RelatedWorkError("manuscript scope ID is duplicated")
            scope_ids.add(scope_id)
            for field in ("target_document", "position"):
                _string(scope.get(field), f"manuscript scope {field}")
            citation_keys = self._string_list(scope.get("citation_keys"), "manuscript scope citation keys", minimum=6)
            if not set(citation_keys).issubset(references):
                raise RelatedWorkError("manuscript scope cites an unverified external reference")
            required_terms = set(
                self._string_list(scope.get("required_glossary_terms"), "manuscript scope glossary terms")
            )
            if not self.REQUIRED_GLOSSARY_TERMS.issubset(required_terms):
                raise RelatedWorkError("manuscript scope omits a required operational glossary term")
            self._string_list(scope.get("comparator_ids"), "manuscript scope comparator IDs")
            self._string_list(scope.get("claim_constraints"), "manuscript scope claim constraints")
            scopes.append(scope)
        if scope_ids != self.REQUIRED_SCOPE_IDS:
            raise RelatedWorkError("manuscript scopes do not match the R2 portfolio")

        comparator_values = _list(mapping.get("comparators"), "related-work comparators")
        if len(comparator_values) < 8:
            raise RelatedWorkError("related-work packet has too few comparators")
        comparators: list[dict[str, Any]] = []
        comparator_ids: set[str] = set()
        for value in comparator_values:
            comparator = _mapping(value, "related-work comparator")
            if set(comparator) != self.REQUIRED_COMPARATOR_FIELDS:
                raise RelatedWorkError("related-work comparator fields are invalid")
            comparator_id = _string(comparator.get("comparator_id"), "related-work comparator ID")
            if comparator_id in comparator_ids:
                raise RelatedWorkError("related-work comparator ID is duplicated")
            comparator_ids.add(comparator_id)
            citation_keys = self._string_list(comparator.get("citation_keys"), "related-work comparator citation keys")
            if not set(citation_keys).issubset(references):
                raise RelatedWorkError("related-work comparator cites an unverified external reference")
            for field in ("comparison_axis", "r2_position", "non_equivalence"):
                _string(comparator.get(field), f"related-work comparator {field}")
            comparators.append(comparator)
        for scope in scopes:
            scope_comparators = set(self._string_list(scope["comparator_ids"], "manuscript scope comparator IDs"))
            if not scope_comparators.issubset(comparator_ids):
                raise RelatedWorkError("manuscript scope names an unknown comparator")
        used_citations = {
            key
            for scope in scopes
            for key in self._string_list(scope["citation_keys"], "manuscript scope citation keys")
        } | {
            key
            for comparator in comparators
            for key in self._string_list(comparator["citation_keys"], "related-work comparator citation keys")
        }
        if used_citations != set(references):
            raise RelatedWorkError("external-evidence registry has an uncited reference")
        return mapping, scopes, comparators

    def _glossary(self) -> list[str]:
        relative = self._relative(self.glossary_path, "R2 operational glossary")
        try:
            content = self.glossary_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise RelatedWorkError("cannot read R2 operational glossary") from exc
        if not content.startswith("# R2 operational glossary"):
            raise RelatedWorkError("R2 operational glossary heading is invalid")
        terms = {
            "material": "| Material |",
            "biology": "| Biology |",
            "protocol": "| Protocol |",
            "outcome": "| Outcome |",
            "independent_unit": "| Independent unit |",
            "evidence_locator": "| Evidence locator |",
            "ood_group": "| OOD group |",
        }
        missing = [term for term, marker in terms.items() if marker not in content]
        if missing:
            raise RelatedWorkError(f"R2 operational glossary is missing: {', '.join(missing)}")
        if "source_not_stated" not in content or "not convertible by default" not in content:
            raise RelatedWorkError("R2 glossary does not preserve missing-unit comparability boundary")
        if not relative.startswith("docs/literature/"):
            raise RelatedWorkError("R2 operational glossary is outside the reviewed documentation scope")
        return sorted(terms)

    def run(self, *, strict: bool = False) -> RelatedWorkSummary:
        """Create an immutable related-work evidence receipt in strict mode."""

        if not strict:
            raise RelatedWorkError("T125 requires --strict")
        if self.output_root.exists():
            raise RelatedWorkError("related-work audit already executed")
        self._relative(self.registry_path, "R2 external-evidence registry")
        self._relative(self.map_path, "R2 manuscript comparator map")
        registry, references = self._structured_references()
        mapping, scopes, comparators = self._map(references)
        glossary_terms = self._glossary()
        if any(
            not self.REQUIRED_GLOSSARY_TERMS.issubset(
                set(self._string_list(scope["required_glossary_terms"], "scope glossary terms"))
            )
            for scope in scopes
        ):
            raise RelatedWorkError("not every manuscript scope receives all glossary terms")

        self.output_root.mkdir(parents=True, exist_ok=False)
        evidence_path = self.output_root / "external_evidence_manifest.json"
        self._write(
            evidence_path,
            {
                "schema_version": 1,
                "audit_id": self.AUDIT_ID,
                "registry_id": registry["registry_id"],
                "registry_sha256": _sha256(self.registry_path),
                "citation_count": len(references),
                "references": [references[key] for key in sorted(references)],
                "search_protocol": registry["search_protocol"],
            },
        )
        comparator_path = self.output_root / "comparator_matrix.json"
        self._write(
            comparator_path,
            {
                "schema_version": 1,
                "audit_id": self.AUDIT_ID,
                "map_id": mapping["map_id"],
                "map_sha256": _sha256(self.map_path),
                "comparator_count": len(comparators),
                "comparators": sorted(comparators, key=lambda row: str(row["comparator_id"])),
            },
        )
        coverage_path = self.output_root / "manuscript_glossary_coverage.json"
        self._write(
            coverage_path,
            {
                "schema_version": 1,
                "audit_id": self.AUDIT_ID,
                "glossary_relative_path": self._relative(self.glossary_path, "R2 operational glossary"),
                "glossary_sha256": _sha256(self.glossary_path),
                "glossary_terms": glossary_terms,
                "manuscript_scope_count": len(scopes),
                "manuscript_scopes": sorted(scopes, key=lambda row: str(row["scope_id"])),
            },
        )
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "audited_at": self.AUDITED_AT,
            "status": "PASS_RELATED_WORK_EVIDENCE_PACKET",
            "external_evidence_manifest_sha256": _sha256(evidence_path),
            "comparator_matrix_sha256": _sha256(comparator_path),
            "manuscript_glossary_coverage_sha256": _sha256(coverage_path),
            "citation_count": len(references),
            "comparator_count": len(comparators),
            "manuscript_scope_count": len(scopes),
            "glossary_term_count": len(glossary_terms),
            "historical_fixture_manuscripts_retroactively_cleared": False,
            "model_fitted": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
            "claim_boundary": (
                "This packet supplies verified external references, comparator boundaries and "
                "operational definitions for future R2 manuscripts. It does not replace T123, "
                "T124, T126, T127 or T128 evidence."
            ),
        }
        receipt_path = self.output_root / "related_work_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return RelatedWorkSummary(
            citation_count=_integer(receipt["citation_count"], "citation count", minimum=12),
            comparator_count=_integer(receipt["comparator_count"], "comparator count", minimum=8),
            manuscript_scope_count=_integer(receipt["manuscript_scope_count"], "manuscript scope count", minimum=2),
            glossary_term_count=_integer(receipt["glossary_term_count"], "glossary term count", minimum=7),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable related-work outputs without rebuilding them."""

        evidence_path = self.output_root / "external_evidence_manifest.json"
        comparator_path = self.output_root / "comparator_matrix.json"
        coverage_path = self.output_root / "manuscript_glossary_coverage.json"
        receipt_path = self.output_root / "related_work_receipt.json"
        receipt = self._json(receipt_path, "related-work receipt")
        if (
            receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != "PASS_RELATED_WORK_EVIDENCE_PACKET"
            or receipt.get("external_evidence_manifest_sha256") != _sha256(evidence_path)
            or receipt.get("comparator_matrix_sha256") != _sha256(comparator_path)
            or receipt.get("manuscript_glossary_coverage_sha256") != _sha256(coverage_path)
            or _integer(receipt.get("citation_count"), "receipt citation count") < 12
            or _integer(receipt.get("comparator_count"), "receipt comparator count") < 8
            or _integer(receipt.get("manuscript_scope_count"), "receipt manuscript scope count") != 2
            or _integer(receipt.get("glossary_term_count"), "receipt glossary term count") < 7
            or receipt.get("historical_fixture_manuscripts_retroactively_cleared") is not False
            or receipt.get("model_fitted") is not False
            or receipt.get("independent_validation") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise RelatedWorkError("related-work receipt is invalid")
        return receipt
