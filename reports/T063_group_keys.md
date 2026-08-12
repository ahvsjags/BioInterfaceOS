# T063 canonical group-key evidence

## Result

The server now runs `biointerfaceos split build-groups --fixture` against hash-verified T030, T041, T043, T047, and T057 inputs. Six records produce six study keys, three paper-family keys, four project keys, and deterministic keys for lab, material, bioenvironment, protocol, and date.

Two cross-split collisions are retained for review: one paper-family collision and one project collision. Unknown laboratory, unresolved trade-name material, missing bioenvironment, and missing date remain conservative explicit keys; no identity or outcome value was silently imputed.

## Validation

```text
GROUP_KEYS_VALID rows=6 unique_study=6 unique_paper_families=3 unique_projects=4 collisions=2 review_rows=2 resumed=0 outcome_leakage=false split_freeze=false
GROUP_KEYS_VALID rows=6 unique_study=6 unique_paper_families=3 unique_projects=4 collisions=2 review_rows=2 resumed=1 outcome_leakage=false split_freeze=false
3 focused group-key tests passed
232 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- `LAB_UNKNOWN:FAMILY_002`, `MATERIAL_UNKNOWN:NANOCOAT_X`, `BIOENV_UNKNOWN`, and `DATE_UNKNOWN` are explicit, reviewable keys.
- Same paper-family/project relationships are not split apart; cross-split conflicts are emitted as collision records and review queue entries.
- This task creates group keys only; split freezing is explicitly false and no outcome values are read or used.
- No live network, raw download, credential, or locked payload access occurred.

## Artifacts

- Implementation commit: `00968b3`.
- Fixture: `tests/fixtures/splits/group_keys_fixture.json`, SHA-256 `fff898d82640cb2c2b95e52eef3b406bbda7e98d650f6919ec7b1ad6bcbe333d`.
- Group keys: `reports/splits/group_keys/group_keys.json`, SHA-256 `794b128c7c5029eb0987fcf60e39ed7bc291e87be90d053c48a46db1043c2cba`.
- Collision audit: `reports/splits/group_keys/collision_audit.json`, SHA-256 `8c66249615f70a9369fba0ed5607405b4f7d11c96178714372cc8d9b5d119b73`.
- Review queue: `reports/splits/group_keys/review_queue.json`, SHA-256 `dce52805313355f200bbef6c6a71dcd7d72da36a6b94221531b6821e1ba33b59`.
- Processing receipt: `reports/splits/group_keys/processing_receipt.json`, SHA-256 `910e9aca5f132fa735b642ee5d32d59a6000f9995617ad92c08055eeeea536c9`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
