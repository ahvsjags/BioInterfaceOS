# T117 — 公开发布合规、文档与资产清单完成记录

状态：`DONE`（软件/文档发行边界已通过；科学投稿仍不可用）。

## 交付

- 根 `LICENSE`：Apache-2.0，来自 Apache Software Foundation 的官方许可证文本；
- `NOTICE` 与 `CITATION.cff`：明确仅 repository-authored `PUBLIC` 文件受到该公开许可证覆盖，外部来源、派生记录、历史 fixture 和退休 release 未被重新许可；
- `docs/release/PUBLIC_ASSET_REGISTRY.json`：对全部 Git-tracked assets 应用互斥、default-deny 的公开/受控/排除规则；
- `docs/release/PUBLIC_RELEASE_INVENTORY.md`、根 README 和 release README：明确 software replay 与 scientific replication / empirical validation 的边界；
- `biointerfaceos release audit-public --strict`：检查根许可/引用元数据、README 路径、唯一 glob 分类、源/许可证声明及历史 bundle 隔离，并生成带哈希 receipt。

## 正式审计

`bioif-public-release-audit-v1.1.0` 结果为 `PASS_PUBLIC_RELEASE_AUDIT`：

- 已分类 Git-tracked assets：1,648；
- `PUBLIC`：653；`CONTROLLED`：69；`EXCLUDED`：926；
- `historical_fixture_bundle_publicly_released=false`；
- `scientific_submission_ready=false`。

旧 `release/public/bioif-public-v1.0.0`、`data/`、`registry/`、`reports/` 和历史 `release/` 内容未删除或重写；它们保留审计可见性，但不进入新的公开发行。逐路径清单、报告和 receipt 位于 round-two public-release audit report directory。

## 验证

- `release audit-public --strict`：passed，receipt verify passed；
- `ruff check` / `ruff format --check`：passed；
- targeted pytest：15 passed；
- mypy（更新的 CLI 与审计模块）：passed；
- `uv build`：source distribution 与 wheel 均成功构建。

T118 将处理任何可重新分发 output 的可重建 source-data / SBOM / clean-room receipt；T120–T124 才能引入真实观测和独立科学验证。
