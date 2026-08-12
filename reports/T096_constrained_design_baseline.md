# T096 Constrained multiobjective design baseline

## Result

T096 was completed on the KAUST Ibex server at implementation commit `44aac21`.
The fixture-backed workflow froze a public component simplex, structure rules,
objective definitions, penalty weights, a common budget, observed controls, and
the Pareto dominance policy before candidate scoring. It compared deterministic
enumeration, NSGA-II-style ranking, and BO-style penalized ranking while retaining
invalid and unsupported candidates in separate audit ledgers.

## Reproducible command

```bash
biointerfaceos design baseline --fixture
```

The command was run twice with deterministic resume behavior:

```text
DESIGN_BASELINE_VALID candidates=9 valid_candidates=7 invalid_candidates=2 supported_candidates=6 methods=3 constraint_pass_rate=1.000000 controls_recovered=2 controls_total=2 pareto_members=4 abstentions=1 selected_method=bo_style resumed=1
```

## Design and support evidence

- Seven of nine candidates passed the simplex and structure constraints; the two
  invalid candidates remain auditable as a simplex violation and a structure
  violation. The measured constraint pass rate among valid candidates is 1.0.
- Uncertainty and applicability-domain penalties are active in every method's
  penalized score. The high-AD candidate is excluded from supported scoring and
  retained as one explicit abstention.
- Both predefined observed controls (`CTRL-A`, `CTRL-B`) are recovered by the
  bounded proposal sets. All methods use budget 6 and the same frozen inputs.
- Four supported candidates form the reproducible Pareto set under maximize
  performance/novelty and minimize risk. The selected method is `bo_style` under
  the deterministic control-recovery tie-break.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T041, T078, T090, and T095 checksums/contracts verified |
| Candidate ledger | 9 total; 7 valid; 2 invalid retained |
| Constraints | Simplex/structure validation passed; constraint pass rate 1.0 |
| Penalties | Uncertainty and AD penalties active; 6 supported candidates |
| Controls | 2/2 observed controls recovered |
| Pareto | 4 members; deterministic and reproducible |
| OOD policy | 1 unsupported candidate abstained and preserved |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 325 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Lockfile, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |

## Artifacts

- Schema: `agents/design/constrained_baseline.v1.json`
- Fixture: `tests/fixtures/design/constrained_design_fixture.json`
- Workflow and CLI: `src/biointerfaceos/design_baseline_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/design/baseline/`
- Focused tests: `tests/design/test_design_baseline_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T097: implement target-corona conditional generative design,
subject to a data-sufficiency gate and predefined comparisons against the
constrained baseline.
