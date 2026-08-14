"""Link protein-corona modules to response signatures without pseudo-pairing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LinkModalitiesError(RuntimeError):
    """Raised when modality provenance or pairing gates fail."""


@dataclass(frozen=True)
class LinkModalitiesSummary:
    """Summary of a study-preserving modality-link run."""

    links_attempted: int
    direct_links: int
    indirect_links: int
    unmatched_links: int
    candidate_cards: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LinkModalitiesError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LinkModalitiesError(f"{label} must be a non-empty string")
    return value.strip()


class LinkModalitiesWorkflow:
    """Build direct/indirect evidence links with explicit unmatched strata."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/omics/link_modalities_fixture.json")
        self.output_root = output_root or self.root / "reports/omics/modality_links"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LinkModalitiesError(f"cannot load link fixture: {exc}") from exc
        data = _mapping(fixture, "link fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "link_modalities":
            raise LinkModalitiesError("link fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not data["inputs"]:
            raise LinkModalitiesError("link fixture has no inputs")
        if not isinstance(data.get("links"), list) or not data["links"]:
            raise LinkModalitiesError("link fixture has no links")
        return data

    def _read_input(self, value: Any) -> tuple[str, dict[str, Any] | str]:
        row = _mapping(value, "link input")
        label = _string(row.get("label"), "input label")
        relative = _string(row.get("path"), "input path")
        path = (self.root / relative).resolve(strict=True)
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise LinkModalitiesError("link input escaped repository") from exc
        expected = _string(row.get("sha256"), "input checksum")
        if _sha256(path.read_bytes()) != expected:
            raise LinkModalitiesError(f"link input checksum differs: {label}")
        if path.suffix == ".json":
            try:
                return label, _mapping(json.loads(path.read_text(encoding="utf-8")), label)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise LinkModalitiesError(f"cannot load link input {label}: {exc}") from exc
        return label, path.read_text(encoding="utf-8")

    def _load_inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any] | str]:
        inputs: dict[str, dict[str, Any] | str] = {}
        for value in fixture["inputs"]:
            label, payload = self._read_input(value)
            if label in inputs:
                raise LinkModalitiesError(f"duplicate link input: {label}")
            inputs[label] = payload
        required = {
            "T056 module matrix",
            "T056 mapping audit",
            "T061 signature scores",
            "T061 signature registry",
            "T047 silver evidence",
        }
        if set(inputs) != required:
            raise LinkModalitiesError("link inputs do not match T047/T056/T061 contract")
        return inputs

    @staticmethod
    def _module_index(payload: dict[str, Any] | str) -> dict[tuple[str, str], dict[str, Any]]:
        if not isinstance(payload, dict):
            raise LinkModalitiesError("module matrix must be JSON")
        rows = payload.get("rows")
        if not isinstance(rows, list) or not rows:
            raise LinkModalitiesError("module matrix has no rows")
        index: dict[tuple[str, str], dict[str, Any]] = {}
        for value in rows:
            row = _mapping(value, "module row")
            key = (
                _string(row.get("project_accession"), "module project"),
                _string(row.get("sample_id"), "module sample"),
            )
            index[key] = row
        return index

    @staticmethod
    def _signature_index(
        payload: dict[str, Any] | str,
    ) -> dict[tuple[str, str, str], dict[str, Any]]:
        if not isinstance(payload, dict):
            raise LinkModalitiesError("signature scores must be JSON")
        rows = payload.get("scores")
        if not isinstance(rows, list) or not rows:
            raise LinkModalitiesError("signature scores have no rows")
        index: dict[tuple[str, str, str], dict[str, Any]] = {}
        for value in rows:
            row = _mapping(value, "signature score row")
            key = (
                _string(row.get("study_accession"), "signature study"),
                _string(row.get("sample_id"), "signature sample"),
                _string(row.get("signature_id"), "signature ID"),
            )
            index[key] = row
        return index

    @staticmethod
    def _signature_registry(payload: dict[str, Any] | str) -> set[str]:
        if not isinstance(payload, dict):
            raise LinkModalitiesError("signature registry must be JSON")
        rows = payload.get("signatures")
        if not isinstance(rows, list):
            raise LinkModalitiesError("signature registry has no signatures")
        return {_string(_mapping(value, "signature definition").get("signature_id"), "signature ID") for value in rows}

    def run(self, *, fixture: bool = True) -> LinkModalitiesSummary:
        """Validate and emit direct/indirect/unmatched modality links."""
        if not fixture:
            raise LinkModalitiesError("--fixture is required for modality linking")
        fixture_data = self._load_fixture()
        inputs = self._load_inputs(fixture_data)
        module_index = self._module_index(inputs["T056 module matrix"])
        signature_index = self._signature_index(inputs["T061 signature scores"])
        signature_ids = self._signature_registry(inputs["T061 signature registry"])
        links: list[dict[str, Any]] = []
        exclusions: list[dict[str, Any]] = []
        for value in fixture_data["links"]:
            link = _mapping(value, "modality link")
            link_id = _string(link.get("link_id"), "link ID")
            link_class = _string(link.get("link_class"), "link class")
            module_project = _string(link.get("module_project"), "module project")
            module_id = _string(link.get("module_id"), "module ID")
            module_sample_ids = link.get("module_sample_ids")
            response_study = _string(link.get("response_study"), "response study")
            signature_id = _string(link.get("signature_id"), "signature ID")
            response_sample_ids = link.get("response_sample_ids")
            if not isinstance(module_sample_ids, list) or not isinstance(response_sample_ids, list):
                raise LinkModalitiesError(f"link sample IDs are invalid: {link_id}")
            module_samples = [_string(item, "module sample") for item in module_sample_ids]
            response_samples = [_string(item, "response sample") for item in response_sample_ids]
            if signature_id not in signature_ids:
                raise LinkModalitiesError(f"unknown signature in link: {link_id}")
            module_rows = []
            for sample_id in module_samples:
                row = module_index.get((module_project, sample_id))
                if row is None:
                    raise LinkModalitiesError(f"unknown module sample in link: {link_id}")
                module_rows.append(row)
            score_rows = []
            for sample_id in response_samples:
                row = signature_index.get((response_study, sample_id, signature_id))
                if row is None:
                    raise LinkModalitiesError(f"unknown response sample in link: {link_id}")
                score_rows.append(row)
            if link_class == "direct_matched":
                matched_unit = _string(link.get("matched_unit_id"), "matched unit")
                match_basis = _string(link.get("match_basis"), "match basis")
                evidence_locator = _string(link.get("evidence_locator"), "direct evidence locator")
                if not response_samples or not module_samples:
                    raise LinkModalitiesError(f"direct link lacks sample IDs: {link_id}")
                status = "DIRECT_CANDIDATE"
                delta = None
                if len(module_rows) >= 2:
                    delta = round(
                        module_rows[-1]["module_values"][module_id] - module_rows[0]["module_values"][module_id],
                        8,
                    )
                response_delta = None
                if len(score_rows) >= 2:
                    response_delta = round(score_rows[-1]["score"] - score_rows[0]["score"], 8)
                link_record = {
                    "link_id": link_id,
                    "link_class": link_class,
                    "status": status,
                    "module_project": module_project,
                    "module_id": module_id,
                    "module_sample_ids": module_samples,
                    "response_study": response_study,
                    "signature_id": signature_id,
                    "response_sample_ids": response_samples,
                    "matched_unit_id": matched_unit,
                    "match_basis": match_basis,
                    "evidence_locator": evidence_locator,
                    "module_delta": delta,
                    "signature_delta_first_to_last": response_delta,
                    "confidence": _string(link.get("confidence"), "link confidence"),
                    "candidate_mechanism": _string(link.get("candidate_mechanism"), "candidate mechanism"),
                    "causal_claim": False,
                }
            elif link_class == "indirect_literature":
                evidence_locator = _string(link.get("evidence_locator"), "indirect evidence locator")
                if response_samples or link.get("matched_unit_id") is not None:
                    raise LinkModalitiesError(f"indirect link contains pseudo-pairing: {link_id}")
                link_record = {
                    "link_id": link_id,
                    "link_class": link_class,
                    "status": "INDIRECT_CANDIDATE",
                    "module_project": module_project,
                    "module_id": module_id,
                    "module_sample_ids": module_samples,
                    "response_study": response_study,
                    "signature_id": signature_id,
                    "response_sample_ids": [],
                    "matched_unit_id": None,
                    "match_basis": None,
                    "evidence_locator": evidence_locator,
                    "confidence": _string(link.get("confidence"), "link confidence"),
                    "candidate_mechanism": _string(link.get("candidate_mechanism"), "candidate mechanism"),
                    "causal_claim": False,
                }
            elif link_class == "unmatched":
                reason = _string(link.get("exclusion_reason"), "exclusion reason")
                if response_samples or link.get("matched_unit_id") is not None:
                    raise LinkModalitiesError(f"unmatched link contains pairing: {link_id}")
                exclusions.append(
                    {
                        "link_id": link_id,
                        "link_class": link_class,
                        "module_project": module_project,
                        "module_id": module_id,
                        "response_study": response_study,
                        "signature_id": signature_id,
                        "reason": reason,
                    }
                )
                continue
            else:
                raise LinkModalitiesError(f"unsupported link class: {link_class}")
            links.append(link_record)

        direct = [row for row in links if row["link_class"] == "direct_matched"]
        indirect = [row for row in links if row["link_class"] == "indirect_literature"]
        cards = [
            {
                "card_id": f"CARD-{row['link_id']}",
                "link_id": row["link_id"],
                "claim_level": "candidate_mechanism",
                "link_class": row["link_class"],
                "module": f"{row['module_project']}:{row['module_id']}",
                "response": f"{row['response_study']}:{row['signature_id']}",
                "evidence_locator": row["evidence_locator"],
                "causal_claim": False,
                "wording": row["candidate_mechanism"],
            }
            for row in links
        ]
        pairing = {
            "schema_version": 1,
            "direct_links_require_declared_matched_unit": True,
            "indirect_links_have_no_response_sample_ids": all(not row["response_sample_ids"] for row in indirect),
            "pseudo_pairs_created": False,
            "cross_study_expression_batch_merge": False,
            "direct_matched_units": [row["matched_unit_id"] for row in direct],
            "unmatched_exclusions": len(exclusions),
            "status": "PASSED",
        }
        raw_payloads = {
            "links": {"schema_version": 1, "links": links},
            "direct": {"schema_version": 1, "links": direct},
            "indirect": {"schema_version": 1, "links": indirect},
            "cards": {"schema_version": 1, "cards": cards},
            "pairing": pairing,
            "exclusions": {"schema_version": 1, "append_only": True, "entries": exclusions},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "links": self.output_root / "link_graph.json",
            "direct": self.output_root / "direct_strata.json",
            "indirect": self.output_root / "indirect_strata.json",
            "cards": self.output_root / "candidate_mechanism_cards.json",
            "pairing": self.output_root / "pairing_audit.json",
            "exclusions": self.output_root / "exclusion_ledger.json",
            "receipt": self.output_root / "processing_receipt.json",
            "log": self.output_root / "processing_log.json",
            "manifest": self.output_root / "processing_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "fixture": True,
            "links_attempted": len(fixture_data["links"]),
            "direct_links": len(direct),
            "indirect_links": len(indirect),
            "unmatched_links": len(exclusions),
            "candidate_cards": len(cards),
            "pseudo_pairs_created": False,
            "cross_study_expression_batch_merge": False,
            "real_network_accessed": False,
            "locked_payload_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T056_T061_inputs_verified", "links": len(fixture_data["links"])},
                {"event": "direct_matched_links_retained", "count": len(direct)},
                {"event": "indirect_literature_links_retained", "count": len(indirect)},
                {"event": "unmatched_pairs_excluded", "count": len(exclusions)},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "links_attempted": len(fixture_data["links"]),
            "direct_links": len(direct),
            "indirect_links": len(indirect),
            "unmatched_links": len(exclusions),
            "candidate_cards": len(cards),
            "pseudo_pairs_created": False,
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                    "sha256": _sha256(payload_bytes[name]),
                    "bytes": len(payload_bytes[name]),
                }
                for name, path in paths.items()
                if name in payload_bytes
            },
        }
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise LinkModalitiesError("existing modality-link receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise LinkModalitiesError(f"existing modality-link artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return LinkModalitiesSummary(
            links_attempted=len(fixture_data["links"]),
            direct_links=len(direct),
            indirect_links=len(indirect),
            unmatched_links=len(exclusions),
            candidate_cards=len(cards),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
