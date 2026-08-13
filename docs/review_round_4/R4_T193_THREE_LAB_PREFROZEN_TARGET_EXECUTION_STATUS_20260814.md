# T193 三实验室预冻结靶标执行状态

## 结论

T193 已经在三个公开、可追溯来源上完成一次真正的 study-held-out、nested、cluster-aware 执行。它使用的是在 T192 新来源进入项目之前就冻结的 R3 99 个共同靶标宇宙；因此新来源没有参与靶标成员资格选择、外层测试集选择、alpha 选择或模型选择。

这一步解决了 T192 共同靶标存在的外层 target-availability leakage 问题，但证据等级仍是探索性开发观察，不能改写为独立生物学验证、lockbox、无作者复现或强 Q1 接收证据。

## 机器核验的规模

| 项目 | 结果 |
|---|---:|
| 预冻结 target universe | 99 个 R3 canonical accessions |
| 三个 source/laboratory anchors | 3 |
| 行级有效观测 | 1,495 |
| measurement batches | 85（Edinburgh 49、Dalian 6、UCD 30） |
| 外层划分 | 3 个 leave-one-laboratory-anchor-out folds |
| 模型 | constant、full sequence ridge、composition-only ridge |
| 内层选择 | development batches 上 leave-one-batch-out nested alpha |
| cluster bootstrap | 2,000 次，按 held-out measurement batch |
| 负对照 | 每个 outer fold 256 次 development-batch 内 rank permutation |

## Held-out 结果

| Held-out anchor | Full ridge mean Spearman | 95% bootstrap CI | Full − composition |
|---|---:|---:|---:|
| Dalian | 0.444 | [0.324, 0.567] | −0.089 |
| UCD | 0.331 | [0.285, 0.378] | −0.037 |
| Edinburgh | 0.205 | [0.166, 0.243] | +0.207 |

负对照上尾 p 值依次为 0.0156、0.1712、0.1751。由于只有三个 laboratory anchors，且 Dalian 是 pooled/unspecified plasma、Edinburgh 当前 map 未编码 donor ID、UCD 含技术重复，这些结果只能说明跨来源 rank portability 的探索性信号，不能等价为独立 donor-level uncertainty 或三队列验证。

## 可审计入口

- 协议：[R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_PROTOCOL.json](../data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_PROTOCOL.json)
- 注册：[R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_REGISTRY.json](../data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_REGISTRY.json)
- 行级 ledger：[source_local_prefrozen_target_ledger.csv](../../reports/review_round_4/t193_three_lab_prefrozen_target_execution/v1.0.0/source_local_prefrozen_target_ledger.csv)
- 结果报告：[t193_three_lab_execution_report.json](../../reports/review_round_4/t193_three_lab_prefrozen_target_execution/v1.0.0/t193_three_lab_execution_report.json)
- 结果 receipt：[t193_three_lab_execution_receipt.json](../../reports/review_round_4/t193_three_lab_prefrozen_target_execution/v1.0.0/t193_three_lab_execution_receipt.json)

命令入口：

```text
biointerfaceos data evaluate-r4-t193-three-lab-prefrozen-target --strict
biointerfaceos data verify-r4-t193-three-lab-prefrozen-target --strict
```

`scientific_submission_ready=false` 保持不变；非作者 lockbox、无作者原始输入复现、外部采用和 DOI 仍未获得。
