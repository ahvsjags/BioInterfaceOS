# Retired historical public bundles

`release/public/bioif-public-v1.0.0` 是第二轮审查前生成的历史 fixture bundle。它只为可追溯性保留，不能作为当前公开数据发行、投稿材料或科学证据。

当前可重放范围是 **software replay only**；它是 **not scientific replication**，也是 **not empirical validation**。该目录中未明示为 `PUBLIC` 的任何资产均不可重新分发。完整资产决定见 [`docs/release/PUBLIC_ASSET_REGISTRY.json`](../../docs/release/PUBLIC_ASSET_REGISTRY.json)，并由：

```bash
python -m biointerfaceos release audit-public --strict
```

进行严格检查。
