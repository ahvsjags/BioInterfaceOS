# T055: Implement label-free quantification and protein inference

## Purpose

Convert the accepted T054 PSM/peptide/protein evidence into an auditable label-free protein-by-sample matrix, preserving replicate identity, missingness, contaminants, protein groups, normalization choices, and fixture-ratio recovery.

## Preconditions

T054 is complete and its deterministic accepted peptide/protein outputs, search receipt, database provenance, and FDR summary are frozen. The fixture quantification input will declare sample/run identities and expected synthetic ratios without inventing biological replicates.

## Non-goals

This task will not infer missing values as observed measurements, merge unrelated projects, discard contaminants silently, or claim live-study quantitative effects from the toy fixture. Any protein group ambiguity remains visible in the output and uncertainty is retained.

## Interfaces and invariants

The quantification receipt will record input hashes, sample/run IDs, replicate counts, normalization method, missingness policy, contaminant handling, protein-group inference rule, and deterministic resume identity. Every matrix cell will carry observed/missing status and source evidence. Expected ratios will be evaluated only against the declared synthetic fixture truth.

## Implementation plan

1. Define the fixture run/sample table, LFQ intensities, contaminants, protein groups, and expected-ratio schema.
2. Validate T054 output hashes and map accepted proteins to declared samples without creating pseudo-replicates.
3. Implement deterministic normalization with an explicit route and preserve raw and normalized values.
4. Infer protein groups from peptide evidence, retain ambiguous groups, flag contaminants, and summarize missingness by sample/protein.
5. Add `biointerfaceos omics quantify --fixture`, focused tests, and fixture expected-ratio recovery assertions.
6. Write deterministic matrices, QC summaries, receipt/log/manifest, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics quantify --fixture`
- replicate, normalization, protein-group, contaminant, and missingness assertions
- T054 input checksum and deterministic resume assertions
- `biointerfaceos assets verify`
- `biointerfaceos catalog check`
- `biointerfaceos lockbox self-test`
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`
- `biointerfaceos state validate`
- `python -m compileall -q src tests`
- `git diff --check`

## Failure recovery

If the fixture does not contain enough independent runs to support the declared ratio test, preserve a missing/insufficient-replicates status and do not promote quantitative conclusions. If normalization or inference is ambiguous, retain raw values and emit a review queue rather than applying an unrecorded correction.

## Outputs

Run/sample manifest, raw and normalized protein matrices, protein-group table, missingness/contaminant/QC summaries, expected-ratio recovery report, deterministic receipts/logs, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.

## Completion evidence

- Implementation commit: `c060481`.
- The fixture contained 4 independent runs across 2 conditions, with 2 biological replicates per condition. Two accepted T054 proteins were quantified; one contaminant group and one ambiguous shared protein group were retained and flagged rather than silently promoted.
- The primary declared-run-scaling route recovered expected treated/control ratios for both proteins (2/2): `P0SPIKE1=2.0` and `P0SPIKE2=1.88235294` against expected `2.0` and `1.88`. A median-centering comparison route was also emitted; raw values and normalized values were both preserved.
- One protein-by-run cell remained missing (`P0SPIKE2` in `TRT_R2`); `no_imputation=true`. No pseudo-replicates were created, and contaminant handling remained explicit.
- Focused LFQ tests: 3 passed. Full offline gate: 208 tests passed; Ruff, formatting, mypy, UV lock/sync, Sage search, conversion, PRIDE triage, coverage, Silver/Gold-auto validation, review export, assets, catalog, lockbox, release, state validation, compileall, and `git diff --check` passed.
- The first CLI run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes. No raw download, locked payload access, or live network request occurred.
