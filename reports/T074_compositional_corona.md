# T074 Compositional Corona M4 Evidence

Date: 2026-08-12  
Task: Fit compositional corona model  
Implementation commit: `c99691b` (`feat-fit-compositional-corona-m4`)

## Scope

The M4 workflow validates three-part simplex compositions, preserves raw zero masks, compares raw-zero flooring with a pseudocount alternative in ILR space, evaluates full train/validation splits, and recovers a toy composition through inverse ILR.

## Acceptance results

Command:

```text
biointerfaceos train m4 --config configs/models/m4.yaml
```

Observed first and resumed runs:

```text
M4_VALID rows=16 train=8 validation=8 alternatives=2 best_rmse=0.317028 toy_recovery=true resumed=0 target_values_exposed=false
M4_VALID rows=16 train=8 validation=8 alternatives=2 best_rmse=0.317028 toy_recovery=true resumed=1 target_values_exposed=false
```

The pseudocount alternative is best with validation RMSE `0.317028` and bootstrap interval `[0.181165, 0.453202]`; raw-zero flooring is retained with RMSE `0.905354` and interval `[0.280181, 1.501396]`. T073 M3 direct RMSE is `0.419009`, so `m4_not_worse_than_m3=true` for the selected pseudocount alternative. Both alternatives preserve full-split primary evaluation and record train/validation zero-row counts.

The composition audit records two raw-zero rows, raw-zero fraction `0.125`, zero-mask preservation, three simplex parts, two ILR balances, and zero simplex sum error. Toy inverse-ILR recovery passes with the configured tolerance. Target values are not emitted in public artifacts.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m4.yaml`
- `reports/models/m4/m4_results.json`
- `reports/models/m4/m4_comparison.json`
- `reports/models/m4/simplex_audit.json`
- `reports/models/m4/zero_audit.json`
- `reports/models/m4/toy_recovery.json`
- `reports/models/m4/failure_ledger.json`
- `reports/models/m4/m4_receipt.json`
- `reports/models/m4/m4_log.json`
- `reports/models/m4/m4_manifest.json`
- `tests/fixtures/models/m4_fixture.json`
- `tests/models/test_m4_workflow.py`

## Verification

- `UV_OFFLINE=1 make check`: 265 passed; ruff, format, and mypy passed.
- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or public target-value exposure was used.

## Handoff

T074 is complete. T075 is the next active task: implement a dynamic corona world model with explicit data sufficiency gating, constrained trajectories, toy recovery, and a simpler kinetic fallback when needed.
