# T100 OOD leave-group and sensitivity suite

## Result

T100 was completed on the KAUST Ibex server at implementation commit `5497ad3`.
The workflow evaluates six outcome-independent group dimensions, records primary
metrics/calibration/selective risk, flags low-n groups, runs leave-largest-study
and evidence-grade sensitivity, and narrows applicability wording when OOD support
is insufficient.

## Reproducible command

```bash
biointerfaceos robustness ood --all
```

The command was run twice with deterministic resume behavior:

```text
OOD_VALID dimensions=6 groups=12 low_n_groups=6 leave_largest=1 sensitivity_records=3 primary_records=12 calibration_records=12 selective_risk_records=12 claim_status=NARROWED_BY_OOD resumed=1
```

## Leave-group and sensitivity evidence

- Study, lab, family, species, biofluid, and time group keys all ran under the
  frozen split policy. Every key is marked `pre_outcome_group_key`, and no outcome
  field is used to construct groups.
- Twelve group records include six low-n/OOD groups. Those groups are explicitly
  flagged for abstention rather than pooled into supported applicability claims.
- The largest-study leave-out, low-n exclusion, and evidence-grade-only scenarios
  all ran. The largest study is `STUDY-A`; evidence-grade sensitivity is retained
  as a separate record.
- Because low-n/OOD groups are present, the claim gate is
  `NARROWED_BY_OOD`, preserving supported higher-support groups while downgrading
  broad applicability wording.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T099 ablation receipt verified by checksum and status |
| Group dimensions | 6/6: study, lab, family, species, biofluid, time |
| Primary/OOD metrics | 12 primary, 12 calibration, and 12 selective-risk records |
| Low-n handling | 6 groups flagged and abstained; no silent pooling |
| Sensitivity | Leave-largest-study, drop-low-n, and evidence-grade-only: 3/3 |
| Claim gate | `NARROWED_BY_OOD` |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 333 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Lockfile, schema, assets, catalog, lockbox, immutable release, state, compileall, and diff checks passed |

## Artifacts

- Schema: `agents/robustness/ood.v1.json`
- Fixture: `tests/fixtures/robustness/ood_fixture.json`
- Workflow and CLI: `src/biointerfaceos/ood_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/robustness/ood/`
- Focused tests: `tests/robustness/test_ood_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T101: assess publication selection and missingness bias.
