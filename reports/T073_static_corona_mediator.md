# T073 Static Corona Mediator M3 Evidence

Date: 2026-08-12  
Task: Fit static corona mediator model  
Implementation commit: `cbfafa9` (`feat-fit-static-corona-mediator-m3`)

## Scope

The M3 workflow constructs 16 unique paired material/mediator/response units from the T056/T062-aligned fixture contract, fits direct and mediator-assisted regularized decompositions on train pairs, evaluates validation OOD, runs a random-mediator negative control, and propagates mediator uncertainty.

## Acceptance results

Command:

```text
biointerfaceos train m3 --config configs/models/m3.yaml
```

Observed first and resumed runs:

```text
M3_VALID pairs=16 train=8 validation=8 identification_status=ASSOCIATIONAL_ONLY direct_rmse=0.419009 mediated_rmse=0.413194 resumed=0 target_values_exposed=false
M3_VALID pairs=16 train=8 validation=8 identification_status=ASSOCIATIONAL_ONLY direct_rmse=0.419009 mediated_rmse=0.413194 resumed=1 target_values_exposed=false
```

On validation, the mediated decomposition RMSE is `0.413194` versus direct `0.419009` (difference `-0.005815`). The random-mediator control RMSE is `0.418924`, which is `0.005730` above the mediated model. All comparisons are associational prediction comparisons only.

Pairing audit: 16 unique pairs, 0 duplicate pair IDs, 0 cross-split pairs, complete material/mediator/response fields, split-safe, identity features unused. Uncertainty propagation uses quadrature: mediator uncertainty mean `0.193750`, model residual SD `0.133463`, combined prediction SD `0.238485`.

The identification audit explicitly records `ASSOCIATIONAL_ONLY`, `causal_claim_permitted=false`, no randomized intervention, no verified temporal order, and no blocked unmeasured confounding. The workflow therefore does not promote the mediated improvement to a causal mediation claim.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/m3.yaml`
- `reports/models/m3/m3_comparison.json`
- `reports/models/m3/pairing_audit.json`
- `reports/models/m3/identification_audit.json`
- `reports/models/m3/uncertainty_propagation.json`
- `reports/models/m3/m3_coefficients.json`
- `reports/models/m3/failure_ledger.json`
- `reports/models/m3/m3_receipt.json`
- `reports/models/m3/m3_log.json`
- `reports/models/m3/m3_manifest.json`
- `tests/fixtures/models/m3_fixture.json`
- `tests/models/test_m3_workflow.py`

## Verification

- `UV_OFFLINE=1 make check`: 262 passed; ruff, format, and mypy passed.
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

T073 is complete. T074 is the next active task: fit the compositional corona model with ILR/logistic-normal controls, zero handling, simplex constraints, and toy composition recovery.
