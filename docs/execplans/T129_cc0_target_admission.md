# T129: CC0 human protein-corona target admission and plan amendment

## Purpose

Resolve the real-data gap exposed by T123 without converting heterogeneous
author results into a model dataset. Under the public CC0-only rule, identify
and audit a human-biofluid protein-corona source that can supply the missing
source-matched numeric covariates and biological analysis units. If such a
source is admitted, freeze a versioned amendment to T121 before any model run.

## Trigger and scope

T123 parsed 23 real author-result files from three independent studies and
found zero compatible cross-study targets. This task addresses R2-01 and R2-03;
it does not alter the existing immutable T123 receipts or relabel them as model
evidence.

## Admission invariants

- The candidate must disclose a reusable licence compatible with the public
  CC0-only development cohort, a human biofluid context, and a stable source
  identifier.
- Source files must map each admissible biological analysis unit to the actual
  material/composition, numeric size or other predeclared covariates, assay, and
  protein-crown endpoint. No L/S, TMT channel, fraction, study, laboratory,
  accession, author label, or file path may be inferred or used as a predictive
  feature.
- At least two independent studies/laboratories must support one identically
  defined endpoint after one shared preprocessing rule. Author label-free, TMT,
  and semiquantitative values must not be concatenated.
- Before fitting, issue a versioned T121 amendment freezing units, endpoint,
  preprocessing, allowed features, study-held-out split, nested selection,
  negative controls, and analysis code hash. The old plan remains immutable.
- If any condition fails, preserve raw inputs and write a strict non-admission
  receipt. Do not fit a model, report ablations/OOD results, or unblock T124.

## Implementation plan

1. Build an evidence-backed candidate registry from official source metadata and
   raw/result asset inspection; record licence, organism, biofluid, laboratory,
   covariate map, endpoint scale, units, and checksum/byte provenance.
2. Run a fail-closed source admission audit. Preserve rejected candidates and
   state the exact missing condition rather than filling fields by inference.
3. If a compatible two-study endpoint exists, create T121 Amendment v1.0.1 and
   freeze its hashes before configuring a new T123 model gate. Otherwise publish
   the non-admission receipt and continue source discovery.
4. Route only a successfully frozen target to T123 paired models; retain T124,
   T126, T127, and T128 as blocked until their independent gates are met.

## Acceptance evidence

- Candidate registry, immutable admission/non-admission receipt, source-asset
  checksums, and reviewer-readable missingness decisions.
- On admission only: versioned T121 amendment, common preprocessing outputs,
  study-held-out split and feature manifest. A model result is not an acceptance
  artifact for this task.

## Completion note

Pending.
