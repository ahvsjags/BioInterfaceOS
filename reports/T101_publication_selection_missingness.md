# T101 Publication selection and missingness bias

## Result

T101 was completed on the KAUST Ibex server at implementation commit `177caf7`.
The workflow compares complete-case, inverse-probability-weighted, pattern-mixture,
and bounded-selection models on the same four study clusters. It preserves missing
mechanisms and ambiguous fields, reports deterministic intervals and model
disagreement, and keeps p-values as metadata only.

## Reproducible command

```bash
biointerfaceos robustness bias --fixture
```

The command was run twice with deterministic resume behavior:

```text
BIAS_VALID rows=8 clusters=4 models=4 observed_rows=5 missing_rows=3 missing_mechanisms=3 interval_records=4 model_disagreement=0.300000 p_values_used=0 claim_status=DOWNGRADED_SELECTION_SENSITIVE resumed=1
```

## Selection and missingness evidence

- Four plausible models ran on eight studies across four preserved study clusters:
  complete-case, IPW, pattern-mixture, and bounded selection.
- Three missing rows are explicitly assigned to MCAR, MAR, and MNAR mechanisms;
  missing fields and publication probabilities remain in the missingness audit.
- The conservative bounded-selection envelope produces material model disagreement
  of `0.300000`, so the claim gate is
  `DOWNGRADED_SELECTION_SENSITIVE`.
- Four deterministic interval records are emitted. Reported p-values are counted
  as metadata but `p_values_used=0`; no significance scraping influences any model
  or claim.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T047, T071, T091, T093, and T100 inputs verified by checksum |
| Model coverage | 4/4 preregistered selection/missingness models |
| Clustering | 8 rows across 4 study clusters preserved in every comparison |
| Missingness | 3 missing rows; MCAR, MAR, MNAR mechanisms retained |
| Intervals | 4 deterministic bootstrap interval records |
| P-value policy | Metadata only; p-values not used as ground truth |
| Claim gate | `DOWNGRADED_SELECTION_SENSITIVE` under material disagreement 0.300000 |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 335 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Lockfile, schema, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |

## Artifacts

- Schema: `agents/robustness/bias.v1.json`
- Fixture: `tests/fixtures/robustness/bias_fixture.json`
- Workflow and CLI: `src/biointerfaceos/bias_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/robustness/bias/`
- Focused tests: `tests/robustness/test_bias_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T102: run negative controls and deliberate leakage attacks.
