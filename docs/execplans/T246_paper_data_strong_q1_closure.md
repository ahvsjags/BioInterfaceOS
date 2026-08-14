# T246: paper-data strong-Q1 closure

## Purpose

Convert the verified full-text and public-accession routes into one bounded,
release-ready empirical evidence layer, then close the remaining independent
evaluation, external reproduction, adoption and DOI gates with real receipts.
The scientific claim is technical/source-conditional portability unless the
evidence supports a stronger biological interpretation.

## Preconditions

- T192/T193/T195 three-source common-target receipts.
- T194 PMC9633814 technical cross-core receipt.
- T180/T181/T198 biological paper-cohort receipts.
- T203/T209 paper-derived OOD receipts.
- T200/T217 statistical closure and estimand/multiplicity records.
- T245 local, KAUST and GitHub CI evidence.
- Fixed external handoff at `docs/external/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.md`.

## Non-goals

- No wet-lab experiment is simulated or invented.
- No donor, laboratory, evaluator, user or DOI receipt is synthesized.
- No pooled abundance scale is treated as a cross-study measurement.
- No technical replicate is promoted to biological effective n.

## Interfaces and invariants

- Every scientific number must point to a hash-bound source cell, output and
  declared biological/laboratory unit.
- T195's nine-accession, leave-one-source-anchor-out contrast remains the sole
  primary cross-source estimand.
- T194 remains a technical common-aliquot, core-held-out sensitivity route.
- T203/T209 remain author-run, analysis-only paper-data OOD routes.
- `independent_validation`, `external_scientific_reproduction`,
  `external_user_adoption`, `doi_archived` and
  `scientific_submission_ready` remain false until actual receipts pass audit.

## Implementation plan

1. Freeze the T246 claim boundary and role-separated editorial scores.
2. Bind T192--T209, T245 and the T246 documents to a new immutable release;
   regenerate the release manifest and archive sidecar.
3. Run strict execution-pack validation, clean-room replay and the KAUST
   `make check`/data verification suite from the release.
4. Keep the fixed release and external handoff visible in GitHub Issue #2;
   request one protected non-author evaluator, one no-author reproducer and two
   distinct external users.
5. Accept only signed, identity/COI/environment/hash-bound receipts through the
   existing preflight and verification schemas.
6. Deposit the exact release with an authenticated archival service and verify
   the read-back hash and version DOI.
7. Run the final multi-agent editorial gate and update the manuscript claim
   matrix. Set `scientific_submission_ready=true` only if every hard predicate
   and every module score is independently supported at >=90.

## Progress

- [x] 2026-08-14 — Audited the existing paper-data fallback and T194/T195
  boundaries.
- [x] 2026-08-14 — Wrote the conservative T246 goal and role-separated panel.
- [ ] Bind the current post-CI state to a new immutable public release.
- [ ] Receive and verify non-author lockbox and no-author reproduction receipts.
- [ ] Receive and verify two distinct external adoption receipts.
- [ ] Complete authenticated DOI deposit and read-back.
- [ ] Run final submission gate.

## Discoveries

- The project already contains real paper-attached measurements; the key gap is
  not absence of numbers but the distinction between technical laboratory
  replication and independent biological replication.
- The PMC9633814 route supplies 12 core-held-out folds but only one common pooled
  biological aliquot.
- T192/T195 supply three public laboratory anchors and nine exact common targets,
  but the biological-unit semantics are heterogeneous and must remain explicit.
- The strongest remaining blockers are external and cannot be closed by more
  author-side reruns.

## Decisions

- Use the paper-data routes to close internal model/statistical execution, not to
  manufacture independent validation.
- Treat the related multi-core uniform-processing paper as corroboration or
  sensitivity evidence when its blinded-core/raw-data boundary applies.
- Keep all negative and source-specific OOD results in the manuscript.

## Validation

Expected release checks:

```text
python scripts/validate_execution_pack.py
make check
python -m biointerfaceos data verify-r4-t192-three-lab-common-target --strict
python -m biointerfaceos data verify-r4-t194-fulltext-core-facility --strict
python -m biointerfaceos data verify-r4-t195-three-lab-common-target --strict
```

Expected gate state before real third-party receipts:

```text
independent_validation=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

## Failure recovery

- Preserve all failed candidate screens and prior immutable releases.
- If a source hash, license or unit map changes, invalidate downstream results
  and rerun the affected source audit before model execution.
- If an external receipt is malformed or self-certified, reject it through the
  preflight; do not edit it into compliance.
- Never move or overwrite an immutable tag.

## Outputs

- `docs/review_round_4/R4_T246_PAPER_DATA_STRONG_Q1_CLOSURE_GOAL_20260814.md`
- `docs/review_round_4/R4_T246_MULTI_AGENT_EDITORIAL_REVIEW_20260814.md`
- `docs/review_round_4/R4_T246_MULTI_AGENT_EDITORIAL_REVIEW_20260814.json`
- new immutable release manifest and archive sidecar
- external evaluator/reproduction/adoption receipts, if and only if supplied
  by real non-author parties
- final gate ledger

## Completion note

T246 is not complete. The internal paper-data and engineering evidence is
organized and scored, while the external hard gates remain open. Completion
requires the receipts listed above and a post-receipt editorial review.

