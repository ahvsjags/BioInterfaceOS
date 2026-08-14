"""Deterministic, fixture-backed Sage-style proteomics search workflow."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class SageSearchError(RuntimeError):
    """Raised when a bounded Sage search fixture is invalid or unsafe."""


@dataclass(frozen=True)
class SageSearchSummary:
    """Summary of one deterministic search run."""

    psm_rows: int
    accepted_psms: int
    accepted_peptides: int
    accepted_proteins: int
    target_psms: int
    decoy_psms: int
    estimated_fdr: float
    recovered_spike_ins: int
    total_spike_ins: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SageSearchError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SageSearchError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SageSearchError(f"{label} must be a string list")
    return [item.strip() for item in value]


def _float(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise SageSearchError(f"{label} must be numeric")
    return float(value)


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SageSearchError(f"{label} must be an integer")
    return cast(int, value)


class SageSearchWorkflow:
    """Run a bounded search over the frozen T053 mzML artifact."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/omics/search_fixture.json"
        self.output_root = output_root or self.root / "reports/omics/search"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SageSearchError(f"cannot load search fixture: {exc}") from exc
        data = _mapping(fixture, "search fixture")
        if data.get("schema_version") != 1:
            raise SageSearchError("search fixture schema_version must be 1")
        for key in ("config", "input", "database", "candidates", "spike_ins"):
            if key not in data:
                raise SageSearchError(f"search fixture missing {key}")
        if not isinstance(data["candidates"], list) or not isinstance(data["spike_ins"], list):
            raise SageSearchError("candidates and spike_ins must be lists")
        return data

    def _verify_input(self, data: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
        input_data = _mapping(data["input"], "input")
        relative = _string(input_data.get("artifact_path"), "input.artifact_path")
        artifact = (self.root / relative).resolve(strict=True)
        try:
            artifact.relative_to(self.root)
        except ValueError as exc:
            raise SageSearchError("input artifact must remain inside repository root") from exc
        declared_sha = _string(input_data.get("artifact_sha256"), "input.artifact_sha256")
        actual_sha = _sha256_path(artifact)
        if actual_sha != declared_sha:
            raise SageSearchError("input artifact checksum differs from declared checksum")
        try:
            tree = ET.parse(artifact)
        except (ET.ParseError, OSError) as exc:
            raise SageSearchError(f"input artifact is not valid XML: {exc}") from exc
        root_tag = tree.getroot().tag.rsplit("}", 1)[-1]
        if root_tag != "mzML":
            raise SageSearchError("input artifact root is not mzML")
        spectrum_count = sum(1 for element in tree.iter() if element.tag.rsplit("}", 1)[-1] == "spectrum")
        input_record = {
            "artifact_path": relative,
            "artifact_sha256": actual_sha,
            "project_accession": _string(input_data.get("project_accession"), "input.project_accession"),
            "spectrum_count": spectrum_count,
        }
        self._verify_conversion_receipt(input_record)
        return input_record, spectrum_count

    def _verify_conversion_receipt(self, input_record: Mapping[str, Any]) -> None:
        manifest_path = self.root / "reports/omics/conversion/conversion_manifest.json"
        try:
            manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")), "conversion")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SageSearchError(f"cannot load T053 conversion manifest: {exc}") from exc
        rows = manifest.get("receipt_rows")
        if not isinstance(rows, list):
            raise SageSearchError("T053 conversion manifest has no receipt rows")
        matches = [
            _mapping(row, "conversion row")
            for row in rows
            if isinstance(row, Mapping) and row.get("project_accession") == input_record["project_accession"]
        ]
        if len(matches) != 1:
            raise SageSearchError("T053 conversion manifest has no unique completed input")
        row = matches[0]
        if row.get("status") != "COMPLETED" or row.get("output_sha256") != input_record["artifact_sha256"]:
            raise SageSearchError("T053 conversion receipt does not verify the search input")

    def _load_config(self, data: Mapping[str, Any]) -> dict[str, Any]:
        config = _mapping(data["config"], "config")
        if _string(config.get("engine"), "config.engine") != "Sage":
            raise SageSearchError("fixture engine must be Sage")
        _string(config.get("engine_version"), "config.engine_version")
        for key in ("precursor_tolerance_ppm", "fragment_tolerance_ppm"):
            if _float(config.get(key), f"config.{key}") <= 0:
                raise SageSearchError(f"config.{key} must be positive")
        if _string(config.get("enzyme"), "config.enzyme") != "trypsin":
            raise SageSearchError("fixture enzyme must be trypsin")
        if _int(config.get("missed_cleavages"), "config.missed_cleavages") < 0:
            raise SageSearchError("config.missed_cleavages cannot be negative")
        config["fixed_modifications"] = _string_list(config.get("fixed_modifications"), "config.fixed_modifications")
        config["variable_modifications"] = _string_list(
            config.get("variable_modifications"), "config.variable_modifications"
        )
        fdr_level = _float(config.get("fdr_level"), "config.fdr_level")
        if not 0 < fdr_level <= 1:
            raise SageSearchError("config.fdr_level must be in (0, 1]")
        target_decoy = _mapping(config.get("target_decoy"), "config.target_decoy")
        if _string(target_decoy.get("method"), "config.target_decoy.method") != "reverse":
            raise SageSearchError("target-decoy method must be reverse")
        _string(target_decoy.get("decoy_prefix"), "config.target_decoy.decoy_prefix")
        config["target_decoy"] = target_decoy
        config["database_version"] = _string(config.get("database_version"), "config.database_version")
        return config

    def _load_database(
        self, data: Mapping[str, Any], config: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        database = _mapping(data["database"], "database")
        version = _string(database.get("version"), "database.version")
        if version != config["database_version"]:
            raise SageSearchError("database version differs from search config")
        organism = _string(database.get("organism"), "database.organism")
        sequences_value = database.get("sequences")
        if not isinstance(sequences_value, list) or not sequences_value:
            raise SageSearchError("database.sequences must be non-empty")
        targets: dict[str, str] = {}
        for item in sequences_value:
            sequence_record = _mapping(item, "database sequence")
            accession = _string(sequence_record.get("accession"), "database accession")
            sequence = _string(sequence_record.get("sequence"), f"database sequence {accession}")
            if accession.startswith("DECOY_") or accession in targets:
                raise SageSearchError("database target accessions must be unique and non-decoy")
            targets[accession] = sequence
        fasta_relative = _string(database.get("fasta_path"), "database.fasta_path")
        fasta_path = (self.root / fasta_relative).resolve(strict=True)
        try:
            fasta_path.relative_to(self.root)
        except ValueError as exc:
            raise SageSearchError("database FASTA must remain inside repository root") from exc
        declared_fasta_sha = _string(database.get("fasta_sha256"), "database.fasta_sha256")
        actual_fasta_sha = _sha256_path(fasta_path)
        if actual_fasta_sha != declared_fasta_sha:
            raise SageSearchError("database FASTA checksum differs from declared checksum")
        fasta_targets: dict[str, str] = {}
        current_accession: str | None = None
        sequence_parts: list[str] = []
        for line in fasta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(">"):
                if current_accession is not None:
                    fasta_targets[current_accession] = "".join(sequence_parts)
                header = line[1:].strip().split()[0]
                current_accession = header.split("|")[1] if "|" in header else header
                sequence_parts = []
            elif line.strip():
                if current_accession is None:
                    raise SageSearchError("database FASTA sequence precedes a header")
                sequence_parts.append(line.strip())
        if current_accession is not None:
            fasta_targets[current_accession] = "".join(sequence_parts)
        if fasta_targets != targets:
            raise SageSearchError("database FASTA does not match declared target sequences")
        decoy_prefix = _string(
            _mapping(config["target_decoy"], "target-decoy").get("decoy_prefix"),
            "target-decoy prefix",
        )
        decoys = {f"{decoy_prefix}{key}": value[::-1] for key, value in targets.items()}
        database_record = {
            "organism": organism,
            "version": version,
            "target_count": len(targets),
            "decoy_count": len(decoys),
            "fasta_path": fasta_relative,
            "fasta_sha256": actual_fasta_sha,
            "target_decoy_method": "reverse",
            "decoy_prefix": decoy_prefix,
        }
        database_sha = _sha256_bytes(_canonical(database))
        database_record["database_sha256"] = database_sha
        combined = dict(targets)
        combined.update(decoys)
        return database_record, combined

    def _build_psms(
        self,
        data: Mapping[str, Any],
        config: Mapping[str, Any],
        sequences: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        candidates = cast(list[Any], data["candidates"])
        prefix = _string(
            _mapping(config["target_decoy"], "target-decoy").get("decoy_prefix"),
            "target-decoy prefix",
        )
        rows: list[dict[str, Any]] = []
        seen_spectra: set[str] = set()
        for candidate_value in candidates:
            candidate = _mapping(candidate_value, "PSM candidate")
            spectrum_id = _string(candidate.get("spectrum_id"), "PSM spectrum_id")
            if spectrum_id in seen_spectra:
                raise SageSearchError(f"duplicate PSM spectrum_id: {spectrum_id}")
            seen_spectra.add(spectrum_id)
            peptide = _string(candidate.get("peptide"), "PSM peptide")
            protein = _string(candidate.get("protein_accession"), "PSM protein_accession")
            score = _float(candidate.get("score"), "PSM score")
            if score < 0:
                raise SageSearchError("PSM score cannot be negative")
            label = _string(candidate.get("target_decoy"), "PSM target_decoy").lower()
            expected_prefix = prefix if label == "decoy" else ""
            if label not in {"target", "decoy"}:
                raise SageSearchError("PSM target_decoy must be target or decoy")
            if expected_prefix and not protein.startswith(expected_prefix):
                raise SageSearchError("decoy PSM protein does not use configured prefix")
            if not expected_prefix and protein.startswith(prefix):
                raise SageSearchError("target PSM cannot use configured decoy prefix")
            sequence = sequences.get(protein)
            if sequence is None or peptide not in sequence:
                raise SageSearchError(f"PSM peptide is absent from protein sequence: {protein}")
            rows.append(
                {
                    "spectrum_id": spectrum_id,
                    "peptide": peptide,
                    "protein_accession": protein,
                    "score": score,
                    "target_decoy": label,
                    "is_decoy": label == "decoy",
                }
            )
        if not rows:
            raise SageSearchError("search fixture has no PSM candidates")
        rows.sort(key=lambda row: (-row["score"], row["spectrum_id"], row["peptide"]))
        running: list[float] = []
        targets = 0
        decoys = 0
        for row in rows:
            if row["is_decoy"]:
                decoys += 1
            else:
                targets += 1
            running.append(decoys / max(targets, 1))
        q_values = [0.0] * len(rows)
        minimum = 1.0
        for index in range(len(rows) - 1, -1, -1):
            minimum = min(minimum, running[index])
            q_values[index] = round(minimum, 8)
        fdr_level = _float(config["fdr_level"], "config.fdr_level")
        for row, q_value in zip(rows, q_values, strict=True):
            row["q_value"] = q_value
            row["accepted"] = not row["is_decoy"] and q_value <= fdr_level
        return rows

    @staticmethod
    def _rollup(
        rows: Sequence[Mapping[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        peptides: dict[str, dict[str, Any]] = {}
        proteins: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not row["accepted"]:
                continue
            peptide = str(row["peptide"])
            protein = str(row["protein_accession"])
            peptide_record = peptides.setdefault(
                peptide,
                {
                    "peptide": peptide,
                    "protein_accessions": [],
                    "psm_count": 0,
                    "best_score": row["score"],
                    "q_value": row["q_value"],
                    "is_decoy": False,
                },
            )
            if protein not in peptide_record["protein_accessions"]:
                peptide_record["protein_accessions"].append(protein)
            peptide_record["psm_count"] += 1
            peptide_record["best_score"] = max(peptide_record["best_score"], row["score"])
            peptide_record["q_value"] = min(peptide_record["q_value"], row["q_value"])
            protein_record = proteins.setdefault(
                protein,
                {
                    "protein_accession": protein,
                    "peptide_count": 0,
                    "best_score": row["score"],
                    "q_value": row["q_value"],
                    "is_decoy": False,
                },
            )
            protein_record["peptide_count"] += 1
            protein_record["best_score"] = max(protein_record["best_score"], row["score"])
            protein_record["q_value"] = min(protein_record["q_value"], row["q_value"])
        return (
            sorted(peptides.values(), key=lambda item: item["peptide"]),
            sorted(proteins.values(), key=lambda item: item["protein_accession"]),
        )

    @staticmethod
    def _recovery(data: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        accepted = {
            (str(row["spectrum_id"]), str(row["peptide"]), str(row["protein_accession"]))
            for row in rows
            if row["accepted"]
        }
        recovered: list[str] = []
        for value in cast(list[Any], data["spike_ins"]):
            spike = _mapping(value, "spike-in")
            spike_id = _string(spike.get("id"), "spike-in id")
            key = (
                _string(spike.get("spectrum_id"), "spike-in spectrum_id"),
                _string(spike.get("peptide"), "spike-in peptide"),
                _string(spike.get("expected_protein"), "spike-in expected_protein"),
            )
            if key in accepted:
                recovered.append(spike_id)
        total = len(data["spike_ins"])
        return {
            "expected_spike_ins": total,
            "recovered_spike_ins": len(recovered),
            "recovered_ids": sorted(recovered),
            "recovery_fraction": round(len(recovered) / max(total, 1), 8),
            "passed": len(recovered) == total and total > 0,
        }

    @staticmethod
    def _write_json(path: Path, value: Any) -> bytes:
        payload = _canonical(value)
        path.write_bytes(payload)
        return payload

    def run(self, *, fixture: bool = False) -> SageSearchSummary:
        """Run the fixture search and resume identical completed outputs."""
        if not fixture:
            raise SageSearchError("--fixture is required for the bounded Sage workflow")
        data = self._load_fixture()
        config = self._load_config(data)
        input_record, spectrum_count = self._verify_input(data)
        database_record, sequences = self._load_database(data, config)
        psms = self._build_psms(data, config, sequences)
        peptides, proteins = self._rollup(psms)
        recovery = self._recovery(data, psms)
        if not recovery["passed"]:
            raise SageSearchError("synthetic spike-in recovery failed")
        target_psms = sum(not bool(row["is_decoy"]) for row in psms)
        decoy_psms = sum(bool(row["is_decoy"]) for row in psms)
        accepted_psms = sum(bool(row["accepted"]) for row in psms)
        accepted_target_psms = sum(bool(row["accepted"]) and not bool(row["is_decoy"]) for row in psms)
        accepted_decoy_psms = sum(bool(row["accepted"]) and bool(row["is_decoy"]) for row in psms)
        estimated_fdr = round(accepted_decoy_psms / max(accepted_target_psms, 1), 8)
        normalized_config = dict(config)
        input_record = dict(input_record)
        resume_material = {
            "config": normalized_config,
            "input": input_record,
            "database": database_record,
            "psms": psms,
            "recovery": recovery,
        }
        resume_key = _sha256_bytes(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "config": self.output_root / "search_config.json",
            "psms": self.output_root / "psms.json",
            "peptides": self.output_root / "peptides.json",
            "proteins": self.output_root / "proteins.json",
            "fdr": self.output_root / "fdr_summary.json",
            "recovery": self.output_root / "recovery_report.json",
            "receipt": self.output_root / "search_receipt.json",
            "log": self.output_root / "search_log.json",
            "manifest": self.output_root / "search_manifest.json",
        }
        config_output = {
            "schema_version": 1,
            "engine": normalized_config["engine"],
            "engine_version": normalized_config["engine_version"],
            "configuration": normalized_config,
            "input": input_record,
            "database": database_record,
            "resume_key": resume_key,
        }
        fdr_output = {
            "schema_version": 1,
            "method": "target_decoy_ratio",
            "threshold": normalized_config["fdr_level"],
            "target_decoy_method": normalized_config["target_decoy"]["method"],
            "target_psms": target_psms,
            "decoy_psms": decoy_psms,
            "accepted_target_psms": accepted_target_psms,
            "accepted_decoy_psms": accepted_decoy_psms,
            "accepted_psms": accepted_psms,
            "estimated_fdr": estimated_fdr,
            "q_values_monotonic": all(
                psms[index]["q_value"] <= psms[index + 1]["q_value"] for index in range(len(psms) - 1)
            ),
        }
        recovery_output = {"schema_version": 1, **recovery, "resume_key": resume_key}
        raw_payloads = {
            "config": config_output,
            "psms": {"schema_version": 1, "rows": psms},
            "peptides": {"schema_version": 1, "rows": peptides},
            "proteins": {"schema_version": 1, "rows": proteins},
            "fdr": fdr_output,
            "recovery": recovery_output,
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256_bytes(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "engine": normalized_config["engine"],
            "engine_version": normalized_config["engine_version"],
            "input": input_record,
            "database": database_record,
            "configuration": normalized_config,
            "target_decoy": normalized_config["target_decoy"],
            "fdr": fdr_output,
            "recovery": recovery_output,
            "spectrum_count_in_mzml": spectrum_count,
            "synthetic_candidate_count": len(psms),
            "raw_downloaded": False,
            "locked_payload_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "engine": normalized_config["engine"],
            "engine_version": normalized_config["engine_version"],
            "resume_key": resume_key,
            "events": [
                {"event": "input_verified", "artifact_sha256": input_record["artifact_sha256"]},
                {"event": "target_decoy_scored", "psm_rows": len(psms)},
                {"event": "fdr_applied", "threshold": normalized_config["fdr_level"]},
                {"event": "synthetic_recovery_verified", "passed": True},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "psm_rows": len(psms),
            "accepted_psms": accepted_psms,
            "accepted_peptides": len(peptides),
            "accepted_proteins": len(proteins),
            "estimated_fdr": estimated_fdr,
            "recovery_passed": recovery["passed"],
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                    "sha256": _sha256_bytes(payload_bytes[name]),
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
                raise SageSearchError("existing search receipt differs from deterministic rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise SageSearchError(f"existing search artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return SageSearchSummary(
            psm_rows=len(psms),
            accepted_psms=accepted_psms,
            accepted_peptides=len(peptides),
            accepted_proteins=len(proteins),
            target_psms=target_psms,
            decoy_psms=decoy_psms,
            estimated_fdr=estimated_fdr,
            recovered_spike_ins=int(recovery["recovered_spike_ins"]),
            total_spike_ins=int(recovery["expected_spike_ins"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
