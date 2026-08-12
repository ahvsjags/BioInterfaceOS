# T090 Functional-axis discovery evidence

## Result

T090 was completed on the KAUST Ibex server at implementation commit `16d070c`.
The fixture-backed discovery workflow identified two exploratory protein-corona functional axes from four samples and two validated modules. The selected `log_ratio` model was stable under bootstrap and leave-study validation, and the random-module control remained low.

The workflow is deliberately exploratory: the candidate axes are evidence-linked representations for downstream mediation and counterfactual work, not automatically accepted biological claims.

## Reproducible command

```bash
biointerfaceos discover functional-axes --fixture
```

The command was run twice to exercise deterministic resume behavior. The validated receipt was:

```text
FUNCTIONAL_AXES_VALID samples=4 modules=2 alternatives=3 candidate_axes=2 bootstrap_stability=0.930000 leave_study_stability=0.900000 random_control_stability=0.220000 uncertainty_records=2 selected_model=log_ratio lockbox_clean=true resumed=1
```

## Acceptance evidence

| Gate | Result |
|---|---|
| Candidate axes | 2 exploratory candidates, all with evidence links |
| Model comparison | 3 alternatives; `log_ratio` selected |
| Bootstrap stability | 0.93 |
| Leave-study stability | 0.90 |
| Random-module control | 0.22; control passed |
| Uncertainty | 2 bootstrap interval records |
| Target/lockbox gate | Clean; no target values exposed |
| Full test suite | 313 passed via `UV_OFFLINE=1 make check` |
| Dependency/release gate | `uv lock --check`, frozen sync, assets, catalog, lockbox, state, compileall, diff check and immutable release verification passed |

## Artifacts

- Schema: `agents/discovery/functional_axes.v1.json`
- Fixture: `tests/fixtures/agents/functional_axes_fixture.json`
- Workflow and CLI: `src/biointerfaceos/functional_axes_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/omics/functional_axes/`
- Focused tests: `tests/omics/test_functional_axes_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T091, which will estimate preregistered material–corona–outcome mediation laws using these functional axes and the existing paired/DAG evidence. If identification gates fail, the implementation must downgrade the result to association and prohibit mediation wording.
