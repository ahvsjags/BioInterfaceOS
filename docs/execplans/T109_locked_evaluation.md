# T109 Execute one-shot locked 2025–2026 evaluation

## Objective

Run the evaluator-only lockbox protocol exactly once against the signed internal
release `bioif-internal-prelock-v1.0.0`. Use only the predeclared Paper C
predictions and frozen evaluation commands.

## Hard boundaries

- Verify the T108 signature, release manifest, prediction table, claim matrix,
  and evaluator authorization before any evaluation call.
- Forbid training, tuning, model selection, and prediction rewriting.
- Do not expose raw protected values to development code or manuscript code.
- Write first-run results, immutable receipt, and raw evaluator logs together.
- Seal outputs before interpretation and reject a second evaluation attempt.

## Implementation steps

1. Add a versioned lockbox evaluation schema and metadata-only fixture.
2. Implement `lockbox evaluate --release FROZEN_DEV --once` with evaluator-only
   token checks, one-shot state, fixed commands, and sealed output artifacts.
3. Add focused tests for signature verification, forbidden train/tune calls,
   first-run success, second-run rejection, and tamper detection.
4. Add the CLI command and `make lockbox-evaluate` target.
5. Run the complete offline gate and validate the sealed evaluator receipt.
6. Record T109 and activate T110 only after the first-run receipt is immutable.

## Evaluation contract

- Evaluate only candidates C1–C5 from the T107 prediction table.
- Preserve abstentions and unresolved contradictions.
- Report outcome status and aggregate metadata without copying protected raw
  values into development artifacts.
- The first run is the authoritative run. A mechanical failure may produce a
  technical retry only under the declared protocol and must preserve the first
  receipt.

## Fallback

On mechanical failure, preserve the first-run receipt and logs. Permit only a
protocol-declared technical rerun. Never tune a model, modify predictions, or
reinterpret a failed lockbox result as a successful evaluation.
