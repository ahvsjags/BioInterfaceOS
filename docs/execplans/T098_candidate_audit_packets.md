# T098 Create candidate audit packets and retrospective validation

## Objective

Turn the supported T096/T097 design outputs into candidate-level audit packets
and run a retrospective validation protocol using only later, public evidence
metadata. Each candidate must carry provenance, applicability-domain, uncertainty,
novelty, nearest-evidence, perturbation-stability, and allowed-language fields.

## Scope and constraints

- Use the frozen T096 constrained baseline and T097 generative-design receipts,
  ledgers, and manifests as the only candidate-generation inputs.
- Deduplicate candidate formulations by component, structure, conditioning, and
  method fingerprints before any ranking or retrospective match evaluation.
- Freeze AD and uncertainty thresholds, nearest-neighbor distance, perturbation
  budget, temporal cutoff, retrospective matching rules, and wording gates before
  reading later evidence metadata.
- Evaluate candidates against later public metadata without tuning candidate
  selection or thresholds to the retrospective outcomes. Keep temporal matches
  descriptive and exclude any future evidence from design-time scoring.
- Exclude high-OOD, unsafe, invalid, or unresolved candidates from supported
  claims; retain them in an explicit rejection/abstention ledger.
- Remain offline and fixture-backed: no network, credentials, raw download, locked
  payload, or hidden outcome access.

## Planned implementation

1. Add `agents/design/candidate_audit.v1.json` for deduplication, provenance,
   AD/uncertainty, novelty, perturbation, temporal, and language contracts.
2. Add `tests/fixtures/design/candidate_audit_fixture.json` with supported,
   duplicate, high-OOD, unstable, unsafe, and retrospective metadata cases.
3. Implement `src/biointerfaceos/candidate_audit_workflow.py` with candidate
   fingerprinting, neighbor and novelty checks, perturbation stability, temporal
   matching, and claim-language gating.
4. Expose `biointerfaceos design audit-candidates --fixture` and emit candidate
   cards, deduplication audit, evidence-neighbor audit, robustness ledger,
   retrospective validation, abstention/failure ledgers, lockbox scan, receipt,
   and manifest under `reports/design/candidates/`.
5. Add focused tests for deduplication, OOD/uncertainty exclusion, perturbation
   stability, temporal matching without tuning, and allowed wording.
6. Run focused tests and the complete lockfile, quality, data, release, state, and
   diff gates before recording T098.

## Acceptance criteria

- Candidate packets are provenance-complete, deduplicated, and reproducible.
- AD, uncertainty, nearest evidence, perturbation stability, and allowed wording
  are present for every retained candidate.
- High-OOD or unsafe candidates are excluded from supported wording and preserved
  in the abstention ledger.
- Any temporal match is evaluated descriptively without changing candidate
  selection or tuning thresholds.
- Full repository and immutable-release gates pass.

## Failure fallback

Retain only the supported, low-OOD candidates with complete provenance and label
all remaining designs exploratory. If retrospective evidence is unavailable or
ambiguous, preserve the audit packet and report the match as unresolved rather
than treating it as validation.
