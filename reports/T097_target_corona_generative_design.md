# T097 Target-corona conditional generative design

## Result

T097 was completed on the KAUST Ibex server at implementation commit `bb7f3b6`.
The workflow freezes a target-corona conditioning contract, first applies a data
sufficiency gate, and then compares a bounded conditional generator with the T096
BO-style baseline. OOD proposals abstain; conditioning, uncertainty-penalty, and
support-restriction ablations are retained in an auditable matrix.

## Reproducible command

```bash
biointerfaceos design generative --fixture
```

The command was run twice with deterministic resume behavior:

```text
DESIGN_GENERATIVE_VALID rows=12 groups=4 heldout=4 sufficiency_passed=1 generator_attempted=1 baseline_validity=0.666667 generator_validity=0.833333 novelty_gain=0.132000 pareto_gain=1 ood_uncertainty_delta=-0.100000 ablations=3 selected_method=conditional_generator fallback=0 abstentions=2 resumed=1
```

## Gate and comparison evidence

- The sufficiency gate passed with 4 independent groups, 8 training rows, 4
  held-out rows, full target-coverage flags, and support density 0.875 against a
  0.75 threshold.
- The conditional generator improved validity from `0.666667` to `0.833333`,
  improved supported novelty by `0.132000`, and added one Pareto member under the
  frozen comparison policy.
- OOD uncertainty changed by `-0.100000` relative to the baseline, satisfying the
  no-worse OOD uncertainty gate. Two OOD proposals abstained and remain in the
  proposal ledger.
- Three predefined ablations were complete. The workflow also implements the
  explicit fallback path: if the sufficiency gate fails or the generator does not
  beat the baseline under all frozen criteria, T096's BO-style baseline is kept.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T079 multimodal and T096 constrained-design receipts verified by checksum |
| Data sufficiency | 4 groups, 8 train, 4 held-out; gate passed |
| Baseline comparison | Generator validity 0.833333 vs baseline 0.666667 |
| Novelty/Pareto | Novelty gain 0.132000; Pareto gain 1 |
| OOD uncertainty | Delta -0.100000; no-worse criterion passed; 2 abstentions retained |
| Ablations | Conditioning, uncertainty penalty, and support restriction: 3/3 complete |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 327 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Lockfile, schema, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |

## Artifacts

- Schema: `agents/design/target_corona_generative.v1.json`
- Fixture: `tests/fixtures/design/target_corona_generative_fixture.json`
- Workflow and CLI: `src/biointerfaceos/target_corona_generative_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/design/generative/`
- Focused tests: `tests/design/test_target_corona_generative_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T098: create candidate audit packets and retrospective
validation for the supported design outputs.
