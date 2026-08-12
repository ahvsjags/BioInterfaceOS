# T054: Implement Sage search workflow and toy recovery

## Purpose

Run a reproducible, fixture-backed Sage-style database search over the T053 mzML artifact, producing auditable PSM, peptide, and protein outputs with explicit target-decoy FDR controls and a synthetic spike-in recovery test.

## Preconditions

T053 is complete and its supported mzML artifact, checksum, instrument metadata, and conversion receipt are frozen. T023 supplies the search/configuration contracts and the repository has an offline species FASTA fixture available for the selected toy search.

## Non-goals

This task will not access restricted PRIDE files, download project-specific databases, cherry-pick project-specific spectra, or claim live-study discovery from a toy fixture. A declared alternative open search engine may be used only if Sage cannot run within the bounded environment and the decision, compatibility limits, and QC equivalence are recorded.

## Interfaces and invariants

The search receipt will record input artifact and database SHA-256 values, engine/version, precursor and fragment tolerances, enzyme, allowed missed cleavages, fixed and variable modifications, target/decoy construction, database version, FDR level, and deterministic resume identity. PSM, peptide, and protein tables will retain target/decoy labels and scores needed to reproduce q-values. No target-only filtering may be used for the reported discoveries.

## Implementation plan

1. Define the fixture search configuration, species FASTA, synthetic spike-in peptides, and schema for PSM, peptide, protein, and receipt outputs.
2. Validate the T053 mzML checksum and parse bounded spectra without accessing any unavailable raw source.
3. Execute the Sage fixture search with explicit enzyme, modifications, mass tolerances, protein database version, and target-decoy settings.
4. Compute deterministic target-decoy q-values and FDR summaries at the declared threshold; retain decoy counts and filtering decisions.
5. Roll up accepted PSMs to unique peptides and proteins with protein-level evidence and ambiguity handling.
6. Add synthetic spike-in recovery tests that assert expected identifications, no target-only inflation, and stable output hashes across resume.
7. Add `biointerfaceos omics search --fixture`, focused tests, evidence report, and state/ledger updates.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics search --fixture`
- explicit inspection of enzyme, modifications, database version, target-decoy, FDR, and spike-in recovery fields
- T053 input checksum and resume assertions
- `biointerfaceos assets verify`
- `biointerfaceos catalog check`
- `biointerfaceos lockbox self-test`
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`
- `biointerfaceos state validate`
- `python -m compileall -q src tests`
- `git diff --check`

## Failure recovery

If the Sage binary is unavailable offline, preserve the declared search configuration and use a documented open-engine fallback with the same target-decoy/FDR and spike-in acceptance tests. If the fixture cannot satisfy the declared FDR or recovery threshold, stop at a failed search receipt, retain the failure outputs, and do not promote PSMs, peptides, or proteins.

## Outputs

Search configuration, FASTA provenance, PSM/peptide/protein tables, FDR/QC summaries, synthetic recovery report, deterministic receipts/logs, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.

## Completion evidence

- Implementation commit: `ef55fd0`.
- The bounded Sage-style fixture engine produced 3 PSM rows: 2 targets and 1 reverse decoy; 2 target PSMs passed the declared 1% target-decoy FDR threshold, yielding 2 peptides, 2 proteins, estimated FDR `0.0`, and monotonic q-values.
- Search parameters were explicit: Sage `fixture-sage-v1`, trypsin, 2 missed cleavages, 10 ppm precursor tolerance, 20 ppm fragment tolerance, carbamidomethyl[C] fixed modification, oxidation[M] variable modification, reverse decoys with `DECOY_` prefix, and database version `uniprot-human-fixture-2026-08`.
- The independent Homo sapiens FASTA was checksum-verified (`ca365eb053c919982daddca1e046c83bb1f7b0d2ee6270ddf24765a91c68bfed`) and matched the declared target database. Synthetic spike-in recovery passed 2/2. The T053 mzML input checksum was verified; its fixture contains zero native spectra, so the recovery is explicitly synthetic/toy and not promoted as a live-study result.
- Focused Sage tests: 3 passed. Full offline gate: 205 tests passed; Ruff, formatting, mypy, UV lock/sync, conversion, PRIDE triage, coverage, Silver/Gold-auto validation, review export, assets, catalog, lockbox, release, state validation, compileall, and `git diff --check` passed.
- The first CLI run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes. No raw download, locked payload access, or live network request occurred.
