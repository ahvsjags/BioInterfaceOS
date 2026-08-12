"""Tests for real proteomics result profiling with no target promotion."""

from __future__ import annotations

import gzip
import sqlite3
from pathlib import Path

import pytest

from biointerfaceos.real_proteomics_result_profile import (
    RealProteomicsResultProfileError,
    RealProteomicsResultProfileWorkflow,
    _canonical_accession,
)

ROOT = Path(__file__).resolve().parents[2]


def _mzidentml(path: Path) -> None:
    value = b"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<MzIdentML xmlns=\"http://psidev.info/psi/pi/mzIdentML/1.1\">
  <SequenceCollection>
    <DBSequence id=\"db1\" accession=\"P02768|ALBU_HUMAN\" />
    <DBSequence id=\"db2\" accession=\"Q9ZZZ9|TEST_HUMAN\" />
    <PeptideEvidence id=\"pe1\" dBSequence_ref=\"db1\" />
    <PeptideEvidence id=\"pe2\" dBSequence_ref=\"db2\" />
  </SequenceCollection>
  <DataCollection><AnalysisData><SpectrumIdentificationList id=\"list\">
    <SpectrumIdentificationResult id=\"sir1\">
      <SpectrumIdentificationItem id=\"sii1\" passThreshold=\"true\">
        <PeptideEvidenceRef peptideEvidence_ref=\"pe1\" />
      </SpectrumIdentificationItem>
      <SpectrumIdentificationItem id=\"sii2\" passThreshold=\"false\">
        <PeptideEvidenceRef peptideEvidence_ref=\"pe2\" />
      </SpectrumIdentificationItem>
    </SpectrumIdentificationResult>
  </SpectrumIdentificationList></AnalysisData></DataCollection>
</MzIdentML>
"""
    with gzip.open(path, "wb") as stream:
        stream.write(value)


def test_mzidentml_profile_uses_only_passed_peptide_evidence(tmp_path: Path) -> None:
    path = tmp_path / "result.mzid.gz"
    _mzidentml(path)

    accessions, spectra, unparseable = RealProteomicsResultProfileWorkflow._mzidentml_profile(path)

    assert accessions == ("P02768",)
    assert spectra == 1
    assert unparseable == 0


def test_msf_profile_reads_target_annotation_rows_without_scores(tmp_path: Path) -> None:
    path = tmp_path / "result.msf"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE ProteinAnnotations (ProteinID INTEGER, Description TEXT)")
    connection.execute("CREATE TABLE ProteinScores (ProteinID INTEGER, ProteinScore REAL)")
    connection.execute(
        "INSERT INTO ProteinAnnotations VALUES (?, ?)",
        (1, ">sp|P02768|ALBU_HUMAN Serum albumin OS=Homo sapiens"),
    )
    connection.execute(
        "INSERT INTO ProteinAnnotations VALUES (?, ?)",
        (2, ">tr|Q9ZZZ9|TEST_HUMAN Test OS=Homo sapiens"),
    )
    connection.execute("INSERT INTO ProteinScores VALUES (?, ?)", (1, 1.0))
    connection.commit()
    connection.close()

    accessions, rows, unparseable = RealProteomicsResultProfileWorkflow._msf_profile(path)

    assert accessions == ("P02768",)
    assert rows == 1
    assert unparseable == 0


def test_canonical_accession_rejects_unstructured_values() -> None:
    assert _canonical_accession("P02768|ALBU_HUMAN") == "P02768"
    assert _canonical_accession(">sp|Q9ZZZ9|TEST_HUMAN Test") == "Q9ZZZ9"
    assert _canonical_accession("not an accession") is None


def test_profile_requires_strict_mode_and_acquired_files(tmp_path: Path) -> None:
    workflow = RealProteomicsResultProfileWorkflow(
        ROOT,
        raw_root=tmp_path / "raw",
        output_root=tmp_path / "profile",
    )

    with pytest.raises(RealProteomicsResultProfileError, match="requires --strict"):
        workflow.run()
    with pytest.raises(RealProteomicsResultProfileError, match="required acquired result is missing"):
        workflow.run(strict=True)
