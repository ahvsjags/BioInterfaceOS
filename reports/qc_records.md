# Physical and Statistical Plausibility QC

- mode: strict
- records: 7
- flags: 5 (4 critical, 1 warning)
- quarantined records: 4
- clean-control false-positive rate: 0.000
- injected-error recall: 1.000

Rules cover bounded fractions and percentages, non-negative concentrations and dispersion, unique positive sample counts, and a candidate SEM/SD label-confusion check. Critical records are quarantined; warning records remain review-only.

## Flags

- qc:bad-fraction:FRACTION_OUT_OF_RANGE:fraction CRITICAL FRACTION_OUT_OF_RANGE: fraction must lie in [0, 1]
- qc:bad-concentration:NEGATIVE_CONCENTRATION:concentration CRITICAL NEGATIVE_CONCENTRATION: concentration cannot be negative
- qc:duplicate-sample:DUPLICATE_SAMPLE_COUNT:sample_size CRITICAL DUPLICATE_SAMPLE_COUNT: sample_size appears more than once in the same record
- qc:sem-confusion:SEM_SD_CONFUSION_CANDIDATE:sd WARNING SEM_SD_CONFUSION_CANDIDATE: sem equals sd despite sample_size > 1; uncertainty labels may be confused
- qc:bad-percent:PERCENT_OUT_OF_RANGE:percent CRITICAL PERCENT_OUT_OF_RANGE: percent must lie in [0, 100]
