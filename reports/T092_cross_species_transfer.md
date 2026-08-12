# T092 Cross-species and biofluid transfer evidence

## Result

T092 was completed on the KAUST Ibex server at implementation commit `e893b8c`.
The workflow compared direct, functional-axis, optimal-transport, and conditional transfer methods across human–mouse and biofluid strata. Material identity, unmatched cases, leave-material validation, calibration, and abstention were recorded as separate artifacts.

## Reproducible command

```bash
biointerfaceos discover cross-species --fixture
```

The command was run twice with deterministic resume behavior:

```text
CROSS_SPECIES_VALID rows=10 strata=2 methods=4 development_materials=3 heldout_materials=2 scored_heldout=2 abstentions=2 overlap_passed=true pairing_passed=true selected_method=optimal_transport resumed=1
```

## Method and validation evidence

- Four methods were preregistered before fitting: `direct`, `functional`, `optimal_transport`, and `conditional`.
- Both strata fit on MAT-1–MAT-3 and validated on held-out MAT-4; MAT-5 was explicitly unmatched and abstained.
- The selected development comparison was `optimal_transport`, with held-out RMSE 0.000000 for human–mouse and 0.015000 for biofluid in the fixture.
- Functional-axis and conditional controls were retained in the comparison; no method was tuned on held-out material.
- The two supported held-out cases were scored and the two unsupported unmatched cases were preserved in the abstention ledger.
- Rank accuracy was reported for development material pairs, while single-material held-out strata correctly report rank as not estimable.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T056, T078, T089, and T090 checksum/contract checks passed |
| Methods | 4/4 compared in both strata |
| Pairing | 8 paired cases, 2 unmatched exclusions, no pseudo-pairs |
| Leave-material validation | MAT-4 held out in both strata; no held-out tuning |
| Overlap | Partial overlap reported; supported MAT-4 scored and unsupported MAT-5 abstained |
| Calibration | Prediction intervals and coverage reported for each method/stratum |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 317 passed via `UV_OFFLINE=1 make check` |
| Final repository gate | Assets, catalog, lockbox, state, compileall, diff check, and immutable release verification passed |

## Artifacts

- Schema: `agents/discovery/cross_species.v1.json`
- Fixture: `tests/fixtures/omics/cross_species_fixture.json`
- Workflow and CLI: `src/biointerfaceos/cross_species_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/omics/cross_species/`
- Focused tests: `tests/omics/test_cross_species_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T093: discover unit-aware symbolic design laws with nested study CV, dimensional constraints, flexible-model controls, expression stability, OOD validation, and a frozen complexity penalty.
