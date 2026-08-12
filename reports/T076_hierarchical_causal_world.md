# T076 Hierarchical Causal World M6 Evidence

Date: 2026-08-12  
Task: Fit hierarchical causal world model  
Implementation commit: `3220b11` (`feat-fit-hierarchical-causal-world-m6`)

## Scope

The M6 workflow consumes the validated T073 M3, T074 M4, and T075 M5 receipts, preregisters a DAG and estimand card, fits a bounded ridge predictive mediator model, audits positivity/overlap, evaluates confounding sensitivity and alternative DAGs, and applies an automatic language downgrade when causal identification gates fail.

## Acceptance results

Command:

```text
biointerfaceos train m6 --config configs/models/m6.yaml
```

Observed first and resumed runs:

```text
M6_VALID rows=12 train=8 validation=4 overlap_passed=true causal_claim_permitted=false validation_rmse=0.028683 resumed=0 target_values_exposed=false
M6_VALID rows=12 train=8 validation=4 overlap_passed=true causal_claim_permitted=false validation_rmse=0.028683 resumed=1 target_values_exposed=false
```

The fixture passes the declared overlap threshold (`0.1`) with propensity support from `0.25` to `0.75`. The causal gate remains closed because treatment is observational, temporal order is not established, and confounding is not blocked across the audited DAG alternatives. The primary coefficient and mediator-adjusted predictions are therefore labeled predictive/associational; causal ATE and mediated effect are explicitly `NONIDENTIFIED`. Four confounding-bias strengths (`0.0`, `0.1`, `0.25`, `0.5`) are reported, and three alternative DAG cards all remain nonidentified.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m6.yaml`
- `reports/models/m6/dag_card.json`
- `reports/models/m6/estimand_card.json`
- `reports/models/m6/overlap_audit.json`
- `reports/models/m6/confounding_sensitivity.json`
- `reports/models/m6/alternative_dags.json`
- `reports/models/m6/m6_results.json`
- `reports/models/m6/language_policy.json`
- `reports/models/m6/failure_ledger.json`
- `reports/models/m6/m6_receipt.json`
- `reports/models/m6/m6_log.json`
- `reports/models/m6/m6_manifest.json`
- `tests/fixtures/models/m6_fixture.json`
- `tests/models/test_m6_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 271 passed; ruff, format, and mypy passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or public target-value exposure was used.

## Handoff

T076 is complete. T077 is the next active task: compare cross-domain invariant learning methods under identical tuning budgets, with strict environment-label leakage controls and an OOD-improvement requirement.
