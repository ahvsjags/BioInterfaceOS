# Release boundary

`release/` 同时保存历史 fixture/开发记录和未来可发布构件；它不是一个默认可重新分发的目录。每个已跟踪文件的权利、来源、证据边界和发行决定均由 [`docs/release/PUBLIC_ASSET_REGISTRY.json`](../docs/release/PUBLIC_ASSET_REGISTRY.json) 定义。

当前公开范围只包含以 `PUBLIC` 标记的软件与文档。所有 `data/`、`registry/`、历史 `reports/`、历史 `release/` bundle、文稿和图件都保留在仓库中以便审计，但为 `EXCLUDED` 或 `CONTROLLED`，不得被当作新的公开数据发行或科学证据。

执行严格审计：

```bash
python -m biointerfaceos release audit-public --strict
```

该命令只确认资产发行边界；不会把 deterministic software replay 变成 scientific replication 或 empirical validation。
