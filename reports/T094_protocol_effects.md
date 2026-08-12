# T094 Protocol-correction and reversal evidence

## Result

T094 was completed on the KAUST Ibex server at implementation commit `49fc799`.
The workflow froze four protocol variables, computed raw and protocol-adjusted effects, ran within-study and predefined stratum reversal tests, quantified heterogeneity, retained counterexamples, and applied an automatic language gate.

## Reproducible command

```bash
biointerfaceos discover protocol-effects --fixture
```

The command was run twice with deterministic resume behavior:

```text
PROTOCOL_EFFECTS_VALID rows=6 variables=4 studies=6 raw_effect=0.076667 adjusted_effect=-0.045000 reversal_tests=6 reversals_detected=9 counterexamples=2 heterogeneity_max=0.096667 universal_reversal_permitted=false language_status=PROTOCOL_DEPENDENT_BOUNDARY resumed=1
```

## Effect and reversal evidence

- Predefined protocol variables were `species`, `biofluid`, `assay`, and `dose_bin`; no post-hoc subgroup variables were searched.
- The aggregate raw effect was positive (0.076667), while the protocol-adjusted effect was negative (-0.045000), demonstrating an aggregate reversal.
- Nine reversal tests were detected across the aggregate, within-study, and predefined protocol strata.
- Two counterexamples retained the same raw/adjusted sign, so the reversal is not universal.
- Maximum adjusted-effect heterogeneity across predefined variables was 0.096667, and all strata/counterexamples remain in the report.
- The language gate is `PROTOCOL_DEPENDENT_BOUNDARY`; blocked wording includes `universal reversal` and `causal correction`.

## Acceptance evidence

| Gate | Result |
|---|---|
| Input provenance | T071, T089, and T091 checksums/contracts verified |
| Protocol ontology | 4 predefined variables, frozen before analysis |
| Within/comparable-study analysis | 6 study-preserving rows and 6 study clusters |
| Simpson/reversal tests | 6 test blocks, 9 reversals detected |
| Counterexamples | 2 retained; no post-hoc subgroup exclusions |
| Claim wording | Downgraded to protocol-dependent boundary effect |
| Lockbox/network | Clean; no raw download, credentials, network, or locked payload |
| Full test suite | 321 passed via `UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=/tmp/BioInterfaceOS-venv-xup0a make check` |
| Final repository gate | Dependencies, assets, catalog, lockbox, state, compileall, diff check, and immutable release verification passed |

## Artifacts

- Schema: `agents/discovery/protocol_effects.v1.json`
- Fixture: `tests/fixtures/omics/protocol_effects_fixture.json`
- Workflow and CLI: `src/biointerfaceos/protocol_effects_workflow.py`, `src/biointerfaceos/cli.py`
- Outputs: `reports/omics/protocol_effects/`
- Focused tests: `tests/omics/test_protocol_effects_workflow.py`
- Immutable release reverified: `bioif-data-20260811-42783ef-e32d9290`

The next task is T095: run counterfactual ranking and contradiction analyses, varying only supported interventions and abstaining on unstable OOD rankings.
