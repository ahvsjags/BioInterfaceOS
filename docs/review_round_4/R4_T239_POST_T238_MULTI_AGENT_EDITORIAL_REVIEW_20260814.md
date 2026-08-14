# R4-T239：T238 后五角色多智能体编辑复核

日期：2026-08-14。评审对象为当前工作树、T238 正式 protocol/registry/report/receipt、T253 历史复核以及当前外部 handoff 状态。五个角色均为只读复核：统计学主审、计算蛋白组学/生物学编辑、可复现性审稿人、期刊主编、反证与魔鬼代言人。

## 共识决定

**Major Revision；`scientific_submission_ready=false`。**

五个角色的八项分数完全收敛到同一组保守评分。T238 是实质性的作者侧统计修正，但没有产生第三方 evidence receipt；因此内部分析提升不能抵消四个外部硬门。

## 模块评分

| 模块 | 共识分数 | T238 后判断 |
|---|---:|---|
| 数据兼容性与样本基础 | 82 | 四源 row-traceable paper-data map；pooled/technical/donor-unresolved 边界仍在 |
| 统计分析设计 | 88 | fold-local target membership、nested selection、cluster uncertainty 已闭合；仍为 source-conditional estimand |
| 统计执行与有效样本 | 77 | receipt 可重执行；3,844 是 fold ledger rows，held-out test-only 为 783，不是 donor-level n |
| 模型、消融、negative control 与 OOD | 75 | 四折模型真实执行；sequence 增量只有 Edinburgh 折明显为正，其他三折为 0 |
| 独立评估 / protected lockbox | 12 | 0/1 verified non-author evaluator receipt |
| 外部科学复现 | 8 | 0/1 no-author accession-to-result receipt |
| 外部用户采用 | 46 | 0/2 distinct non-author adoption receipts |
| DOI 不可变归档 | 25 | 0/1 authenticated archive-service read-back |

- 内部科学核心均值：`(82+88+77+75)/4 = 80.5`
- 外部证据均值：`(12+8+46+25)/4 = 22.75 ≈ 22.8`
- 八项简单均值：`51.625 ≈ 51.6`

外部四项是硬门，不能用内部均值抵消。

## T238 真正改变的内容

1. 每个 outer fold 的 target set 只由三个 development sources 的可用 accession 交集确定，held-out source 不参与 target membership、alpha selection 或 model selection。
2. 四个 held-out source folds 的 development-only target 数为 `9/9/10/10`，每折 held-out available target 为 `7`。
3. receipt 明确区分 `fold_ledger_row_count=3844`、`development_observation_count=3061` 与不重复的 `held_out_test_observation_count=783`。
4. 每次 permutation 都重新选择 alpha；64 次 null 被明确限定为有限 Monte Carlo QC，不是确认性 p-value；paired ablation 与 batch bootstrap 使用 2,000 次重采样。
5. T238 结果支持 source-conditional exploratory rank portability，不支持普遍 sequence-feature superiority：full-minus-composition 只有 Edinburgh fold 为 `+0.1201`（95% CI `0.1006–0.1439`），其余三折为 `0`。

## T238 没有改变的内容

- 仍是 `DEVELOPMENT_OBSERVATION / EXPLORATORY`，不是 independent validation。
- 4 个 laboratory/source anchors 不是 4 个独立 donor cohorts；measurement batches、technical replicates 和 pooled/unspecified plasma 不能换算成 donor-level effective n。
- 主要是 paper-attached processed data，未完成无作者 raw-MS independent reanalysis。
- 没有非作者 lockbox、no-author reproduction、两个真实外部 adoption receipts 或 authenticated DOI read-back。
- 作者/Codex run、GitHub Issue、模板包、公开 Release、CI 和 KAUST replay 均不计为第三方科学证据。

## 三个最高优先级拒稿点

1. 四项外部证据硬门仍全部关闭。
2. 有效生物学样本基础不能支撑 donor-level biological generalization。
3. sequence-feature 增量跨来源不稳定；正文若写 universal sequence superiority、independent biological validation 或 external reproduction，将构成过度主张。

## 投稿定位

当前最稳妥的稿件定位是：

> author-run, paper-derived, source-conditional protein-target rank-portability/resource analysis with exploratory laboratory-anchor-held-out execution.

在真实第三方 receipts 到齐前，不建议以已完成强 Q1 生物学验证论文投稿；可继续准备 computational methods、provenance/reproducibility resource、benchmark 或 source-conditional portability 方向稿件。
