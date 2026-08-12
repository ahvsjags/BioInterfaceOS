# T065 frozen development split evidence

## Result

The server now runs `biointerfaceos split freeze-dev --fixture` using hash-verified T063 group keys, T064 duplicate audit, T015 lockbox policy, and T047 Silver manifest. The frozen development manifest contains 2 train rows and 1 validation row; 2 candidates are excluded for being after the validation window or lacking a date.

Group containment and duplicate-cluster containment pass. Ten identity-like fields are frozen in a feature blacklist, outcome values are not used, and the manifest records split and blacklist hashes for downstream reproducibility.

## Validation

```text
SPLIT_FREEZE_VALID candidates=5 train=2 validation=1 excluded=2 groups=2 blacklisted_features=10 resumed=0 outcome_leakage=false lockbox_accessed=false
SPLIT_FREEZE_VALID candidates=5 train=2 validation=1 excluded=2 groups=2 blacklisted_features=10 resumed=1 outcome_leakage=false lockbox_accessed=false
3 focused split-freeze tests passed
238 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- Train rows satisfy date ≤ 2023-12-31; validation rows are within 2024.
- Paper family, project, material, bioenvironment, and duplicate-cluster keys remain contained within each split.
- `paper_id`, `accession`, `author`, `journal`, `layout_position`, `file_path`, `source_url`, `split_label`, `record_id`, and `project_accession` are blacklisted.
- Two exclusions retain exact reasons and evidence locators; no silent deletion occurred.
- No outcome value, locked payload, credential, raw download, or live network was accessed.

## Artifacts

- Implementation commit: `ab5368f`.
- Fixture: `tests/fixtures/splits/split_fixture.json`, SHA-256 `fa7f6b605654407065ba9453cc3273830c6d1695a860d65a81a2fdb486a3e6f9`.
- Split manifest: `reports/splits/frozen_dev/split_manifest.json`, SHA-256 `c1b32d9b2b23cca7ec9ba7bf7cc0471514fdf2a0fb07a3204461b5b8cfa150c2`.
- Feature blacklist: `reports/splits/frozen_dev/feature_blacklist.json`, SHA-256 `ed8ded66663ceac9aeed4a88648ee60177ff98f09b718762b3ff8fb171ceb0af`.
- Exclusion ledger: `reports/splits/frozen_dev/exclusion_ledger.json`, SHA-256 `6b305fdf7e04b531688b5f489e85c0ff27bd2c14a5b93ef2b60aac830bb7d681`.
- Leakage audit: `reports/splits/frozen_dev/leakage_audit.json`, SHA-256 `3d426a4516c882430d919d39853150f9849bb0a5dc2ca3e1c60f19c630423d09`.
- Freeze receipt: `reports/splits/frozen_dev/freeze_receipt.json`, SHA-256 `9cf28f50297606cdff0e0d4378f62fc510e30c3ca54dbbbc6e65be7b244f426a`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
