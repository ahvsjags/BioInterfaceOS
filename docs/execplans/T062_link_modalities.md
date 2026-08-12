# T062 Link corona functional modules to cell-state evidence

## Purpose

Link T056 protein-corona functional modules to T061 cell-state and immune-response signatures while keeping directly matched study/sample evidence separate from indirect literature-level links. The output is a candidate mechanism graph, not a causal or experimental claim.

## Preconditions

T056 harmonized corona modules, T061 signature scores, and T047 evidence/coverage records are complete. Study IDs, module IDs, sample metadata, source checksums, and signature provenance remain frozen.

## Non-goals

This task will not create pseudo-pairs between unrelated samples, infer a causal mediator, merge corona and expression matrices across studies, or promote indirect literature associations to direct measurements.

## Interfaces and invariants

Every link records link class (`direct_matched` or `indirect_literature`), corona project/module, response study/signature, pairing key, evidence locator, provenance, and confidence. Direct links require an explicit shared study/sample or declared matched unit; indirect links require a literature/evidence locator and must not contain invented sample IDs. Missing pairing remains explicit.

## Implementation plan

1. Hash and load T056 module matrices, mapping audit, T061 signature registry/scores, and T047 evidence fixture.
2. Define a sanitized link fixture containing one directly matched module/signature stratum and one indirect literature-level association, plus an unmatched candidate.
3. Validate pairing keys and prevent cross-study pseudo-pairs; preserve independent modality boundaries.
4. Emit link graph, direct/indirect strata, candidate mechanism cards, pairing audit, exclusion ledger, and deterministic receipt/log/manifest.
5. Add `biointerfaceos omics link-modalities`, focused tests, evidence, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos omics link-modalities --fixture`
- direct/indirect separation and no-pseudo-pairing assertions
- evidence locator/provenance and missing-pairing assertions
- no causal wording, no cross-study batch merge, and no live network access
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If no valid shared unit exists, retain the two modalities as independent triangulation and emit an explicit unmatched/exclusion reason. If an indirect locator is incomplete, downgrade or quarantine the link instead of treating it as direct evidence.

## Outputs

Evidence link graph, direct/indirect strata, candidate mechanism cards, pairing audit, exclusion ledger, deterministic receipts/logs/manifests, focused tests, this ExecPlan, evidence report, and task-ledger/state advancement.
