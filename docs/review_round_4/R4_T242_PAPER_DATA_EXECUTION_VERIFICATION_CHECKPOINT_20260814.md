# R4-T242: Paper-data execution verification checkpoint

Date: 2026-08-14  
Status: `AUTHOR_SIDE_PAPER_DATA_ROUTES_VERIFIED_EXTERNAL_GATES_OPEN`

## Verified execution routes

The current checkout independently verified the paper-data fallback routes after the canonical release-hash repair:

| Route | Verification result | Accounting |
|---|---|---|
| T222 published-paper data fallback | `VERIFY_VALID` | 4 routes, 16 references, 4 source registries, 8 source maps, 4 reports |
| T195 three-lab common-target execution | `VERIFY_VALID` | 809 observations, 9 frozen targets, 3 laboratories, 85 measurement batches |
| PMC10257194 paper source audit | `VERIFY_VALID` | 4,362 source cells, 97 shared proteins, 45 batches, 45 biological units |
| PMC10257194 paper OOD | `VERIFY_VALID` | 2,724 development observations, 4,362 external observations, 45 batches, 3 models |
| T198 paper-cohort missingness | `VERIFY_VALID` | 8 thresholds, primary threshold 10, 666 qualified batches, 141 biological units, 17,026 observations |

The corresponding commands were run with `--strict` from the current worktree:

```text
.venv\\Scripts\\python.exe -m biointerfaceos data verify-r4-t222-paper-data-fallback --strict
.venv\\Scripts\\python.exe -m biointerfaceos data verify-r4-t195-three-lab-common-target --strict
.venv\\Scripts\\python.exe -m biointerfaceos data verify-r4-pmc10257194-paper-source --strict
.venv\\Scripts\\python.exe -m biointerfaceos data verify-r4-pmc10257194-paper-ood --strict
.venv\\Scripts\\python.exe -m biointerfaceos data verify-r4-t198-paper-cohort-missingness --strict
```

These are the locked project environment commands used by this Windows checkout.

## Scientific interpretation

This checkpoint confirms that the project has executable, auditable real observations from published full text, supplementary workbooks and public accessions. It strengthens the author-side data, statistics, model and OOD evidence modules. It does not change the biological-unit boundaries: measurement batches and technical replicates are not silently promoted to independent donors.

## External-gate boundary

All verified routes remain author-side or paper-data evidence. They do not create:

- a non-author protected lockbox evaluator receipt;
- a no-author scientific reproduction receipt;
- two independent external adoption receipts; or
- a DOI archive read-back.

Therefore `independent_validation`, `external_scientific_reproduction`, `external_user_adoption`, `doi_archived`, and `scientific_submission_ready` remain `false`.
