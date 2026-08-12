# T091 Material–corona–outcome mediation evidence

## Result

T091 was completed on the KAUST Ibex server at implementation commit `91d4735`.
The workflow preregistered four estimands over a paired development chain, estimated primary and alternative mediator decompositions, propagated uncertainty by study-cluster bootstrap, attempted an independent development replication, and applied an automatic language gate.

The result is intentionally association-only. The existing DAG audit does not establish randomized intervention, temporal order, or control of unmeasured confounding, so the workflow blocks causal mediation wording even though the independent fixture replication passed.

## Reproducible command

```bash
biointerfaceos discover mediation --fixture
```

The command was run twice with deterministic resume behavior:

```text
MEDIATION_VALID rows=12 development=8 replication=4 study_clusters=4 estimands=4 alternative_mediators=2 dag_scenarios=3 cluster_bootstrap_records=64 replication_attempted=true replication_passed=true causal_claim_permitted=false language_status=ASSOCIATION_ONLY resumed=1
```

## Estimates and gates

| Quantity | Development | Independent replication |
|---|---:|---:|
| Primary total effect | 0.6875 | 0.5250 |
| Primary direct effect | 1.1738024 | 1.1820690 |
| Primary indirect effect | -0.4863024 | -0.6570690 |
| Primary mediated fraction | -0.70734894 | -1.25155993 |

- Four estimands were frozen before calculation: total, direct, indirect, and mediated fraction.
- Two mediator alternatives were evaluated: the T090 primary functional axis, an alternative mediator, and a cyclic-shift random control.
- Three DAG scenarios were audited; all causal identification gates remained unmet.
- Development uncertainty used 32 resamples for each of two mediators, producing 64 bootstrap records with `study_id` clustering.
- The independent replication used STUDY-C and STUDY-D and was not used for tuning.
- The language result is `ASSOCIATION_ONLY`; blocked terms include `causes`, `mediates`, and `causal mediation`.

## Acceptance evidence

| Gate | Result |
|---|---|
| Paired chain inputs | T062, T073, T076, and T090 checksums verified |
| Preregistration | 4 estimands, seed 91, 32 cluster-bootstrap replicates |
| Alternative mediators/DAGs | Passed schema and sensitivity audit; 3 DAG scenarios |
| Independent replication | Attempted and passed on held-out studies |
| Causal language | Correctly downgraded; `causal_claim_permitted=false` |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 315 passed via `UV_OFFLINE=1 make check` |
| Final repository gate | Dependencies, assets, catalog, lockbox, state, compileall, diff check, and immutable release verification passed |

## Artifacts

- Schema: `agents/discovery/mediation.v1.json`
- Fixture: `tests/fixtures/omics/mediation_fixture.json`
- Workflow and CLI: `src/biointerfaceos/mediation_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/omics/mediation/`
- Focused tests: `tests/omics/test_mediation_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T092: compare human–mouse and biofluid transfer models with explicit overlap, pairing, leave-material validation, and abstention gates.
