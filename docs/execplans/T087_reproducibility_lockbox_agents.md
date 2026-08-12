# T087 Reproducibility and Lockbox evaluator agents

## Purpose

Implement a reproducibility evaluator that rebuilds a fixture result and compares hashes, alongside a disabled-by-default Lockbox evaluator that cannot activate before signed freeze authorization.

## Preconditions

T014/T015 release and lockbox foundations, T068 graders, T080 typed runtime, T086 red-team critical gate, and the immutable fixture release are valid.

## Non-goals

This task will not open the locked test payload, expose training methods through the evaluator interface, activate evaluation from an unsigned or unfrozen state, or overwrite a prior reproduction receipt.

## Interfaces and invariants

`biointerfaceos agent eval reproducibility` will rebuild a fixture result in a temporary workspace, compare artifact and manifest hashes, and emit a signed-freeze gate. The evaluator API exposes only metadata and receipts; model training methods are absent. Lockbox activation requires a signed freeze token matching the frozen release and remains disabled in the development fixture.

## Implementation plan

1. Define versioned schemas for reproduction inputs, hash comparisons, evaluator capabilities, activation gates, and receipts.
2. Load the frozen release manifest and grader metadata without reading locked payload content.
3. Rebuild the fixture result in a temporary directory, compare byte hashes, and preserve mismatch evidence if any.
4. Attempt unsigned lockbox activation and verify that it is rejected; scan the evaluator interface for training-method exposure.
5. Add CLI, focused tests, evidence artifacts, report, and state/ledger advancement.

## Validation

- `UV_OFFLINE=1 uv lock --check`
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`
- `UV_OFFLINE=1 make check`
- `biointerfaceos agent eval reproducibility`
- fixture rebuild is clean and hash-identical
- lockbox evaluator cannot activate before signed freeze
- training methods are absent from evaluator interface
- assets, catalog, lockbox, release, state, compileall, and diff gates

## Failure recovery

Keep the Lockbox evaluator disabled on any gate failure. Preserve reproduction mismatches and capability-scan findings; do not read or copy locked payloads while diagnosing.

## Outputs

Versioned evaluator schemas, reproduction fixture, hash comparison, disabled activation gate, capability audit, receipts, focused tests, evidence report, and state/ledger advancement.
