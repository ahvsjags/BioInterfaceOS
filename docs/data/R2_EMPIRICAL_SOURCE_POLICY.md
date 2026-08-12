# R2 empirical-source admission policy

This register is a source-admission record, not a benchmark, model evaluation, statistical analysis, or independent scientific validation.

## Admission rules

- Admit only source files reachable without credentials from a stable landing page or DOI/accession and carrying an explicit reusable licence.
- Retain the exact downloaded raw asset, its direct source URL, byte count, SHA-256 digest, original worksheet, row, column, independent unit, and measured value.
- Require source, study, laboratory, affiliation, material, biological system, protocol and endpoint fields for every admitted observation after source-level inheritance.
- Treat an absent, restrictive, incompatible, or unverifiable licence as an exclusion. Do not copy it into `data/empirical` or use it for an empirical statement.
- Reject fixtures, synthetic records, mocked values, unlocatable cells, and secondary summaries as primary empirical rows.

## Current boundary

`bioif-r2-open-observations-v1.1.0` admits a CC BY 4.0 University of Leeds dataset (DOI `10.5518/1171`) whose landing record exposes four anonymous-public XLSX raw-data files. The first admitted endpoint is the workbook's released GUV shrinking-rate table. The audit reads the original cells during every run; it does not maintain a separately edited result table.

This one-study development source unlocks only planning work. It does not satisfy the multi-study, multi-laboratory, held-out benchmark, model-effect, or independent-evaluator gates in T122–T124.
