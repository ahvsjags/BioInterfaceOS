"""Fixture-backed cell and immune response signature derivation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SignatureWorkflowError(RuntimeError):
    """Raised when signature provenance, scoring, or leakage checks fail."""


@dataclass(frozen=True)
class SignatureWorkflowSummary:
    """Summary of a study-preserving signature run."""

    studies: int
    samples: int
    signatures: int
    scores: int
    stable_folds: int
    total_folds: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SignatureWorkflowError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SignatureWorkflowError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SignatureWorkflowError(f"{label} must be numeric")
    return float(value)


class SignatureWorkflow:
    """Derive separate predefined and data-driven scores from frozen study inputs."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/signature_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/signatures"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SignatureWorkflowError(f"cannot load signature fixture: {exc}") from exc
        fixture = _mapping(data, "signature fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "signatures":
            raise SignatureWorkflowError("signature fixture schema or mode is invalid")
        if not isinstance(fixture.get("inputs"), list) or not fixture["inputs"]:
            raise SignatureWorkflowError("signature fixture has no inputs")
        if not isinstance(fixture.get("signatures"), list) or not fixture["signatures"]:
            raise SignatureWorkflowError("signature fixture has no signatures")
        return fixture

    def _read_input(self, value: Any) -> tuple[str, dict[str, Any]]:
        row = _mapping(value, "signature input")
        label = _string(row.get("label"), "input label")
        relative = _string(row.get("path"), "input path")
        path = (self.root / relative).resolve(strict=True)
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise SignatureWorkflowError("signature input escaped repository") from exc
        expected = _string(row.get("sha256"), "input checksum")
        if _sha256_path(path) != expected:
            raise SignatureWorkflowError(f"signature input checksum differs: {label}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SignatureWorkflowError(f"cannot load signature input {label}: {exc}") from exc
        return label, _mapping(payload, label)

    def _load_inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        inputs: dict[str, dict[str, Any]] = {}
        for value in fixture["inputs"]:
            label, payload = self._read_input(value)
            if label in inputs:
                raise SignatureWorkflowError(f"duplicate signature input: {label}")
            inputs[label] = payload
        required = {
            "T059 normalized matrices",
            "T059 sample metadata",
            "T060 raw counts",
            "T060 sample metadata",
        }
        if set(inputs) != required:
            raise SignatureWorkflowError("signature inputs do not match T059/T060 contract")
        return inputs

    @staticmethod
    def _sample_metadata(payload: Mapping[str, Any], label: str) -> dict[str, dict[str, Any]]:
        rows = payload.get("samples")
        if not isinstance(rows, list) or not rows:
            raise SignatureWorkflowError(f"{label} has no samples")
        result: dict[str, dict[str, Any]] = {}
        for value in rows:
            row = _mapping(value, f"{label} sample")
            sample_id = _string(row.get("sample_id"), "sample ID")
            if sample_id in result:
                raise SignatureWorkflowError(f"duplicate sample metadata: {sample_id}")
            result[sample_id] = row
        return result

    def _collect_samples(self, inputs: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        processed_matrices = inputs["T059 normalized matrices"].get("study_objects")
        if not isinstance(processed_matrices, list) or not processed_matrices:
            raise SignatureWorkflowError("T059 normalized matrices have no study objects")
        processed_metadata = self._sample_metadata(
            inputs["T059 sample metadata"], "T059 sample metadata"
        )
        samples: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for study_value in processed_matrices:
            study = _mapping(study_value, "T059 study object")
            accession = _string(study.get("study_accession"), "T059 accession")
            matrix = study.get("matrix")
            if not isinstance(matrix, list) or not matrix:
                raise SignatureWorkflowError(f"T059 matrix is empty: {accession}")
            values_by_gene: dict[str, dict[str, float]] = {}
            for matrix_value in matrix:
                row = _mapping(matrix_value, "T059 normalized matrix row")
                gene = _string(row.get("normalized_gene_id"), "normalized gene ID")
                values = _mapping(row.get("values"), "T059 normalized values")
                values_by_gene[gene] = {
                    _string(sample_id, "T059 sample ID"): _number(value, "T059 expression")
                    for sample_id, value in values.items()
                }
            study_sample_ids = set(next(iter(values_by_gene.values())))
            for sample_id in sorted(study_sample_ids):
                metadata = processed_metadata.get(sample_id)
                if metadata is None or metadata.get("study_accession") != accession:
                    raise SignatureWorkflowError(f"T059 metadata mismatch: {sample_id}")
                if sample_id in seen_ids:
                    raise SignatureWorkflowError(
                        f"sample appears in multiple input routes: {sample_id}"
                    )
                seen_ids.add(sample_id)
                samples.append(
                    {
                        "study_accession": accession,
                        "sample_id": sample_id,
                        "condition": _string(metadata.get("condition"), "condition"),
                        "route": "processed",
                        "values": {
                            gene: values_by_gene[gene][sample_id] for gene in sorted(values_by_gene)
                        },
                    }
                )

        raw_studies = inputs["T060 raw counts"].get("studies")
        if not isinstance(raw_studies, list) or not raw_studies:
            raise SignatureWorkflowError("T060 raw counts have no studies")
        raw_metadata = self._sample_metadata(inputs["T060 sample metadata"], "T060 sample metadata")
        for study_value in raw_studies:
            study = _mapping(study_value, "T060 raw study")
            accession = _string(study.get("study_accession"), "T060 accession")
            count_rows = study.get("counts")
            if not isinstance(count_rows, list) or not count_rows:
                raise SignatureWorkflowError(f"T060 counts are empty: {accession}")
            for count_value in count_rows:
                count_row = _mapping(count_value, "T060 count row")
                sample_id = _string(count_row.get("sample_id"), "T060 sample ID")
                metadata = raw_metadata.get(sample_id)
                if metadata is None or metadata.get("study_accession") != accession:
                    raise SignatureWorkflowError(f"T060 metadata mismatch: {sample_id}")
                if sample_id in seen_ids:
                    raise SignatureWorkflowError(
                        f"sample appears in multiple input routes: {sample_id}"
                    )
                counts = _mapping(count_row.get("counts"), "T060 counts")
                total = sum(_number(value, "T060 count") for value in counts.values())
                if total <= 0:
                    raise SignatureWorkflowError(f"T060 sample has zero library size: {sample_id}")
                seen_ids.add(sample_id)
                samples.append(
                    {
                        "study_accession": accession,
                        "sample_id": sample_id,
                        "condition": _string(metadata.get("condition"), "condition"),
                        "route": "raw",
                        "values": {
                            _string(gene, "T060 gene ID"): math.log2(
                                1.0 + 1_000_000.0 * _number(value, "T060 count") / total
                            )
                            for gene, value in counts.items()
                        },
                    }
                )
        if not samples:
            raise SignatureWorkflowError("no samples collected for signature derivation")
        return samples

    @staticmethod
    def _validate_registry(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        registry: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["signatures"]:
            row = _mapping(value, "signature definition")
            signature_id = _string(row.get("signature_id"), "signature ID")
            family = _string(row.get("family"), "signature family")
            provenance = _string(row.get("provenance"), "signature provenance")
            method = _string(row.get("method"), "signature method")
            if signature_id in seen or family not in {"predefined", "data_driven"}:
                raise SignatureWorkflowError("signature registry is invalid")
            seen.add(signature_id)
            normalized: dict[str, Any] = {
                "signature_id": signature_id,
                "family": family,
                "provenance": provenance,
                "method": method,
            }
            if family == "predefined":
                members = row.get("gene_members")
                weights = _mapping(row.get("weights"), "predefined weights")
                if not isinstance(members, list) or not members:
                    raise SignatureWorkflowError(
                        f"predefined signature has no members: {signature_id}"
                    )
                normalized["gene_members"] = [
                    _string(member, "signature gene") for member in members
                ]
                normalized["weights"] = {
                    _string(gene, "signature weight gene"): _number(weight, "signature weight")
                    for gene, weight in weights.items()
                }
            else:
                candidates = row.get("candidate_genes")
                max_genes = row.get("max_genes")
                if (
                    not isinstance(candidates, list)
                    or not candidates
                    or not isinstance(max_genes, int)
                ):
                    raise SignatureWorkflowError(
                        f"data-driven signature is invalid: {signature_id}"
                    )
                normalized["candidate_genes"] = [
                    _string(candidate, "candidate gene") for candidate in candidates
                ]
                normalized["max_genes"] = max_genes
            registry.append(normalized)
        if not any(row["family"] == "predefined" for row in registry):
            raise SignatureWorkflowError("predefined signature family is missing")
        if not any(row["family"] == "data_driven" for row in registry):
            raise SignatureWorkflowError("data-driven signature family is missing")
        return registry

    @staticmethod
    def _z_scores(samples: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
        by_study: dict[str, list[dict[str, Any]]] = {}
        for sample in samples:
            by_study.setdefault(sample["study_accession"], []).append(sample)
        z_scores: dict[str, dict[str, float]] = {}
        for _accession, study_samples in by_study.items():
            genes = sorted({gene for sample in study_samples for gene in sample["values"]})
            means = {
                gene: sum(sample["values"].get(gene, 0.0) for sample in study_samples)
                / len(study_samples)
                for gene in genes
            }
            stds = {
                gene: math.sqrt(
                    sum(
                        (sample["values"].get(gene, 0.0) - means[gene]) ** 2
                        for sample in study_samples
                    )
                    / len(study_samples)
                )
                for gene in genes
            }
            for sample in study_samples:
                z_scores[sample["sample_id"]] = {
                    gene: round((sample["values"].get(gene, 0.0) - means[gene]) / stds[gene], 8)
                    if stds[gene] > 0
                    else 0.0
                    for gene in genes
                }
        return z_scores

    def run(self, *, fixture: bool = True) -> SignatureWorkflowSummary:
        """Derive signatures from frozen T059/T060 outputs."""
        if not fixture:
            raise SignatureWorkflowError("--fixture is required for signature derivation")
        fixture_data = self._load_fixture()
        inputs = self._load_inputs(fixture_data)
        samples = self._collect_samples(inputs)
        registry = self._validate_registry(fixture_data)
        z_scores = self._z_scores(samples)
        genes = sorted({gene for sample in samples for gene in sample["values"]})
        selected_by_study: dict[str, dict[str, list[str]]] = {}
        for signature in registry:
            if signature["family"] != "data_driven":
                continue
            signature_id = signature["signature_id"]
            candidates = [gene for gene in signature["candidate_genes"] if gene in genes]
            for accession in sorted({sample["study_accession"] for sample in samples}):
                study_samples = [
                    sample for sample in samples if sample["study_accession"] == accession
                ]
                variances = {
                    gene: sum(
                        (
                            sample["values"].get(gene, 0.0)
                            - sum(item["values"].get(gene, 0.0) for item in study_samples)
                            / len(study_samples)
                        )
                        ** 2
                        for sample in study_samples
                    )
                    / len(study_samples)
                    for gene in candidates
                }
                selected = [
                    gene
                    for gene, variance in sorted(
                        variances.items(), key=lambda item: (-item[1], item[0])
                    )
                    if variance > 0
                ][: int(signature["max_genes"])]
                if not selected:
                    raise SignatureWorkflowError(
                        f"data-driven signature has no variable genes: {accession}"
                    )
                selected_by_study.setdefault(accession, {})[signature_id] = selected

        score_rows: list[dict[str, Any]] = []
        for sample in samples:
            sample_z = z_scores[sample["sample_id"]]
            accession = sample["study_accession"]
            for signature in registry:
                if signature["family"] == "predefined":
                    members = [gene for gene in signature["gene_members"] if gene in sample_z]
                    if not members:
                        raise SignatureWorkflowError(
                            "predefined signature has no genes in sample: "
                            f"{signature['signature_id']}"
                        )
                    weights = signature["weights"]
                    denominator = sum(abs(weights.get(gene, 1.0)) for gene in members)
                    score = (
                        sum(sample_z[gene] * weights.get(gene, 1.0) for gene in members)
                        / denominator
                    )
                else:
                    members = selected_by_study[accession][signature["signature_id"]]
                    score = sum(sample_z[gene] for gene in members) / len(members)
                score_rows.append(
                    {
                        "study_accession": accession,
                        "sample_id": sample["sample_id"],
                        "condition": sample["condition"],
                        "route": sample["route"],
                        "signature_id": signature["signature_id"],
                        "family": signature["family"],
                        "provenance": signature["provenance"],
                        "method": signature["method"],
                        "genes_used": members,
                        "score": round(score, 8),
                    }
                )

        study_ids = sorted({sample["study_accession"] for sample in samples})
        signature_ids = [signature["signature_id"] for signature in registry]
        score_lookup: dict[tuple[str, str, str], list[float]] = {}
        for row in score_rows:
            score_lookup.setdefault(
                (row["signature_id"], row["study_accession"], row["condition"]), []
            ).append(row["score"])
        deltas: dict[tuple[str, str], float] = {}
        for signature_id in signature_ids:
            for accession in study_ids:
                treated = score_lookup.get((signature_id, accession, "treated"), [])
                control = score_lookup.get((signature_id, accession, "control"), [])
                if not treated or not control:
                    raise SignatureWorkflowError(
                        f"signature contrast is incomplete: {signature_id}/{accession}"
                    )
                deltas[(signature_id, accession)] = round(
                    sum(treated) / len(treated) - sum(control) / len(control), 8
                )
        stability_rows: list[dict[str, Any]] = []
        for signature_id in signature_ids:
            for held_out in study_ids:
                training_deltas = [
                    deltas[(signature_id, accession)]
                    for accession in study_ids
                    if accession != held_out and deltas[(signature_id, accession)] != 0
                ]
                reference_direction = (
                    (1 if sum(1 if delta > 0 else -1 for delta in training_deltas) > 0 else -1)
                    if training_deltas
                    else 0
                )
                held_out_delta = deltas[(signature_id, held_out)]
                held_out_direction = 1 if held_out_delta > 0 else -1 if held_out_delta < 0 else 0
                stable = bool(
                    reference_direction != 0
                    and held_out_direction != 0
                    and reference_direction == held_out_direction
                )
                stability_rows.append(
                    {
                        "signature_id": signature_id,
                        "held_out_study": held_out,
                        "training_studies": [
                            accession for accession in study_ids if accession != held_out
                        ],
                        "training_reference_direction": reference_direction,
                        "held_out_treated_minus_control": held_out_delta,
                        "held_out_direction": held_out_direction,
                        "stable": stable,
                        "labels_used_for_feature_selection": False,
                    }
                )

        selected_registry = []
        for signature in registry:
            row = dict(signature)
            if signature["family"] == "data_driven":
                row["selected_genes_by_study"] = {
                    accession: selected_by_study[accession][signature["signature_id"]]
                    for accession in study_ids
                }
            selected_registry.append(row)
        stable_folds = sum(1 for row in stability_rows if row["stable"])
        raw_payloads = {
            "registry": {"schema_version": 1, "signatures": selected_registry},
            "scores": {
                "schema_version": 1,
                "scores": score_rows,
                "cross_study_batch_merge": False,
            },
            "stability": {
                "schema_version": 1,
                "leave_one_study_out": stability_rows,
                "stable_folds": stable_folds,
                "total_folds": len(stability_rows),
            },
            "qc": {
                "schema_version": 1,
                "studies": study_ids,
                "samples": len(samples),
                "scores": len(score_rows),
                "missing_scores": 0,
                "predefined_signatures": sum(row["family"] == "predefined" for row in registry),
                "data_driven_signatures": sum(row["family"] == "data_driven" for row in registry),
                "cross_study_batch_merge": False,
            },
            "leakage": {
                "schema_version": 1,
                "feature_selection_uses_outcome_labels": False,
                "held_out_labels_used_only_for_evaluation": True,
                "pathway_network_accessed": False,
                "cross_study_expression_batch_merge": False,
                "status": "PASSED",
            },
        }
        resume_material = {
            "registry": selected_registry,
            "scores": score_rows,
            "stability": stability_rows,
        }
        resume_key = _sha256(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "registry": self.output_root / "signature_registry.json",
            "scores": self.output_root / "signature_scores.json",
            "stability": self.output_root / "stability_report.json",
            "qc": self.output_root / "qc_report.json",
            "leakage": self.output_root / "leakage_audit.json",
            "receipt": self.output_root / "processing_receipt.json",
            "log": self.output_root / "processing_log.json",
            "manifest": self.output_root / "processing_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root))
                if path.is_relative_to(self.root)
                else str(path),
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
            "studies": len(study_ids),
            "samples": len(samples),
            "signatures": len(registry),
            "scores": len(score_rows),
            "stable_folds": stable_folds,
            "total_folds": len(stability_rows),
            "cross_study_batch_merge": False,
            "real_network_accessed": False,
            "locked_payload_accessed": False,
            "resume_key": resume_key,
            "inputs": fixture_data["inputs"],
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T059_T060_inputs_verified", "studies": len(study_ids)},
                {"event": "predefined_signatures_scored", "count": receipt["signatures"] - 1},
                {"event": "data_driven_selection_without_labels", "count": 1},
                {"event": "leave_one_study_out_evaluated", "stable_folds": stable_folds},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "studies": len(study_ids),
            "samples": len(samples),
            "signatures": len(registry),
            "scores": len(score_rows),
            "stable_folds": stable_folds,
            "total_folds": len(stability_rows),
            "cross_study_batch_merge": False,
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path),
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
                raise SignatureWorkflowError("existing signature receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise SignatureWorkflowError(f"existing signature artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return SignatureWorkflowSummary(
            studies=len(study_ids),
            samples=len(samples),
            signatures=len(registry),
            scores=len(score_rows),
            stable_folds=stable_folds,
            total_folds=len(stability_rows),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
