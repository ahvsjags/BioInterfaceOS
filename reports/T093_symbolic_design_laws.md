# T093 Unit-aware symbolic design-law evidence

## Result

T093 was completed on the KAUST Ibex server at implementation commit `d961bdb`.
The workflow discovered bounded symbolic expressions over normalized material features and T090 functional axes, enforced dimensional consistency, compared two flexible controls, used nested study-level CV, measured bootstrap expression stability, evaluated OOD validation, and applied a claim gate.

## Reproducible command

```bash
biointerfaceos discover symbolic-laws --fixture
```

The command was run twice with deterministic resume behavior:

```text
SYMBOLIC_LAWS_VALID candidates=4 unit_valid=3 rejected=1 nested_folds=4 controls=2 bootstrap_stability=1.000000 ood_passed=true selected_expression=0.62*surface_norm + 0.28*functional_axis + 0.10*charge_norm fallback=false resumed=1
```

## Candidate and gate evidence

- Three of four candidates were unit-valid. LAW-004 was rejected because its derived units were `1` and `mg^2` while the target unit was `1`.
- The selected expression was `0.62*surface_norm + 0.28*functional_axis + 0.10*charge_norm`.
- Nested study-CV used four outer studies with disjoint inner studies; no outer fold was tuned on its held-out study.
- GAM-like and tree-like flexible controls were evaluated with `selection_role=control_only`, so they could not rewrite the preregistered symbolic selection rule.
- Complexity penalty 0.005, bootstrap seed 93, and 32 bootstrap replicates were frozen before fitting.
- Bootstrap expression stability was 1.0 and the selected candidate passed the OOD RMSE threshold.
- Claim gate status was `symbolic_law_permitted=true`; fallback was not activated.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T071, T089, and T090 checksums/contracts verified |
| Dimensional constraints | 3 valid candidates; 1 dimensional rejection preserved |
| Nested study CV | 4 disjoint outer folds |
| Flexible controls | GAM/tree controls evaluated, control-only role |
| Stability/OOD | Bootstrap stability 1.0; OOD passed |
| Complexity | Frozen before fitting at 0.005 |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 319 passed via `UV_OFFLINE=1 make check` |
| Final repository gate | Dependencies, assets, catalog, lockbox, state, compileall, diff check, and immutable release verification passed |

## Artifacts

- Schema: `agents/discovery/symbolic_laws.v1.json`
- Fixture: `tests/fixtures/omics/symbolic_laws_fixture.json`
- Workflow and CLI: `src/biointerfaceos/symbolic_laws_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/omics/symbolic_laws/`
- Focused tests: `tests/omics/test_symbolic_laws_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T094: test protocol-correction and reversal hypotheses with predefined protocol variables, comparable-study analyses, Simpson/reversal tests, and a claim gate.
