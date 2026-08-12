# T099 Mandatory model and data ablations

## Result

T099 was completed on the KAUST Ibex server at implementation commit `e8127af`.
The workflow ran five preregistered full-versus-ablated comparisons on the same
frozen group splits, paired units, and budget. It reports paired effects,
deterministic bootstrap intervals, calibration/OOD changes, and an explicit
interface-tested missing-ablation ledger.

## Reproducible command

```bash
biointerfaceos robustness ablations --all
```

The command was run twice with deterministic resume behavior:

```text
ABLATIONS_VALID comparisons=5 rows=20 same_splits=1 same_budget=1 mean_effect=0.081000 interval_records=5 calibration_records=5 ood_records=5 missing_ablations=1 claim_blocks=0 resumed=1
```

## Paired ablation evidence

- Five modules were compared: multimodal fusion, uncertainty calibration,
  mediation path, symbolic law, and candidate-audit support. Each has four paired
  units across the same development/held-out group split and budget 8.
- The overall full-minus-ablated primary effect is `0.081000`; each comparison
  has a deterministic 64-resample interval record. Calibration and OOD RMSE
  gains are reported separately for every module.
- One non-essential provider-backed raw-data ablation is unavailable by design.
  Its `network_disabled` interface test returns `BLOCKED_EXPECTED`, the reason is
  recorded, and no associated claim is silently strengthened or blocked.
- The claim gate passes because all essential declared ablations are available,
  pairing and splits are invariant, and no held-out target is used for selection.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T078, T079, T091, T093, and T098 receipts verified by checksum |
| Ablation coverage | 5/5 essential comparisons; 20 paired rows |
| Same budget/splits | Passed for every comparison; budget 8 and frozen group split |
| Effects/intervals | 5 paired-effect records and 5 deterministic bootstrap interval records |
| Calibration/OOD | 5 calibration records and 5 OOD records |
| Missingness policy | 1 non-essential interface-blocked ablation explicitly justified; 0 claim blocks |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 331 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Lockfile, schema, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |

## Artifacts

- Schema: `agents/robustness/ablations.v1.json`
- Fixture: `tests/fixtures/robustness/ablations_fixture.json`
- Workflow and CLI: `src/biointerfaceos/ablation_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/robustness/ablations/`
- Focused tests: `tests/robustness/test_ablation_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T100: run the OOD leave-group and sensitivity suite.
