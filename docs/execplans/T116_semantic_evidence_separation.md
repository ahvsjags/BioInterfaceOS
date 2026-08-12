# T116 — 证据语义隔离与历史兼容迁移

## 目的

消除 fixture、deterministic software replay、development real-data analysis、independent locked evaluation 与 external scientific reproduction 之间的术语泄漏。此任务修复表达、schema 和 guardrails；它不会把任何旧 fixture outcome 升级为实证证据。

## 输入与边界

- 输入：T105–T114 的 claim ledger、lockbox workflow、manuscripts、tests/fixtures、release manifests 和 T115 的 gate registry；
- 不读取、生成或修改任何 protected raw observations；
- 不修改历史 receipt 的 bytes/hash。需要更正时创建新的 migration record 和兼容映射。

## 设计

建立不可互换的 evidence class：

| Code | 定义 | 可用措辞 | 不可用措辞 |
|---|---|---|---|
| `FIXTURE_TEST` | 预置 CI/contract fixture | fixture demonstration, contract-test status | empirical, study, replicated, refuted, law |
| `SOFTWARE_REPLAY` | 同输入、同环境的确定性重放 | software replay, deterministic rebuild | independent scientific replication |
| `DEVELOPMENT_OBSERVATION` | 非-fixture 真实 development observation | exploratory, development association | externally validated, replicated |
| `LOCKED_EVALUATION` | 冻结代码上的受保护真实评价 | evaluator-backed status | universal law，除非统计/适用域另行通过 |
| `EXTERNAL_REPRODUCTION` | 无作者团队的经验性重建 | externally reproduced within scope | universal/general causal claim |

## 实施步骤

1. 对 claim、lockbox、release、manuscript 和 figure metadata 增加 `evidence_class` 与 `allowed_claim_level`；默认拒绝未知或缺失值；
2. 迁移 fixture lockbox outcome 到版本化 `CONTRACT_*` status，保留旧字段/历史 receipt 仅用于回溯，不允许新的稿件或报告消费旧 scientific labels；
3. 更新 manuscript/figure 生成层：若输入为 `FIXTURE_TEST` 或 `SOFTWARE_REPLAY`，自动拒绝 empirical/replication/law/study/OOD 外部验证词汇；
4. 新增单元和集成测试：预置 P1–P5 status、fixture-only target、fixture study ID、software replay 等均须触发拒绝或降级；
5. 在 release 和 claim audit 中展示每项 evidence class、来源、适用范围和禁止推断；
6. 对完整测试集、目标 claim/lockbox/audit 子集和文件 hash 运行回归；把 migration 和失败案例写入报告。

## 验收

- 任何 fixture 驱动 output 无法输出 `REPLICATED`、`REFUTED`、`independent study`、`external OOD validation` 或 `law discovery`；
- historical artifacts 没有被改写，新增 migration ledger 能将旧标签解释为历史 fixture contract；
- claim audit 失败封闭：若 evidence class 缺失、源为 fixture 或词汇不匹配，命令必须非零退出；
- README/文稿/图注中 software replay 与 scientific reproduction 使用明确的不同术语；
- 测试覆盖正反例并通过；没有用删除不利结果来达到零违规。

## 失败处理

若迁移会改变历史 receipt 或某输出无法安全分类，保留原 artifact 并将其隔离出新的 release；对应主张降级为未验证，不得以自由文本例外绕过 schema。
