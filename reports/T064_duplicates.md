# T064 formulation and semantic duplicate evidence

## Result

The server now runs `biointerfaceos split detect-duplicates --fixture` with frozen `duplicate-thresholds-v1` thresholds independent of split labels. Ten items produce four conservative duplicate edges (one each by exact text, composition, structure, and text similarity), six clusters, and one ambiguous semantic-neighbor review edge.

No duplicate edge crosses split boundaries in the fixture. The duplicate detector emits edge method, score, threshold version, split labels, cluster status, review queue, and cross-split audit; it does not delete records or force ambiguous trade names together.

## Validation

```text
DUPLICATES_VALID items=10 edges=4 clusters=6 exact=1 composition=1 structure=1 text=1 review_edges=1 cross_split_duplicates=0 resumed=0 thresholds_tuned_on_split_labels=false
DUPLICATES_VALID items=10 edges=4 clusters=6 exact=1 composition=1 structure=1 text=1 review_edges=1 cross_split_duplicates=0 resumed=1 thresholds_tuned_on_split_labels=false
3 focused duplicate-detection tests passed
235 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- Exact, composition, structure, and text methods each retain independent provenance and the frozen threshold version.
- One below-threshold semantic neighbor remains in manual review; it was not promoted to a duplicate edge.
- Cross-split duplicate count is zero; no split-label tuning was used.
- No live network, raw download, credential, or locked payload access occurred.

## Artifacts

- Implementation commit: `f474d7c`.
- Fixture: `tests/fixtures/splits/duplicate_fixture.json`, SHA-256 `80e9b609e546c64fba3fcbc15ab1430200011a816105abf8ac22c0ed674acd4a`.
- Duplicate edges: `reports/splits/duplicates/duplicate_edges.json`, SHA-256 `8de9604977d4d0812cfa0e329616a624b7e577d93ae4f564f555b0855fabfa5e`.
- Duplicate clusters: `reports/splits/duplicates/duplicate_clusters.json`, SHA-256 `2d32bed62efc2820158f41f813780aed18bfe6be46edab284ce7d099b58ef164`.
- Review queue: `reports/splits/duplicates/review_queue.json`, SHA-256 `a723ecf2a6ddf14ae1e246255e9ccaa17c6abf3d05420cd35b2062df19fe4140`.
- Cross-split audit: `reports/splits/duplicates/cross_split_audit.json`, SHA-256 `9205d2ee5014358f1364b7a61504ac03a6d36c34287382dd1a61eef897eb8137`.
- Processing receipt: `reports/splits/duplicates/processing_receipt.json`, SHA-256 `9e4d2b0ecb05217315b9a5bb03d8208f83cd015da829306e4698c42f1d75ef50`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
