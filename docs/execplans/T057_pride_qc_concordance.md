# T057: Run PRIDE quality control and author-result concordance

## Purpose

Audit development-scope PRIDE project quality and compare harmonized quantitative outputs with author-reported claims, retaining a failure ledger and narrowing evidence grades when raw or replicate QC is insufficient.

## Preconditions

T056 is complete. T052 project cards/sample maps, T054 search/FDR receipts, T055 LFQ matrices, and T056 project/module provenance are frozen. At least three development projects will be attempted from the sanitized PRIDE triage fixture; projects that are restricted, metadata-only, or under-replicated remain explicit failures rather than being silently excluded.

## Non-goals

This task will not access locked PRIDE payloads, fabricate author concordance, promote failed projects to discovery-grade evidence, or use author labels to tune QC thresholds.

## Interfaces and invariants

Each attempted project receives a QC record with access state, run/replicate counts, search FDR, intensity/missingness metrics, project-scale provenance, author-result locators, concordance status, discrepancy categories, and evidence grade. Failure records are append-only and remain linked to the project card and source artifact hashes.

## Implementation plan

1. Define project-level QC, author-claim, concordance, and failure-ledger schemas.
2. Validate T052/T054/T055/T056 hashes and create an attempted-project list of at least three development projects.
3. Apply replicate, FDR, intensity, missingness, and access-state gates without changing thresholds per project.
4. Compare eligible quantitative summaries with fixture author claims using explicit tolerances and locator fields.
5. Quantify concordant, discrepant, unavailable, and failed projects; preserve discrepancy reasons and lower-grade fallbacks.
6. Add `biointerfaceos omics qc-pride`, focused tests, deterministic reports, evidence report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics qc-pride`
- at least three project attempts
- replicate/FDR/intensity gates and failure-ledger checks
- concordance/discrepancy quantification and evidence-grade checks
- explicit no-locked-payload and no-live-network assertions
- `biointerfaceos assets verify`
- `biointerfaceos catalog check`
- `biointerfaceos lockbox self-test`
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`
- `biointerfaceos state validate`
- `python -m compileall -q src tests`
- `git diff --check`

## Failure recovery

If G4-style raw QC cannot be met, retain processed tables only as lower-grade evidence and record the exact failed gate. If author claims lack a resolvable locator or are not comparable to the harmonized scale, classify concordance as unavailable rather than forcing a match.

## Outputs

Project QC table, author-claim concordance table, failure ledger, evidence-grade summary, deterministic receipts/logs, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
