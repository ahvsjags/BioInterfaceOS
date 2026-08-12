# T079 Multimodal Material and Document Representations Evidence

Date: 2026-08-12  
Task: Add multimodal material and document representations  
Implementation commit: `29a0292` (`feat-add-multimodal-representation-fallback`)

## Scope

The multimodal workflow compares material, protocol, structure, figure, text, material/protocol-masked, and fusion representations. Every modality carries an explicit missingness mask; source identity and outcome-derived text are excluded from features; fusion is accepted only when its OOD gain persists.

## Acceptance results

Command:

```text
biointerfaceos train multimodal --config configs/models/multimodal.yaml
```

Observed first and resumed runs:

```text
MULTIMODAL_VALID rows=12 train=8 validation=4 modalities=5 selected_model=material_protocol_masked fusion_ood_gain=-0.093993 selected_ood_rmse=0.073142 leakage_passed=true missingness_masked=true resumed=0 target_values_exposed=false
MULTIMODAL_VALID rows=12 train=8 validation=4 modalities=5 selected_model=material_protocol_masked fusion_ood_gain=-0.093993 selected_ood_rmse=0.073142 leakage_passed=true missingness_masked=true resumed=1 target_values_exposed=false
```

Five modalities are audited. The source identity field is not included in any model feature list, and text provenance is restricted to material/protocol-only content with `outcome_derived=false`. Missing structure/figure values in OOD rows are represented by explicit masks. Fusion OOD RMSE is `0.177412`, worse than the best single-modality OOD RMSE `0.083419`; the fusion gain is `-0.093993`, so the declared material/protocol masked fallback is selected.

## Determinism and artifacts

The second fit returned `resumed=1` after byte-for-byte comparison. Outputs:

- `configs/models/multimodal.yaml`
- `reports/models/multimodal/missingness_audit.json`
- `reports/models/multimodal/leakage_audit.json`
- `reports/models/multimodal/model_comparison.json`
- `reports/models/multimodal/ood_evaluation.json`
- `reports/models/multimodal/multimodal_results.json`
- `reports/models/multimodal/failure_ledger.json`
- `reports/models/multimodal/multimodal_receipt.json`
- `reports/models/multimodal/multimodal_log.json`
- `reports/models/multimodal/multimodal_manifest.json`
- `tests/fixtures/models/multimodal_fixture.json`
- `tests/models/test_multimodal_workflow.py`

## Verification

- `UV_OFFLINE=1 uv lock --check`: passed.
- `UV_OFFLINE=1 uv sync --frozen --python 3.11`: passed.
- `UV_OFFLINE=1 make check`: 280 passed; ruff, format, and mypy passed.
- `biointerfaceos assets verify`: passed.
- `biointerfaceos catalog check`: passed.
- `biointerfaceos lockbox self-test`: passed with forbidden read blocked.
- `biointerfaceos release verify --fixture --release-id bioif-data-20260811-42783ef-e32d9290`: passed.
- `biointerfaceos state validate`: passed.
- `python -m compileall -q src tests`: passed.
- `git diff --check`: passed.
- No network access, raw download, locked payload access, or public target-value exposure was used.

## Handoff

T079 is complete. T080 is the next active task: implement a typed multi-agent runtime with schema validation, tool allowlists, budgets, deterministic replay, retries, and append-only traces using mock/rule backends only.
