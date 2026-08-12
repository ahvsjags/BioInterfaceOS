# T107 Draft Paper C scientific-law manuscript pre-lock

## Result

T107 was completed on the KAUST Ibex server at implementation commit `dec93c5`.
The pre-lock package freezes five development candidates, five exact analyses,
five predictions, allowed wording, abstention boundaries, and figure
specifications before any protected evaluation.

## Reproducible command

```bash
make paper-c-prelock
```

Observed first and resumed runs:

```text
PAPER_C_PRELOCK_VALID candidates=5 strong_candidates=2 analyses=5 predictions=5 claims=8 tables=6 figures=5 evidence_inputs=8 style_passed=true lockbox_accessed=false resumed=0 target_values_exposed=false
PAPER_C_PRELOCK_VALID candidates=5 strong_candidates=2 analyses=5 predictions=5 claims=8 tables=6 figures=5 evidence_inputs=8 style_passed=true lockbox_accessed=false resumed=1 target_values_exposed=false
```

## Candidate boundary

The package uses eight checksum-pinned development reports: T090 functional
axes, T091 mediation, T092 transfer, T093 symbolic laws, T094 protocol effects,
T095 counterfactuals, T100 OOD sensitivity, and T101 selection sensitivity.

The two strongest development candidates are the log-ratio functional-axis
association and the unit-aware symbolic candidate. Protocol effects and
transfer remain bounded candidates. Counterfactual ranking remains exploratory.

T091 remains association-only because causal identification gates fail. T100
narrows applicability because six low-n groups are present. T101 downgrades
claims because selection models disagree by 0.300000. These gates propagate to
every candidate and prediction.

## Frozen prediction package

| Component | Result |
|---|---|
| Candidates | 5 total; 2 with high development support |
| Analyses | 5 exact analyses with primary metrics and abstention rules |
| Predictions | 5 marked `PREDICTED_BEFORE_LOCKBOX` |
| Wording | Allowed and blocked language frozen per candidate |
| Figures | 5 deterministic specifications; no protected outcomes plotted |
| Lockbox | Not accessed; no protected payload included |

## Acceptance evidence

| Gate | Result |
|---|---|
| Full test suite | 352 passed |
| Lock and environment | `uv lock --check` and frozen `uv sync` passed |
| Static checks | ruff check, ruff format check, mypy, compileall, and `git diff --check` passed |
| Repository checks | Schema, assets, catalog, lockbox, immutable release, and project state passed |
| Pre-lock checks | 8 evidence inputs, 5 candidates, 5 analyses, 5 predictions, 8 claims, style audit PASS |
| Immutability | Byte-stable resume, fixture checksum mutation rejection, and artifact tamper rejection passed |
| Protected boundary | `lockbox_accessed=false`, `target_values_exposed=false` |

## Artifacts

- Schema: `agents/manuscripts/paper_c_prelock.v1.json` (SHA-256 `63c4db07e3f27fa9a736391970f1818b900b1c989c420113fc4a5f18169c6f74`)
- Fixture: `tests/fixtures/manuscripts/paper_c_prelock_fixture.json` (SHA-256 `57d8835b20e30529850df31a9e5cb7809d33c9a1ef4a9765e3099c0c986bdbdf`)
- Workflow: `src/biointerfaceos/paper_c_prelock_workflow.py` (SHA-256 `60599d8dcc628168bafbf4f7d00a9c1f7aa0830e6b8ed311df9378b13bea61d3`)
- Tests: `tests/manuscripts/test_paper_c_prelock_workflow.py` (SHA-256 `7529a8a8b78717d49b223882748cb78fd5b68ed345b0bca9044e99852ec026d2`)
- Manuscript package: `release/manuscripts/paper_c_prelock/`
- Receipt SHA-256: `b1efe3e1a3424817ed94e242408a587f6a38b8a78f8a21c964b87ef3861a3f1f`
- Manifest SHA-256: `f810392e1c0e68b6f74cdc6559e8d7f7c44984600764dd81f9e62a94faac1a8d`
- Candidate cards SHA-256: `bbfe4e59780f6c1513d02a3066b25671fcbaac33413331da9ce3380419fe20a9`
- Prediction table SHA-256: `d672d3ed54d3c7a306828d8a67808a3133be1433891f8f61b426f0a83fd21483`
- Analysis specs SHA-256: `d2672dd4ca2e07ab75e7775762a2d46b116b295ec8ef40ea33fb743d2bcfa933`
- Allowed wording SHA-256: `a2f434733c90d9b52f136b487d55ad38d9776b9c5144c48e1eccc047914d95b7`
- Table manifest SHA-256: `e9bbda029bbca5d47c0f75451d01385d831d48947f34de09550dcdeacbb51468`
- Figure manifest SHA-256: `c9a43bba947e4e170f86766fe2ba9476e0823e252c528af08d7eb72e181dbcab`
- Style audit SHA-256: `6cc47a3e25e33e6dbbc14f51dfc1f09ba89651ea51b715f7e0328ed9ddd40d93`

## Limitations

- The candidates are fixture-backed development discoveries.
- The mediation chain is association-only.
- OOD and selection sensitivity narrow applicability.
- Protected evaluation outcomes remain unknown and unreported.
- Final venue citations and typesetting remain submission-stage work.

The next task is T108: create the signed internal frozen release before lockbox.
