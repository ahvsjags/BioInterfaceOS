# T180/T181: PXD017052 141-subject biological-cohort OOD

## Purpose

Convert a paper-attached, publicly obtainable human plasma protein-corona matrix into a byte-traceable biological-unit audit and run a separately frozen exploratory OOD analysis. The work addresses the previous effective-n gap without mislabeling pooled technical batches as independent biological samples.

## Preconditions

- Frozen R3 rank ledger and sequence-feature table.
- Public CC-BY-4.0 article PMC7376165 and its Supplementary Data 5 workbook.
- Existing R3 analysis protocol and source-local rank estimand.
- Python 3.11 with `openpyxl` and `numpy`.

## Non-goals

- No new laboratory anchor or independent lineage claim.
- No protected lockbox evaluation, non-author reproduction, clinical validation, DOI issuance, or adoption claim.
- No concatenation of raw abundance scales across studies.
- No deletion of missing values or negative model results.

## Interfaces and invariants

- T180 registry: `docs/data/R4_T180_PXD017052_NSCLC_SOURCE_REGISTRY.json`.
- T180 audit: `src/biointerfaceos/r4_pxd017052_nsclc_source_audit.py`.
- T180 CLI: `audit-r4-pxd017052-nsclc-source` and `verify-r4-pxd017052-nsclc-source`.
- T181 protocol: `docs/data/R4_T181_PXD017052_NSCLC_BIOLOGICAL_OOD_PROTOCOL.json`.
- T181 execution: `src/biointerfaceos/r4_pxd017052_nsclc_biological_ood.py`.
- T181 CLI: `evaluate-r4-pxd017052-nsclc-biological-ood` and `verify-r4-pxd017052-nsclc-biological-ood`.
- `scientific_submission_ready` remains `false`.
- External data are excluded from feature/alpha selection and model refitting until after the frozen R3 fit population is established.

## Implementation plan

1. Freeze the Supplementary Data 5 asset hash and paper/source semantics.
2. Map only uniquely resolved members of the frozen 99-target R3 universe.
3. Preserve `NA` and zero states; exclude depleted-plasma control from NP-corona analysis.
4. Generate a source-cell map retaining workbook, row, cell, subject, particle and batch provenance.
5. Freeze the T181 estimand, thresholds, nested selection, biological-unit bootstrap, paired ablation and negative-control rules.
6. Fit only on 2,724 R3 development observations and score the 141-subject cohort.
7. Record model metrics, subject metrics, prediction rows, selection rows, ablation and negative-control artifacts.
8. Re-review with independent methods, domain and editorial agents; preserve the lowest defensible claims.

## Progress

- [x] 2026-08-13 — Screened PXD065103 and rejected it for direct matrix admission because only proprietary `.sne` search files and raw files were available.
- [x] 2026-08-13 — Reused the paper-attached PMC7376165 Supplementary Data 5 workbook; SHA-256 `2f133be55c63b5959c19381f830c83304192063403c5f1ab8e2a8e3f3c7dab74`.
- [x] 2026-08-13 — T180 audit: 141 biological units, 705 batches, 666 qualified batches, 34 shared targets, 23,970 cells, 17,330 positive cells, 6,640 `AUTHOR_NA` cells.
- [x] 2026-08-13 — T181 execution: 17,026 external observations; 3 models; subject-equal cluster bootstrap; paired ablation; 256 permutation negative-control resamples.
- [x] 2026-08-13 — Three-agent read-only editorial re-review completed; verdict remains Major Revision.
- [ ] Obtain real non-author lockbox/evaluator receipt.
- [ ] Obtain no-author end-to-end reproduction receipt.
- [ ] Obtain independent adoption receipts and immutable DOI release.

## Discoveries

- The paper-attached matrix contains 141 individual subjects and 5 NP conditions but only 34 uniquely mapped members of the frozen target intersection.
- Qualified-batch filtering leaves 666/705 batches; the number of qualified batches varies by subject, so missingness/qualification remains a sensitivity-analysis issue.
- Full model subject-equal Spearman is `0.06845`; composition-only is `0.03917`; paired delta is `0.02928`; negative-control upper-tail `p=0.24125`.
- Full model has lower rank-error performance than the constant baseline on MAE and RMSE, so the positive paired delta cannot be called practical predictive utility.

## Decisions

- Call the evidence `same-laboratory biological-cohort OOD`, not independent validation.
- Use subject-level cluster resampling for the primary exploratory uncertainty summary.
- Keep T180/T181 separate from the public R8 tag until the release manifest is explicitly refreshed.
- Keep all external-evidence gates false until contributor-held receipts are independently verified.

## Validation

```text
$env:PYTHONPATH='src'; python -m pytest -q tests/review_round_3 tests/review_round_4
# expected: all review_round_3/review_round_4 tests pass

$env:PYTHONPATH='src'; python -c "from biointerfaceos.cli import main; import sys; sys.argv=['biointerfaceos','data','verify-r4-pxd017052-nsclc-source','--assets-root','data/raw/r4_candidate_pxd017052_nsclc','--strict']; raise SystemExit(main())"
$env:PYTHONPATH='src'; python -c "from biointerfaceos.cli import main; import sys; sys.argv=['biointerfaceos','data','verify-r4-pxd017052-nsclc-biological-ood','--strict']; raise SystemExit(main())"
```

## Failure recovery

T180/T181 execution is one-shot. Never overwrite an existing receipt or mutate a source map in place. If an input changes, create a new versioned registry/protocol/output directory and recompute all hashes. Preserve candidate raw assets outside Git's tracked public source unless the public release policy explicitly changes.

## Outputs

- T180 registry, source-cell map, report and receipt.
- T181 protocol, rank ledger, predictions, batch metrics, biological-unit metrics, model metrics, nested selection, negative-control rows, parameters, report and receipt.
- T181 three-role editorial re-review: `docs/review_round_4/R4_T181_MULTI_AGENT_REVIEW_20260813.md`.

## Completion note

T180/T181 materially improve real-data compatibility and effective biological-unit accounting. They do not close protected independent evaluation, no-author reproduction, external adoption, DOI provenance, or the strict strong-Q1 submission gate.
