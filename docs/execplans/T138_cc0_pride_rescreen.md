# T138: Bounded CC0 PRIDE rescreen for a real T129 target

## Purpose

Recheck the official PRIDE Archive with a broader, explicit query set after the
earlier T129 screens, while preserving the frozen 2024-12-31 cutoff and
CC0-only route.  The task records only the source metadata and small result
assets actually inspected; it does not infer material properties from labels.

## Evidence boundary

- Eight official API queries returned 83 unique projects; 25 were CC0, human
  and pre-cutoff at project-metadata level.
- Seven newly unreviewed directory leads were enumerated without bulk transfer.
- Only PXD019524's six small CSVs and PXD046988's 523,887-byte table were read.
  Their local SHA-256 values and publisher SHA-1 values are recorded in the
  registry.
- PXD019524 supplies categorical GO/FLG result-file labels and author TMT
  output.  PXD046988 supplies categorical GO/GNP, medium/plasma, time and
  replicate labels in one author DIA table.  Neither source supplies an
  analysis-unit-to-numeric-material/size map, a frozen human-biofluid unit
  manifest, a disclosed independent laboratory or a shared cross-study endpoint.

## Invariants

- No current or future file-name, sample-name, material-name or replicate token
  becomes a predictive covariate.
- This screening adds no source to the CC0 cohort, permits no model fitting and
  leaves T121 Amendment v1.0.1, T124 and T128 unavailable.
- The former receipts remain immutable; T129 receives a new consolidated
  version with the two non-admitted sources explicitly counted.

## Validation

```bash
python -m biointerfaceos model audit-cc0-target-rescreen --strict
python -m biointerfaceos model audit-t129-current-target-evidence --strict
python -m pytest tests/model/test_cc0_target_rescreen.py tests/model/test_t129_current_target_evidence.py -q
```

## Completion evidence

`reports/review_round_2/cc0_target_rescreen/v1.0.0/` contains the immutable
non-admission report and receipt.  It is a discovery record only, not a
scientific result, independent validation or submission-readiness claim.
