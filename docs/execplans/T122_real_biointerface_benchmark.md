# T122: Real study-held-out BioInterfaceBench and extraction evaluation

## Purpose

Build the first empirical benchmark namespace only after acquiring multiple independent openly licensed studies, then evaluate extraction under a study-held-out protocol with raw predictions, coverage, calibration and cluster-aware uncertainty.

## Preconditions

T120 and T121 are complete. The only currently admitted study is the Leeds GUV dataset, so it can be a development source but cannot constitute a held-out benchmark by itself.

## Non-goals

Do not relabel a source-local split as external validation, fabricate new study groups, infer measurements from figures, publish an empirical performance result before raw prediction artifacts are frozen, or claim biological generalization.

## Interfaces and invariants

- Required command: `python -m biointerfaceos benchmark evaluate-real --strict`.
- At least three distinct studies and laboratories, with explicit reusable licences and row-level source provenance, must be admitted before evaluation.
- Test groups are entire studies; no study, laboratory or duplicate material/protocol family may straddle development and held-out partitions.
- Prediction rows must be tied to a frozen benchmark item, parser version and source locator. Metrics require coverage, calibration and study-clustered intervals.
- Any insufficient coverage remains a blocked, non-result state rather than a zero-performance report.

## Implementation plan

1. Scout and verify at least two additional source records with reusable raw data and non-overlapping laboratory/study identity.
2. Extend T120 registry and provenance audit while retaining every raw asset and cell-level source locator.
3. Define an adjudication protocol and benchmark item schema before writing evaluators.
4. Freeze study-held-out partitions and baseline configurations; generate raw prediction, coverage, calibration and uncertainty artifacts.
5. Implement strict benchmark audit, negative leakage tests, receipt and public-boundary checks.

## Progress

- [ ] Source scouting and licence verification.
- [ ] Multi-study row-level provenance admission.
- [ ] Annotation/benchmark protocol and split freeze.
- [ ] Baseline evaluation and independent audit.

## Discoveries

- Current registry coverage is insufficient for this task and must not be stretched beyond its one-study evidence boundary.

## Decisions

- Pending source admissions.

## Validation

- The strict command must reject fewer than three studies/laboratories, a source-local “held out” label, duplicate group leakage and absent raw prediction rows.
- Successful evaluation must expose the planned uncertainty/coverage artifacts while maintaining exploratory-only claim language.

## Failure recovery

If no source satisfies both row-level location and licence requirements, preserve the negative search record, keep T122 blocked and do not use a secondary figure, inaccessible supplement or fixture as a substitute.

## Outputs

- Expanded empirical registry, raw-asset records and admission audit.
- Real benchmark protocol, frozen study splits, adjudication package, predictions and strict evaluation receipt.

## Completion note

Pending.
