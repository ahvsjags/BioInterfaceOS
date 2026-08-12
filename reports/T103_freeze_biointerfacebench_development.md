# T103 Freeze BioInterfaceBench development release

## Result

T103 was completed on the KAUST Ibex server at implementation commit `0e78fd9`.
The new `benchmark freeze-dev` workflow verifies the benchmark instance,
grader, statistical-baseline, representation, frozen-split, and T102 negative
control receipts before emitting an immutable semantic-versioned release.

## Reproducible command

```bash
biointerfaceos benchmark freeze-dev --fixture
```

Observed first and resumed runs:

```text
BENCHMARK_FREEZE_VALID release_id=biointerfacebench-dev-v1.0.0 version=1.0.0 instances=16 train=8 validation=8 graders=3 baselines=5 representations=4 public_hidden_separated=true negative_controls_clean=true resumed=1 target_values_exposed=false
```

## Freeze evidence

- Six prerequisite receipts are checksum-pinned: T067 instances, T068 graders,
  T069 statistical baselines, T070 representations, T065 split, and T102
  negative controls.
- The release contains 16 benchmark instances across 8 families, with an 8/8
  train/validation split, 3 grader cases, 5 statistical baselines, and 4
  representation baselines.
- Public instance records and the metadata-only hidden registry are separated;
  no hidden target reference or target hash appears in the public layer.
- Release artifacts are immutable: rerunning produces `resumed=1`, while any
  mutation or checksum mismatch is rejected without overwrite.
- T102 strict negative controls remain clean with zero critical leakage.

## Acceptance evidence

| Gate | Result |
|---|---|
| Version | `biointerfacebench-dev-v1.0.0` / semantic version `1.0.0` |
| Benchmark | 16 instances, 8 families, 8 train / 8 validation |
| Graders | 3 cases |
| Baselines | 5 statistical, 4 representation |
| Layer separation | Public/hidden separated; target values exposed false |
| Immutability | First freeze and byte-stable resume passed; tamper test passed |
| Full test suite | 340 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Repository gates | Lockfile, sync, schema, assets, catalog, lockbox, immutable data release, state, compileall, and diff checks passed |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |

## Artifacts

- Schema: `agents/benchmark/freeze_dev.v1.json`
- Fixture: `tests/fixtures/benchmark/freeze_dev_fixture.json`
- Workflow and CLI: `src/biointerfaceos/benchmark_freeze.py`, `src/biointerfaceos/cli.py`
- Tests: `tests/benchmark/test_benchmark_freeze.py`
- Release directory: `reports/benchmark/releases/biointerfacebench-dev-v1.0.0/`
- Release manifest SHA-256: `7e9e200cd3f71264d3926d846030c9186d9b2b0d1c03f63fa6326ce18e00adaf`
- Benchmark card SHA-256: `46a05dcf0ba816e2d079f3e8c793228f24b3421bfd6f6380903d7b27d2e5b633`
- Freeze manifest SHA-256: `7af124f96ee1dc5667cdb1b4c1096f71ddca8a927eafad62caba1ec45a255280`
- Freeze receipt SHA-256: `932a8979adb91ea1c15b00db3af49f419adeeda8ae39e353d160d23510052b1b`

The next task is T104: freeze development data and model release.
