# R4 T193 多智能体编辑复审

日期：2026-08-14
对象：BioInterfaceOS T193 预冻结靶标、三来源 study-held-out 执行与外部证据门禁
编辑结论：**Reject / return before strong-Q1 submission; after external gates are completed, eligible for a new editorial round**

## 1. Panel composition

本轮综合了三个审稿角色：

1. provenance/data strict reviewer：审查 raw→map→ledger 闭合、行级追溯、multi-accession ambiguity、许可与 laboratory-anchor 语义；
2. statistical reviewer：审查预冻结 target universe、outer leave-one-laboratory-out、nested batch alpha、cluster bootstrap、消融与置换对照；上一轮统计 reviewer 的 T192 评分为 62/100，本轮结合 T193 实际执行结果更新；
3. senior editor/reproducibility reviewer：审查结果是否支持主张、模型是否稳健、外部 lockbox/复现/采用/DOI 是否真实闭合。

## 2. Conservative module scores

| 模块 | 本轮分数 | 编辑判断 |
|---|---:|---|
| 数据兼容性、许可与行级追溯 | **78/100** | T193 使用三来源、99 个 T192 前已冻结的 R3 target universe，1,495 条可追溯观测；但当前执行复用经过审计的 source maps，未在 T193 中从 raw 文件重新生成并逐行比对 map；Edinburgh 691/932、UCD 337/454 行带 multi-accession group ambiguity，不能称无歧义蛋白；三 anchor 也不等于三独立生物队列 |
| 统计分析设计与泄漏控制 | **92/100** | target membership leakage 已被预冻结 R3 universe 解决；outer study/laboratory hold-out、nested batch alpha、预先规定的 missingness/zero 规则与 cluster bootstrap 设计清楚 |
| 统计执行、有效样本与不确定性 | **87/100** | 1,495 行、85 batches、3 outer folds、2,000 bootstrap、256 permutation、配对消融均已实际执行；但有效独立层级最多是 3 个 laboratory anchors，Dalian pooled、Edinburgh donor ID 未编码、UCD technical replicates 不能提供 donor-level n |
| 模型、消融与 OOD 证据 | **58/100** | full ridge held-out Spearman 为 Dalian 0.444、UCD 0.331、Edinburgh 0.205；full−composition 为 −0.089、−0.037、+0.207，只有 Edinburgh 支持 full 优于 composition-only，不能主张稳健 superiority |
| 独立 evaluator / protected lockbox | **4/100** | 只有 protocol/handoff；没有非作者 evaluator 的一次性 receipt |
| 无作者科学复现 | **0/100** | 没有无作者团队从原始输入起步的 clean-checkout receipt |
| 外部用户采用与可用性 | **0/100** | 没有真实外部用户/机构安装、issue/PR、采用记录 |
| DOI 与不可变归档 | **30/100** | Git tag/release manifest 路径已准备并计划更新至 v0.1.3-r10.7；DOI/Zenodo 等外部归档 receipt 仍缺失 |
| 强 Q1 综合成熟度 | **31/100** | 内部 protocol、执行与可审计性显著增强，但外部证据硬门禁全部未闭合，且模型 superiority 不稳定 |

## 3. T193 实际结果

T193 使用在 T192 新来源进入项目之前冻结的 R3 99-accession target universe，三来源贡献 1,495 条有效正值观测：Edinburgh 932、Dalian 109、UCD 454。执行包含：

- 3 个 leave-one-laboratory-anchor-out outer folds；
- development-only nested leave-one-measurement-batch-out alpha selection；
- constant、full sequence ridge、composition-only ridge 三模型；
- 2,000 次 held-out measurement-batch cluster bootstrap；
- 每个 outer fold 256 次 development-batch 内 rank permutation；
- paired full-minus-composition ablation；
- source-local rank、zero/blank/missingness 和 multi-accession 标记保留。

结果必须按 source-local availability-conditioned rank portability 解读，不是 99-target external validation。每个新 source 实际可检测 target 数为 Edinburgh 23、Dalian 22、UCD 15；缺失与非正值被保留为状态但不进入 rank，因此 target availability bias 仍是 estimand 的组成部分。

## 4. Panel consensus: what T193 fixed

T193 确实解决了 T192 的一个关键问题：新来源没有参与 target membership、outer fold、alpha 或 model selection。因而可以使用以下表述：

> T193 is a pre-registered exploratory leave-one-laboratory-anchor-out portability analysis using an R3 99-accession target universe frozen before T192 source admission, with source-local positive-observation availability retained.

它不能使用以下表述：

- “99-target external validation”；
- “three independent biological laboratories/cohorts”；
- “1,495 independent observations”或“85 independent batches”；
- “nine unambiguous common proteins”；
- “full model is robustly superior to composition-only”；
- “independent validation”、“lockbox evaluation”或“strong-Q1-ready”。

## 5. Remaining blocking findings

1. raw→map closure 仍依赖先前 source-audit 生成的 map；T193 自身完成的是 map→ledger closure，不是从每个 raw asset 重新解析的 raw→map→ledger closure。
2. multi-accession group rows 已被标记但未从主分析中排除或聚合；因此结果是 canonical-accession-labelled sensitivity observation，而不是无歧义蛋白定量。
3. availability-conditioned target set 在三个 source 间不同；99 是 pre-frozen universe，不是每个 held-out source 都观测到的 99 个 target。
4. negative control 固定 observed nested alpha；其 p 值是 conditional-on-selected-alpha 的探索性 null，不是每次 permutation 都重新 nested selection 的完全选择校正检验。
5. 三个 laboratory anchor 的数量不足以提供稳健 biological-cluster uncertainty；Dalian pooled/unspecified，Edinburgh donor ID 未编码，UCD technical replicate 不能增加独立 n。
6. 外部 evaluator、无作者原始输入复现、两个外部采用 receipts、DOI archive 仍然是 0/缺失；GitHub issue 是请求，不是证据。

## 6. Editorial decision

**当前拒稿/退回，不能以 strong-Q1 级别投稿。** T193 把“没有真实数据/没有执行”推进到了“基于全文与公开仓库数据完成可复核的探索性跨来源执行”，并明显提高统计设计与执行模块；但它不能替代真实的非作者 lockbox、无作者复现、外部采用和 DOI 归档，也没有产生稳定的 full-model superiority。

当前所有 readiness flags 必须保持：

```text
independent_validation=false
external_scientific_reproduction=false
external_user_adoption=false
scientific_submission_ready=false
```

### 审稿依据

- [T193 protocol](../../docs/data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_PROTOCOL.json)
- [T193 registry](../../docs/data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_REGISTRY.json)
- [T193 execution report](../../reports/review_round_4/t193_three_lab_prefrozen_target_execution/v1.0.0/t193_three_lab_execution_report.json)
- [T193 execution receipt](../../reports/review_round_4/t193_three_lab_prefrozen_target_execution/v1.0.0/t193_three_lab_execution_receipt.json)
- [T193 status](R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_STATUS_20260814.md)
