# T060 Optional public RNA-seq raw reprocessing

## Purpose

Implement the bounded raw-mode RNA-seq route requested after GEO discovery. The development path is fixture-backed and deterministic: it uses a sanitized public-study representation, short-read records, a versioned reference, and declared counting rules without downloading live FASTQ or accessing restricted material.

## Preconditions

T058 discovery is complete and the public processed/raw metadata boundary is frozen. The fixture must identify one manageable public study, preserve accession and source checksums, and declare the reference version and counting parameters.

## Non-goals

This task will not download live SRA/FASTQ data, access credentialed or locked payloads, infer a reference genome, perform transcript-level ambiguity resolution, or merge raw counts with the T059 processed matrices.

## Interfaces and invariants

Every raw-mode receipt records study accession, source-read checksum, reference version, read-counting rule, sample metadata, expected counts, QC metrics, and resume key. Raw and count objects remain study-local. No network, credential, raw external payload, or cross-study batch merge is permitted in the fixture workflow.

## Implementation plan

1. Define one sanitized public raw-study fixture with paired short reads, sample metadata, a versioned toy reference, and expected gene counts.
2. Validate accession/source/reference checksums and reject any study that is not explicitly public and manageable.
3. Count exact reference-matching reads under a declared paired-end rule; preserve unmatched-read QC instead of silently assigning it.
4. Emit study-level counts, sample metadata, QC, exclusion ledger, deterministic receipt/log/manifest, and resume behavior.
5. Add `biointerfaceos omics geo process --mode raw --fixture`, focused tests, evidence, and state advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics geo process --mode raw --fixture`
- raw-count recovery and reference/version/checksum assertions
- unmatched-read and within-study QC assertions
- no network, credential, locked-payload, or cross-study merge access
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If a public raw study is too large, lacks a versioned reference, or fails checksum/metadata/QC validation, retain its metadata and exclusion reason, keep T059 processed outputs authoritative, and leave the optional raw route blocked.

## Outputs

Study-level raw-count objects, sample metadata, count/QC receipts, exclusion ledger, deterministic logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.

## Completion evidence

- Implementation commit: `666719b`.
- One public, credential-free, manageable fixture study passed raw processing with 4 samples, 18 paired reads, 16 matched pairs, 2 unmatched pairs, and 2 recovered reference genes. The versioned reference and exact paired-end counting rule are recorded in the output receipt.
- Focused GEO raw-processing tests: 3 passed. Full offline gate: 223 tests passed; Ruff, formatting, mypy, UV lock/sync, assets, catalog, lockbox, immutable release verification, state validation, compileall, and `git diff --check` passed.
- The first CLI run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes. No live raw download, credential, locked payload, or network access occurred.
