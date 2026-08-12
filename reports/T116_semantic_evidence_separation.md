# T116 — 证据语义隔离完成记录

状态：`DONE`（历史发布物仍被隔离，不是 submission-ready）。

## 交付

- 新增不可互换的 evidence classes：`FIXTURE_TEST`、`SOFTWARE_REPLAY`、`DEVELOPMENT_OBSERVATION`、`LOCKED_EVALUATION` 和 `EXTERNAL_REPRODUCTION`；
- fixture lockbox 的新输出只允许 `CONTRACT_EXPECTATION_*` 状态，禁止 `REPLICATED`、`REFUTED`、独立研究、经验性验证和 law-discovery 表述；
- 文稿、lockbox、claim audit 和 figure/table metadata 均要求 `evidence_class` 与 `allowed_claim_level`；缺失、fixture 或不匹配的科学断言会 fail closed；
- 旧 release/receipt 没有改写。兼容映射和每个历史来源的分类见 `reports/review_round_2/evidence_semantics/v1.1.0/evidence_migration_ledger.json`。

## 审计结果

`python -m biointerfaceos claim audit-semantics --strict` 有意以退出码 1 返回：

- 状态：`BLOCKED_EVIDENCE_SEMANTICS`；
- finding：历史 `release/manuscripts/paper_a/paper_a.md` 含 fixture 语境下的 `independent studies`；
- `historical_sources_mutated=false`。

这不是 T116 的失败：该 finding 证明历史 artifact 被保留并被新发布链隔离。它不得用于新的 manuscript claim、lockbox audit 或 submission acceptance。消除此历史发布物的 public-facing 影响由 T117/T118 处理。

## 验证

- `pytest -q`：395 passed；
- `ruff check`：passed；
- `ruff format --check`：passed；
- `python -m py_compile ...`：passed；
- `python scripts/validate_execution_pack.py`：0 errors（1 个既有 warning）。
