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

- [x] 2026-08-12 — Verified two additional CC BY 4.0 anonymous-public data records and retained their source workbooks alongside the existing Leeds record.
- [x] 2026-08-12 — Admitted three source/study/laboratory records with URL, licence, checksum, worksheet, unit-locator and value-locator lineage.
- [x] 2026-08-12 — Froze one leave-one-study-out locator-resolution item per source and rejected registries with fewer than three sources.
- [x] 2026-08-12 — Published raw predictions, coverage, calibration and deterministic study-cluster bootstrap artifacts; passed isolated KAUST command and static checks.

## Discoveries

- The three admitted studies have heterogeneous endpoints and measurement contexts. They support a real-source locator-resolution benchmark, not an endpoint-generalising biological predictor or a model-effect analysis.

## Decisions

- Use leave-one-study-out evaluation and publish every prediction. The deterministic cell-locator baseline is deliberately scoped to source-cell resolution; its metrics cannot be promoted to biological or independent-validation claims.
- Retain the Mendeley niosome candidate as an exclusion because its public file listing supplies a PDF rather than a machine-readable row-level table.

## Validation

- The strict command must reject fewer than three studies/laboratories, a source-local “held out” label, duplicate group leakage and absent raw prediction rows.
- The strict command passes with 3 studies, 3 laboratories, 3 items and 3 raw predictions. It writes source admission, raw prediction, coverage/calibration and receipt JSON artifacts.
- `ruff`, `mypy`, eight focused tests and the isolated command passed on KAUST. The public asset audit continues to pass with empirical payloads controlled and excluded from the software replay.

## Failure recovery

If no source satisfies both row-level location and licence requirements, preserve the negative search record, keep T122 blocked and do not use a secondary figure, inaccessible supplement or fixture as a substitute.

## Outputs

- `data/empirical/R2_BENCHMARK_SOURCE_REGISTRY.json` and two additional raw workbooks.
- `src/biointerfaceos/real_benchmark_workflow.py`, CLI, three-source admission record, leave-one-study-out predictions, coverage/calibration and receipt.

## Completion note

T122 is complete at its declared source-locator scope. The benchmark uses real independent studies and held-out groups, but it does not establish biological prediction, model effectiveness or independent scientific validation; those stronger questions remain governed by T123–T124.
