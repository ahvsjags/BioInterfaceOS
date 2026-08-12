# T102 Negative controls and deliberate leakage attacks

## Result

T102 was completed on the KAUST Ibex server at implementation commit `356b849`.
The workflow executes preregistered negative controls and deliberate leakage
attacks against frozen split, model-budget, and provenance inputs. Expected
performance failures are treated as firewall passes; detected metadata and
duplicate leakage is retained as an explicit audit result.

## Reproducible command

```bash
biointerfaceos robustness negative-controls --strict
```

The command was run after implementation and again during the post-commit
release gate:

```text
NEGATIVE_CONTROLS_VALID attacks=9 expected_failures=5 detected=6 critical_leaks=0 duplicate_hits=2 strict_pass=1 claim_status=ATTACKS_CLEAN resumed=1
```

## Attack evidence

- Nine attacks ran under the frozen `frozen_group_split_v1` split and budget `8`.
- Five preregistered low-performance negative controls failed as expected.
- Six attacks were detected by performance, proxy, missingness, or duplicate
  checks; the two duplicate hits remain in the duplicate audit.
- Critical leakage count is `0`, so strict mode retains the clean-release gate
  and emits `ATTACKS_CLEAN`.
- Study, journal, year, layout, unit, missingness, random-mediator, label-shuffle,
  and duplicate attack traces are preserved separately; no public target values
  or locked payloads were accessed.

## Acceptance evidence

| Gate | Result |
|---|---|
| Attack coverage | 9/9 preregistered attacks executed |
| Expected negative controls | 5 expected performance failures |
| Leakage detection | 6 detections; critical leaks 0 |
| Duplicate audit | 2 duplicate hits recorded |
| Strict claim gate | `ATTACKS_CLEAN` |
| Full test suite | 337 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Quality | Ruff, format check, and mypy passed |
| Repository gates | Lockfile, sync, schema, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |

## Artifacts

- Schema: `agents/robustness/negative_controls.v1.json`
- Fixture: `tests/fixtures/robustness/negative_controls_fixture.json`
- Workflow and CLI: `src/biointerfaceos/negative_controls_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/robustness/negative_controls/`
- Focused tests: `tests/robustness/test_negative_controls_workflow.py`
- Receipt SHA-256: `75f61af52ea96576e416395d66fd8ad75b565b148ee36b0025ec2082055b13cc`
- Manifest SHA-256: `42f5058ea24ffb366214a69c091b09ba05b96ede3a3ed0c06f48c27f8b45aa6a`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T103: freeze the BioInterfaceBench development release.
