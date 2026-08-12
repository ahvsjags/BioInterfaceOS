# T061 Derive cell and immune response signatures

## Purpose

Derive auditable cell-state and immune-response signatures from the T059 processed expression objects and the T060 raw-count study, keeping predefined signatures separate from data-driven exploratory scores and validating stability without label leakage.

## Preconditions

T059 processed study objects and T060 raw counts/QC are complete. Upstream study accessions, sample metadata, contrasts, source checksums, and within-study boundaries remain frozen.

## Non-goals

This task will not forcibly batch-merge studies, use outcome labels to learn signatures, call external pathway services, infer cell composition from unavailable data, or promote exploratory factors as predefined biology.

## Interfaces and invariants

Every score records source study/sample, signature family (`predefined` or `data_driven`), gene members, pathway provenance/version, scoring method, normalization input, missingness, and leakage audit. Leave-one-study-out validation must be explicit. Cross-study summaries are score-level comparisons only; expression matrices remain study-local.

## Implementation plan

1. Load and hash T059/T060 expression and metadata inputs, verifying sample and study provenance.
2. Define a small versioned fixture pathway/signature registry with separate predefined immune/cell-state modules and exploratory data-driven modules.
3. Compute study-local signature scores with explicit missing-gene handling and retain the input gene set.
4. Run leave-one-study-out stability and contrast-direction checks without using outcome labels for feature selection.
5. Emit signature registry, score matrix, stability/QC report, leakage audit, deterministic receipt/log/manifest, and tests.
6. Add `biointerfaceos omics derive-signatures`, evidence, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics derive-signatures`
- predefined/data-driven separation and pathway provenance assertions
- leave-study-out stability and no-label-leakage assertions
- no cross-study expression batch merge or live pathway/network access
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If a signature lacks the declared gene members or is unstable under leave-study-out validation, retain the score as exploratory or exclude it with a reason; do not fill missing genes or tune the signature against outcomes.

## Outputs

Signature registry, study-local score matrices, stability/QC report, leakage audit, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
