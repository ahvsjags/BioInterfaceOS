"""Profile acquired T123 author results without freezing a predictive target.

The three sources use distinct instruments and author-result formats.  This
workflow extracts only a conservative *detection-set* representation from each
selected result file.  It deliberately does not merge abundance values, infer
unknown PXD052701 covariates, or convert PXD032162's combined result into TMT
mix-level observations.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sqlite3
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import iterparse

from biointerfaceos.real_proteomics_acquisition import RealProteomicsAcquisitionWorkflow


class RealProteomicsResultProfileError(RuntimeError):
    """Raised when acquired author results cannot be profiled safely."""


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealProteomicsResultProfileError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealProteomicsResultProfileError(f"{label} must be a non-empty string")
    return value.strip()


_UNIPROT_DESCRIPTION = re.compile(r"(?:^|>)\w{2}\|([A-Z0-9]{6,10})\|")
_UNIPROT_ACCESSION = re.compile(r"^([A-Z0-9]{6,10})(?:\||$)")


def _canonical_accession(value: str) -> str | None:
    """Return a conservatively parsed canonical-looking UniProt accession."""

    candidate = value.strip().upper()
    description_match = _UNIPROT_DESCRIPTION.search(candidate)
    if description_match is not None:
        return description_match.group(1)
    accession_match = _UNIPROT_ACCESSION.match(candidate)
    return accession_match.group(1) if accession_match is not None else None


@dataclass(frozen=True)
class ResultProfile:
    """One source result file represented only by protein detection evidence."""

    source_id: str
    source_result_id: str
    format: str
    file_relative_path: str
    file_sha256: str
    author_result_unit: str
    declared_source_unit_count: int
    profile_resolution: str
    spectrum_or_row_count: int
    detected_accessions: tuple[str, ...]
    unparseable_accession_count: int
    covariate_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_result_id": self.source_result_id,
            "format": self.format,
            "file_relative_path": self.file_relative_path,
            "file_sha256": self.file_sha256,
            "author_result_unit": self.author_result_unit,
            "declared_source_unit_count": self.declared_source_unit_count,
            "profile_resolution": self.profile_resolution,
            "spectrum_or_row_count": self.spectrum_or_row_count,
            "detected_protein_count": len(self.detected_accessions),
            "detected_accessions": list(self.detected_accessions),
            "unparseable_accession_count": self.unparseable_accession_count,
            "covariate_status": self.covariate_status,
        }


@dataclass(frozen=True)
class RealProteomicsResultProfileSummary:
    """Compact output accounting for one non-model profile run."""

    source_count: int
    source_result_count: int
    receipt_path: Path


class RealProteomicsResultProfileWorkflow:
    """Fail closed when source-result profiling would be mistaken for a model target."""

    AUDIT_ID = "bioif-r2-real-proteomics-result-profile-v1.0.0"
    RAW_RELATIVE = "data/raw/r2_t123_proteomics"
    OUTPUT_RELATIVE = "reports/review_round_2/real_proteomics_result_profile/v1.0.0"
    ACQUISITION_RELATIVE = (
        "reports/review_round_2/real_proteomics_acquisition/v1.0.0/"
        "acquisition_receipt.json"
    )
    PXD017_PREFIX = "PXD017776/author_results"
    PXD052_PREFIX = "PXD052701/author_results"
    PXD032_MZID = "PXD032162/author_results/Proteinkorona_Nanoplastik_static.mzid.gz"
    PXD017_FILES = (
        "dopc_chol_cleancorona_1_PXD.mzID.gz",
        "dopc_chol_cleancorona_2_PXD.mzID.gz",
        "dopc_chol_cleancorona_3_PXD.mzID.gz",
        "dopcg_chol_cleancorona_1_PXD.mzID.gz",
        "dopcg_chol_cleancorona_2_PXD.mzID.gz",
        "dopcg_chol_cleancorona_3_PXD.mzID.gz",
        "dopg_chol_cleancorona_1_PXD.mzID.gz",
        "dopg_chol_cleancorona_2_PXD.mzID.gz",
        "dopg_chol_cleancorona_3_PXD.mzID.gz",
        "hs_1_PXD.mzID.gz",
        "hs_2_PXD.mzID.gz",
        "hs_3_PXD.mzID.gz",
    )
    PXD052_FILES = (
        "LF1-L.msf",
        "LF1-S.msf",
        "LF2-L.msf",
        "LF2-S.msf",
        "LF3-L.msf",
        "LF3-S.msf",
        "LF4-L.msf",
        "LF4-S.msf",
        "LF5-L.msf",
        "LF5-S.msf",
    )

    def __init__(
        self,
        root: Path,
        *,
        raw_root: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.raw_root = raw_root or self.root / self.RAW_RELATIVE
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
            raise RealProteomicsResultProfileError(f"cannot parse {label}") from exc

    def _path(self, relative: str) -> Path:
        path = (self.raw_root / relative).resolve(strict=False)
        raw_root = self.raw_root.resolve(strict=False)
        if raw_root not in path.parents or not path.is_file():
            raise RealProteomicsResultProfileError(
                f"required acquired result is missing: {relative}"
            )
        return path

    @staticmethod
    def _xml_local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    @classmethod
    def _mzidentml_profile(cls, path: Path) -> tuple[tuple[str, ...], int, int]:
        """Use passed peptide-evidence links; never count all database entries."""

        database_sequences: dict[str, str] = {}
        evidence_to_database: dict[str, str] = {}
        detected_database_ids: set[str] = set()
        spectrum_count = 0
        try:
            with gzip.open(path, "rb") as stream:
                for _, element in iterparse(stream, events=("end",)):
                    tag = cls._xml_local_name(element.tag)
                    if tag == "DBSequence":
                        identifier = element.attrib.get("id")
                        accession = element.attrib.get("accession")
                        if identifier and accession:
                            database_sequences[identifier] = accession
                        element.clear()
                    elif tag == "PeptideEvidence":
                        identifier = element.attrib.get("id")
                        database_id = element.attrib.get("dBSequence_ref")
                        if identifier and database_id:
                            evidence_to_database[identifier] = database_id
                        element.clear()
                    elif tag == "SpectrumIdentificationItem":
                        if element.attrib.get("passThreshold", "").lower() == "true":
                            for reference in element.findall("{*}PeptideEvidenceRef"):
                                evidence_id = reference.attrib.get("peptideEvidence_ref")
                                database_id = (
                                    evidence_to_database.get(evidence_id)
                                    if evidence_id is not None
                                    else None
                                )
                                if database_id is not None:
                                    detected_database_ids.add(database_id)
                        element.clear()
                    elif tag == "SpectrumIdentificationResult":
                        spectrum_count += 1
                        element.clear()
                    elif tag not in {"PeptideEvidenceRef", "SpectrumIdentificationItem"}:
                        element.clear()
        except (OSError, ValueError) as exc:
            raise RealProteomicsResultProfileError(
                f"cannot parse mzIdentML result: {path}"
            ) from exc
        accessions: set[str] = set()
        unparseable = 0
        for database_id in detected_database_ids:
            raw_accession = database_sequences.get(database_id)
            canonical = _canonical_accession(raw_accession) if raw_accession is not None else None
            if canonical is None:
                unparseable += 1
            else:
                accessions.add(canonical)
        if not accessions or spectrum_count == 0:
            raise RealProteomicsResultProfileError(
                f"mzIdentML profile has no passed canonical protein evidence: {path}"
            )
        return tuple(sorted(accessions)), spectrum_count, unparseable

    @staticmethod
    def _msf_profile(path: Path) -> tuple[tuple[str, ...], int, int]:
        """Read author target rows only; no author score is used as an abundance value."""

        try:
            connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
            try:
                rows = connection.execute(
                    "SELECT DISTINCT annotation.Description "
                    "FROM ProteinAnnotations AS annotation "
                    "JOIN ProteinScores AS score ON score.ProteinID = annotation.ProteinID"
                ).fetchall()
            finally:
                connection.close()
        except sqlite3.Error as exc:
            raise RealProteomicsResultProfileError(f"cannot read MSF result: {path}") from exc
        accessions: set[str] = set()
        unparseable = 0
        for (description,) in rows:
            canonical = _canonical_accession(str(description))
            if canonical is None:
                unparseable += 1
            else:
                accessions.add(canonical)
        if not accessions:
            raise RealProteomicsResultProfileError(
                f"MSF profile has no canonical target protein evidence: {path}"
            )
        return tuple(sorted(accessions)), len(rows), unparseable

    def _profiles(self) -> tuple[ResultProfile, ...]:
        profiles: list[ResultProfile] = []
        for file_name in self.PXD017_FILES:
            relative = f"{self.PXD017_PREFIX}/{file_name}"
            path = self._path(relative)
            accessions, spectra, unparseable = self._mzidentml_profile(path)
            profiles.append(
                ResultProfile(
                    source_id="PRIDE-PXD017776",
                    source_result_id=file_name.removesuffix("_PXD.mzID.gz"),
                    format="MZIDENTML_1_1_GZIP",
                    file_relative_path=relative,
                    file_sha256=_sha256(path),
                    author_result_unit="SOURCE_NAMED_PROTEOMICS_RUN",
                    declared_source_unit_count=1,
                    profile_resolution="RUN_LEVEL_DETECTION_SET",
                    spectrum_or_row_count=spectra,
                    detected_accessions=accessions,
                    unparseable_accession_count=unparseable,
                    covariate_status="SOURCE_NAMED_ARMS_ONLY_NOT_NUMERIC_MATERIAL_COVARIATES",
                )
            )
        for file_name in self.PXD052_FILES:
            relative = f"{self.PXD052_PREFIX}/{file_name}"
            path = self._path(relative)
            accessions, rows, unparseable = self._msf_profile(path)
            profiles.append(
                ResultProfile(
                    source_id="PRIDE-PXD052701",
                    source_result_id=file_name.removesuffix(".msf"),
                    format="PROTEOME_DISCOVERER_MSF",
                    file_relative_path=relative,
                    file_sha256=_sha256(path),
                    author_result_unit="SOURCE_NAMED_SEARCH_RESULT_RUN",
                    declared_source_unit_count=1,
                    profile_resolution="RUN_LEVEL_AUTHOR_TARGET_PROTEIN_SET",
                    spectrum_or_row_count=rows,
                    detected_accessions=accessions,
                    unparseable_accession_count=unparseable,
                    covariate_status="UNRESOLVED_L_S_LABELS_NO_SOURCE_MATCHED_REUSABLE_MAP",
                )
            )
        pxd032_path = self._path(self.PXD032_MZID)
        accessions, spectra, unparseable = self._mzidentml_profile(pxd032_path)
        profiles.append(
            ResultProfile(
                source_id="PRIDE-PXD032162",
                source_result_id="Proteinkorona_Nanoplastik_static",
                format="MZIDENTML_1_1_GZIP",
                file_relative_path=self.PXD032_MZID,
                file_sha256=_sha256(pxd032_path),
                author_result_unit="COMBINED_STATIC_MZIDENTML_RESULT",
                declared_source_unit_count=8,
                profile_resolution="SOURCE_LEVEL_ONLY_NOT_TMT_MIX_LEVEL",
                spectrum_or_row_count=spectra,
                detected_accessions=accessions,
                unparseable_accession_count=unparseable,
                covariate_status="PS_PVC_AND_TIMEPOINT_CODES_EXIST_BUT_CANNOT_BE_LINKED_TO_COMBINED_PROTEIN_SET",
            )
        )
        return tuple(profiles)

    @staticmethod
    def _source_summary(profiles: Iterable[ResultProfile]) -> list[dict[str, Any]]:
        grouped: dict[str, list[ResultProfile]] = {}
        for profile in profiles:
            grouped.setdefault(profile.source_id, []).append(profile)
        summary: list[dict[str, Any]] = []
        for source_id, source_profiles in sorted(grouped.items()):
            union = set().union(*(set(profile.detected_accessions) for profile in source_profiles))
            intersection = set(source_profiles[0].detected_accessions)
            for profile in source_profiles[1:]:
                intersection.intersection_update(profile.detected_accessions)
            summary.append(
                {
                    "source_id": source_id,
                    "profile_count": len(source_profiles),
                    "profile_resolution": sorted(
                        {profile.profile_resolution for profile in source_profiles}
                    ),
                    "detected_accession_union_count": len(union),
                    "detected_accession_within_source_intersection_count": len(intersection),
                    "covariate_statuses": sorted(
                        {profile.covariate_status for profile in source_profiles}
                    ),
                }
            )
        return summary

    def run(self, *, strict: bool = False) -> RealProteomicsResultProfileSummary:
        """Create one immutable real-result profile that remains non-predictive."""

        if not strict:
            raise RealProteomicsResultProfileError("proteomics result profile requires --strict")
        if self.output_root.exists():
            raise RealProteomicsResultProfileError("proteomics result profile already executed")
        acquisition = RealProteomicsAcquisitionWorkflow(self.root)
        acquisition_receipt = acquisition.verify()
        if acquisition_receipt.get("status") != "STAGED_REAL_AUTHOR_RESULTS_NOT_A_MODEL_TARGET":
            raise RealProteomicsResultProfileError("acquisition state is not safe for profiling")
        profiles = self._profiles()
        if len(profiles) != 23 or {profile.source_id for profile in profiles} != {
            "PRIDE-PXD017776",
            "PRIDE-PXD052701",
            "PRIDE-PXD032162",
        }:
            raise RealProteomicsResultProfileError("result profile cohort is incomplete")
        source_summary = self._source_summary(profiles)
        profile_accessions = [set(profile.detected_accessions) for profile in profiles]
        all_profile_intersection = set.intersection(*profile_accessions)
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "acquisition_receipt_sha256": _sha256(self.root / self.ACQUISITION_RELATIVE),
            "acquisition_status": acquisition_receipt["status"],
            "endpoint_representation": "AUTHOR_RESULT_SUPPORTED_CANONICAL_PROTEIN_DETECTION_SET",
            "author_abundance_values_concatenated": False,
            "profile_count": len(profiles),
            "source_count": len(source_summary),
            "source_summaries": source_summary,
            "all_profile_detection_intersection_count": len(all_profile_intersection),
            "profiles": [profile.as_dict() for profile in profiles],
            "status": "REAL_RESULT_PROFILE_COMPLETE_NOT_A_MODEL_TARGET",
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "compatible_cross_study_target_count": 0,
            "blocked_reasons": [
                "PXD052701 L/S labels lack a source-matched reusable material/size "
                "covariate map.",
                "PXD032162's acquired mzIdentML is one combined result and cannot "
                "support mix-level protein observations.",
                "The result formats define detection sets only; no common abundance "
                "endpoint or study-held-out predictive feature space is frozen.",
            ],
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "result_profile_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": decision["status"],
            "result_profile_decision_sha256": _sha256(decision_path),
            "profile_count": len(profiles),
            "source_count": len(source_summary),
            "compatible_cross_study_target_count": 0,
            "target_status": "NOT_FROZEN",
            "model_use": "PROHIBITED",
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "result_profile_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(
            stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )
        return RealProteomicsResultProfileSummary(
            source_count=len(source_summary),
            source_result_count=len(profiles),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable non-model profile receipt and required boundaries."""

        decision_path = self.output_root / "result_profile_decision.json"
        receipt_path = self.output_root / "result_profile_receipt.json"
        decision = self._json(decision_path, "proteomics result profile decision")
        receipt = self._json(receipt_path, "proteomics result profile receipt")
        required_false = (
            "model_fitted",
            "paired_ablations_run",
            "external_ood_evaluated",
            "negative_controls_run",
            "independent_validation",
            "scientific_submission_ready",
        )
        if (
            receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != "REAL_RESULT_PROFILE_COMPLETE_NOT_A_MODEL_TARGET"
            or decision.get("status") != receipt["status"]
            or receipt.get("result_profile_decision_sha256") != _sha256(decision_path)
            or receipt.get("profile_count") != 23
            or receipt.get("source_count") != 3
            or receipt.get("compatible_cross_study_target_count") != 0
            or receipt.get("target_status") != "NOT_FROZEN"
            or receipt.get("model_use") != "PROHIBITED"
            or decision.get("author_abundance_values_concatenated") is not False
            or decision.get("compatible_cross_study_target_count") != 0
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise RealProteomicsResultProfileError("proteomics result profile receipt is invalid")
        return receipt
