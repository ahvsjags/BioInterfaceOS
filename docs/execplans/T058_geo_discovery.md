# T058: Discover public GEO/SRA biointerface response datasets

## Purpose

Discover and triage public GEO/SRA studies relevant to nanomaterial or material-biointerface responses, retaining query provenance, endpoint resolution, paper-family links, eligibility decisions, and explicit rejection reasons.

## Preconditions

T020 endpoint contracts, T026 paper-family resolution, and T051 coverage audit are complete. The versioned query matrix and source policy are available. Discovery remains metadata/processed-file level unless a public file is explicitly verified; no credentialed or restricted study is admitted.

## Non-goals

This task will not download restricted matrices, infer exposure details from titles alone, merge studies before sample/contrast resolution, or promote a study without material, biological system, dose/time, and public-file evidence.

## Interfaces and invariants

Every candidate records source accession, query block, response hash, paper-family link, material/nanomaterial, cell/tissue system, dose/time, file and access status, credential requirement, and eligibility decision. Public/processed eligibility is separate from metadata-only discovery. Rejections remain in the candidate registry with reason codes.

## Implementation plan

1. Define a sanitized GEO/SRA discovery fixture covering eligible, metadata-only, credentialed, restricted, and ambiguous candidates.
2. Validate T020/T026/T051 inputs and execute development-scope query blocks with cursor/response provenance.
3. Resolve paper families and extract material, cell/tissue, dose, time, contrast, and public-file fields.
4. Apply source policy and eligibility gates; reject credentialed/restricted candidates explicitly.
5. Emit candidate registry, eligibility cards, query receipts, rejection ledger, and coverage-gap summary.
6. Add `biointerfaceos omics geo discover --scope development`, focused tests, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics geo discover --scope development`
- public/processed file and credential/restriction gates
- material/cell/dose/time and paper-family completeness assertions
- `biointerfaceos assets verify`
- `biointerfaceos catalog check`
- `biointerfaceos lockbox self-test`
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`
- `biointerfaceos state validate`
- `python -m compileall -q src tests`
- `git diff --check`

## Failure recovery

If endpoint metadata is incomplete, retain the candidate as metadata-only with missing fields and a coverage gap. If a file requires credentials or access approval, reject it and preserve the paper-family link; use an eligible processed public matrix only when its provenance is independently verified.

## Outputs

## Completion evidence

- Implementation commit: `89dd592`.
- Development query `geo-train-01` was validated against the frozen search matrix and four candidates were discovered: two eligible processed-file candidates, one restricted/credentialed rejection, and one metadata-only candidate.
- Eligibility cards captured material, biological system, dose, time, public-file checksum/provenance, paper-family link, and evidence locator. Three explicit coverage gaps were retained for the metadata-only candidate; no restricted or credentialed study was admitted.
- Focused GEO discovery tests: 3 passed. Full offline gate: 217 tests passed; Ruff, formatting, mypy, UV lock/sync, Sage search, LFQ, corona harmonization, PRIDE QC, conversion, PRIDE triage, coverage, Silver/Gold-auto validation, review export, assets, catalog, lockbox, release, state validation, compileall, and `git diff --check` passed.
- The first CLI run created deterministic discovery outputs and the second returned `resumed=1` without changing receipt bytes. No endpoint, credential, raw payload, or locked payload was accessed.

GEO/SRA query receipt, candidate registry, eligibility cards, paper-family links, rejection ledger, coverage-gap report, deterministic logs/manifest, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
