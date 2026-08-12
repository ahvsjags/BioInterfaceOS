# T066 split leakage and lockbox audit evidence

## Result

The server now runs `biointerfaceos split audit --strict --fixture` against hash-verified T065 split/blacklist/leakage artifacts and T015 lockbox policy. Ten adversarial cases were exercised: nine identity/study/hash/duplicate attacks were detected and one forbidden lockbox read was blocked. The contamination scan of frozen split artifacts is clean and the approval receipt reports zero critical findings.

## Validation

```text
SPLIT_AUDIT_VALID attacks=10 detected=9 blocked=1 critical_findings=0 clean_scan=True resumed=0
SPLIT_AUDIT_VALID attacks=10 detected=9 blocked=1 critical_findings=0 clean_scan=True resumed=1
3 focused split-audit tests passed
241 full tests passed
```

The final offline gate also passed UV lock/sync, Ruff, formatting, mypy, assets, catalog, lockbox self-test, immutable release verification, state validation, compileall, and `git diff --check`.

## Guard results

- Paper/accession/author/journal/layout/path feature attacks are detected by the frozen blacklist contract.
- Study-only, ID-hash, and duplicate attacks are explicitly recorded as detected adversarial cases.
- Development read of `data/locked_test/payload.bin` is blocked by the lockbox firewall; no locked payload was opened.
- Frozen split artifacts contain no forbidden contamination fields/hashes; strict approval is issued with `critical_findings=0`.

## Artifacts

- Implementation commit: `f94b94a`.
- Fixture: `tests/fixtures/splits/audit_fixture.json`, SHA-256 `00473348900cd8a2409b08cb49a7707efa2049533f0a97fedfc1543377258e7e`.
- Attack findings: `reports/splits/audit/attack_findings.json`, SHA-256 `6f44789dcc78ecf153e1a29a69106481b7a74ee2e75ce73ca5ba9dca00085305`.
- Contamination scan: `reports/splits/audit/contamination_scan.json`, SHA-256 `5e621e280928070eafddce3422a5725272a97a03e7509517c420cf220510520e`.
- Approval receipt: `reports/splits/audit/approval_receipt.json`, SHA-256 `071baf8c1defec31956f254603ad5b297f054df011e5011e63d3a7d2e2767a07`.
- Audit receipt: `reports/splits/audit/audit_receipt.json`, SHA-256 `fdabf7b731618413aaebbd9effb23d54b266616461fec395023560e7ed6174ff`.

The first run created deterministic outputs and the second returned `resumed=1` without changing receipt bytes.
