# T110 Audit sealed lockbox results and update claim statuses

## Result

T110 was completed on the KAUST Ibex server at implementation commit `9b573bf`.
The strict audit verified the signed T108 release, the T109 first-run receipt,
and the frozen Paper C prediction and claim packages. It mapped all five
predictions to explicit post-lock statuses and preserved the language and
applicability gates for C6-C8.

## Reproducible command

```bash
make lockbox-audit
```

Observed first run:

```text
LOCKBOX_AUDIT_VALID audit_id=bioif-lockbox-audit-v1.0.0 predictions=5 replicated=2 refuted=1 inconclusive=2 abstentions=2 claims=8 threshold_changes=0 prediction_rewrites=0 raw_values_written=false
```

A second invocation was rejected before overwrite:

```text
LOCKBOX_AUDIT_INVALID: post-lock audit already executed; overwrite refused
```

## Claim transition summary

| Claim | Prediction | Pre-lock status | Post-lock status | Disposition |
|---|---|---|---|---|
| C1 | P1 | DEVELOPMENT_SUPPORTED | REPLICATED | retain as replicated metadata-only result |
| C2 | P2 | DEVELOPMENT_SUPPORTED | REPLICATED | retain as replicated metadata-only result |
| C3 | P3 | BOUNDED_BY_COUNTEREXAMPLES | INCONCLUSIVE | preserve protocol-boundary abstention |
| C4 | P4 | BOUNDED_BY_ABSTENTION | REFUTED | retain overlap-failure refutation |
| C5 | P5 | EXPLORATORY_ONLY | INCONCLUSIVE | preserve model-disagreement abstention |
| C6 | — | LANGUAGE_GATE | LANGUAGE_GATE_PRESERVED | association-only wording retained |
| C7 | — | LANGUAGE_GATE | APPLICABILITY_LIMIT_PRESERVED | OOD/selection limits retained |
| C8 | — | PRELOCK_ONLY | EVALUATOR_AUTHORIZED_METADATA_ONLY | no protected values released |

No threshold changed, no prediction was rewritten, and no inconvenient case was
removed. Abstentions and failure classes remain explicit in the sealed audit
outputs.

## Acceptance evidence

| Gate | Result |
|---|---|
| Full test suite | 370 passed |
| Static checks | ruff, format check, mypy, compileall, and `git diff --check` passed |
| Environment | `uv lock --check` and frozen `uv sync` passed |
| Repository checks | schema, assets, catalog, lockbox, release, state, and audit verify passed |
| Prediction mapping | 5/5 mapped: 2 replicated, 1 refuted, 2 inconclusive |
| Claim coverage | 8/8 claims transitioned or preserved |
| Immutability | threshold changes 0; prediction rewrites 0; second run rejected |
| Boundary | raw values written false; protected values read false; contamination scan clean |

## Artifacts

- Schema: `agents/lockbox/audit_results.v1.json` (SHA-256 `601c60ddbac4373625ec5f9b4eb708058bb451183aaf64151d71be6ed73d2c11`)
- Fixture: `tests/fixtures/lockbox/audit_fixture.json` (SHA-256 `f9c6ddaa1d94a9e06f036c261486590bf84ffa33e7b408de547c1d917a3f4721`)
- Workflow: `src/biointerfaceos/lockbox_audit_workflow.py` (SHA-256 `07fd7da66955fb102f7be5077b47a1168d78ca685df88f9b18fbaf3e898be639`)
- Tests: `tests/lockbox/test_audit_workflow.py` (SHA-256 `7d17a0eb65143ce091b354d0d0cae2a6ff0bf48fcb7a7b09c022c882d3997e25`)
- Claim transitions: `reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/claim_transitions.json` (SHA-256 `35aee608552de3904b2c040f00bae854a952c528821ac2b80c9b0c3081372a09`)
- Failure analysis: `reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/failure_analysis.json` (SHA-256 `05f90250461bfe467cc359af539b850d727eeb5d6ae81f9c0d1ca9fc08e2fcb7`)
- Audit report: `reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/audit_report.json` (SHA-256 `f1a733a094ce9e21376bb7912251d943760c0f513b843d359976bca969bb3826`)
- Audit receipt: `reports/lockbox/audit/bioif-lockbox-audit-v1.0.0/audit_receipt.json` (SHA-256 `9b72d57cc29f404d4cd63c249292d7c3251e388fd2fbef3659732fa4cf98ff3b`)
- Implementation commit: `9b573bf`

## Limitations

- The evaluator and audit outputs are metadata-only; protected raw values were
  not read or copied into development artifacts.
- `INCONCLUSIVE` and `REFUTED` are retained as outcomes, not converted into
  positive evidence by threshold or wording changes.
- Future figures and manuscript claims must consume these sealed statuses and
  preserve the C6-C8 language/applicability gates.

The next task is T111: generate final publication figures and tables from the
frozen specifications and sealed metadata.
