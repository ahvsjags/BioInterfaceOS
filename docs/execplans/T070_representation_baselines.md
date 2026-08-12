# T070 Implement representation benchmark baselines

## Purpose

Add representation baselines for material text, structure fingerprints, descriptors, and available polymer embeddings under the same T067 split and T068/T069 evaluation contracts. Missing structure must be reported explicitly and must not create silent complete-case bias.

## Preconditions

T067 instances, T068 grader metrics, T069 simple baselines, and the T021/T022 material text/structure interfaces are validated. No locked test data or network download is permitted.

## Non-goals

This task will not tune models on validation outcomes, change split/group assignments, add unverified external embeddings, or claim polymer coverage where structure is absent.

## Interfaces and invariants

`biointerfaceos benchmark run-baselines --group representation` runs descriptor, fingerprint, text, and available polymer-embedding baselines with identical train/validation rows and seed/config logging. Each result reports structure coverage, missingness indicators, primary OOD metrics, confidence intervals, and grouped metrics.

## Implementation plan

1. Define a versioned representation configuration and feature-availability audit for text/structure/descriptor/polymer inputs.
2. Build deterministic local descriptor and fingerprint vectors, text hashing features, and a fixture-backed polymer embedding path when available.
3. Preserve all rows with explicit missing-structure indicators; compute available-subset metrics alongside full-split metrics.
4. Run every representation baseline through T068 metrics with deterministic confidence intervals and identical split membership.
5. Emit feature/coverage audits, baseline results, failure ledger, receipts/logs/manifests, focused tests, and CLI output.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos benchmark run-baselines --group representation`
- descriptor, fingerprint, text, and available polymer baselines attempted
- missing structure coverage and indicator policy reported; no complete-case-only result presented as primary
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

If a representation is unavailable, retain an explicit failure/coverage row and continue other declared representations. If a representation changes split membership or hides missing structures, stop the comparison and preserve the audit artifact until corrected.

## Outputs

Versioned representation configuration, feature/coverage audit, representation result/metric artifacts, failure ledger, deterministic receipts/logs/manifests, focused tests, evidence report, and state/ledger advancement.
