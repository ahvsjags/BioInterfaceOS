# T059: Ingest and normalize GEO processed data

## Purpose

Ingest the eligible processed GEO/SRA matrices from T058 into study-level expression objects, normalize gene identifiers and units, validate sample metadata/contrasts, and run within-study QC without forcibly batch-merging studies.

## Preconditions

T058 discovery is complete and its two eligible processed candidates, public-file checksums, paper-family links, and coverage gaps are frozen. T042 protein/orthology mapping, T043 protocol ontology, and T044 endpoint ontology are available for metadata normalization.

## Non-goals

This task will not download restricted or credentialed matrices, batch-merge unrelated studies, infer missing sample metadata, or treat a metadata-only candidate as a processed expression object.

## Interfaces and invariants

Every study object records source accession, source-file checksum, sample IDs, biological system, material/dose/time, gene-ID namespace and mapping version, normalization method, contrast definition, missingness, QC metrics, and project batch. Within-study normalization is separate from cross-study harmonization. Unusable studies remain in an exclusion ledger.

## Implementation plan

1. Define sanitized processed-matrix fixtures for the T058 eligible candidates with sample metadata, gene IDs, counts/abundance values, and expected contrasts.
2. Validate T058 candidate registry/card hashes and public-file checksums before ingestion.
3. Parse matrices, normalize gene IDs through the declared mapping version, and preserve raw and normalized values.
4. Validate sample metadata, material exposure, dose/time, contrast directions, and within-study replicate/QC thresholds.
5. Emit study-level expression objects, contrast summaries, QC receipts, exclusion ledger, and coverage gaps; keep studies separate.
6. Add `biointerfaceos omics geo process --mode processed`, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics geo process --mode processed`
- gene-ID normalization, metadata/contrast, replicate, and within-study QC assertions
- no cross-study batch merge and explicit exclusion of T058 ineligible candidates
- `biointerfaceos assets verify`
- `biointerfaceos catalog check`
- `biointerfaceos lockbox self-test`
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`
- `biointerfaceos state validate`
- `python -m compileall -q src tests`
- `git diff --check`

## Failure recovery

If a processed file fails checksum, metadata, gene-ID, or within-study QC, quarantine that study with a reason and preserve its discovery card. If only one study remains usable, report it as a standalone study object and do not create a cross-study batch correction.

## Outputs

Study-level expression objects, sample metadata, normalized matrices, contrast summaries, within-study QC reports, exclusion ledger, deterministic receipts/logs, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
