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

## Progress

- [x] Screened two official, pre-cutoff CC0 candidates with locally hashed
  small author-result workbooks: PXD016229 (Leiden University; four
  source-labelled serum conditions) and PXD054751 (Sapienza University of Rome;
  five source-labelled plasma conditions). The strict receipt preserves two
  laboratories and nine source conditions, but no admitted target.
- [x] Installed `python -m biointerfaceos model audit-cc0-target-admission
  --strict`. It validates the candidate registry, fails if a candidate is
  silently promoted, and writes an immutable read-only decision and receipt.
- [x] Screened an independent, versioned expansion tranche: PXD053359 (six
  TopPIC result TSVs) and PXD050779 (one TopPIC workbook), both official
  pre-cutoff CC0 human-plasma sources attributed to Michigan State University.
  The new audit preserves seven local file hashes but admits zero targets.
- [ ] Find a reusable CC0 source asset with a source-matched numeric material or
  size covariate map for every candidate analysis unit.
- [ ] Freeze a shared preprocessing endpoint and an explicit analysis-unit
  manifest across at least two independent laboratories.
- [ ] Create T121 Amendment v1.0.1, then hand only its frozen target to T123.

## Discoveries

- PXD016229 exposes source-labelled quantitative columns for EndoTAG-1,
  AmBisome, Myocet and a no-liposome control; it does not supply a numeric
  material/size covariate map in the selected CC0 workbook.
- PXD054751 exposes five source-labelled plasma-LNP conditions and three
  author-labelled intensity columns per condition. Its formulation labels are
  categorical descriptions, not reusable numeric covariates, and the A1-A3
  suffixes do not establish biological-replicate status.
- The two workbooks use author-specific quantitative outputs. Their numbers are
  not a common cross-study abundance scale and are not concatenated.
- PXD053359 describes with/without-small-molecule processing in project
  metadata, but its six screened TopPIC TSVs only expose S2/S4 acquisition
  labels; no official screened asset maps those labels to numeric material or
  size covariates per analysis unit.
- PXD050779's workbook describes three parallel protein-corona samples from a
  commercial human-plasma source. Its Corona1/2/3 labels and path tokens remain
  source identifiers, not inferred covariates or biological-replicate labels.

## Decisions

- The audit status is `BLOCKED_NO_CC0_COMMON_TARGET`, with zero admissible
  targets. This is a data-coverage result, not a failed model run.
- Do not create T121 Amendment v1.0.1 until the required covariate, endpoint and
  analysis-unit evidence is available. The current T121 plan remains immutable.
- Preserve both candidate assets and their hashes under ignored screening storage;
  do not download their bulk raw files until a source passes the metadata gate.
- The expansion tranche is also non-admitted: its two sources come from one
  laboratory, use heterogeneous top-down outputs, and establish neither a
  numeric source-matched covariate map nor a two-laboratory common endpoint.

## Validation

- 2026-08-13: `python -m biointerfaceos model audit-cc0-target-admission
  --strict` verified two candidates, two laboratories and nine source conditions
  from `docs/data/R2_T129_CC0_TARGET_ADMISSION_REGISTRY.json`, and wrote
  `reports/review_round_2/cc0_target_admission/v1.0.0/`.
- The receipt is read-only and asserts `target_status=NOT_FROZEN`,
  `model_use=PROHIBITED`, zero admissible targets and false model/OOD/independent
  validation fields. Regression tests reject strict-mode omission, candidate
  promotion and receipt tampering.
- 2026-08-13: `python -m biointerfaceos model audit-cc0-target-discovery
  --strict` recorded PXD053359 and PXD050779 separately in
  `docs/data/R2_T129_CC0_TARGET_DISCOVERY_REGISTRY.json`. It verifies two
  candidates, one laboratory and seven screened result assets, with
  `BLOCKED_CC0_EXPANSION_NO_SOURCE_MATCHED_NUMERIC_COVARIATES` and all model,
  OOD and independent-validation fields false.

## Acceptance evidence

- Candidate registry, immutable admission/non-admission receipt, source-asset
  checksums, and reviewer-readable missingness decisions.
- On admission only: versioned T121 amendment, common preprocessing outputs,
  study-held-out split and feature manifest. A model result is not an acceptance
  artifact for this task.

## Completion note

Pending.
