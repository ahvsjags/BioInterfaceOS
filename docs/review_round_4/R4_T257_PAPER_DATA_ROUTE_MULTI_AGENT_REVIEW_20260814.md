# R4-T257：论文数据替代路线五角色多智能体复评

日期：2026-08-14  
评审角色：Poincaré（方法统计）、Wegener（来源与跨实验室）、Popper（反方可证伪性）、Euler（模型工程）、Kant（EIC 编辑）  
状态：`MAJOR_REVISION_EXTERNAL_GATES_UNVERIFIED`

## 编辑结论

五个角色一致认为：全文论文、补充材料和 PRIDE/ProteomeXchange 数据已经足以构成真实、可追溯的 **paper-derived computational benchmark / reproducibility resource**，但不能把作者侧重算改写为独立生物学验证。

当前最稳妥的论文定位是：

> an auditable, source-conditional rank-portability method and benchmark for paper-derived protein-corona measurements

不应定位为四个独立生物队列的验证、donor-level generalization、普适 sequence superiority 或 clinical/biological validation。

## 五角色独立意见摘要

### Poincaré：方法与统计

- 数据兼容性：82；在 donor/sample/batch/source-cell 字段、license 和逐行 hash 全部闭合后，条件性可到约 91。
- 有效样本/生物学 n：当前约 58；全文数据不能把 pooled material、technical replicate 或 measurement batch 变成 donor n。
- 统计执行：当前约 86；完成 donor-aware accounting、clean replay、selection-aware uncertainty 后条件性可到约 92。
- 关键建议：把 `n_biological`、batch、technical replicate 和 unresolved unit 分开报告，不要用 rows 或 batches 替代 biological effective n。

### Wegener：来源与跨实验室

- T249/T238 确有 4 个 laboratory/source anchors、7 个严格 common targets 和 783 条 row-traceable held-out observations。
- PMC6592156 是 pooled plasma/condition batches；Dalian donor 未解析；Edinburgh 当前 map 缺 donor crosswalk；UCD 同时含 biological timepoint 和 technical replicate 语义。
- 这些来源支持 provenance 和 source portability，不能合并成四个独立生物队列。
- PXD032162、PXD020584、PXD028310、PXD050779、PXD053359 的排除或 sensitivity 结果应保留，不得为了增加样本数而放宽 admission。

### Popper：反方与可证伪性

最强反例是五类：伪独立、availability/target 泄漏、endpoint 不一致、作者运行冒充外部复现、许可证/归档边界不清。必须在正文和补充材料中提供：

- source/laboratory/study/material/assay/endpoint/unit/license 矩阵；
- fold-local target、feature、missingness、standardization 和 alpha selection DAG；
- full、composition-only、constant、paired ablation、permutation、失败运行和负结果；
- author-run、software replay、no-author reproduction、lockbox、adoption、DOI 六类证据的独立 ledger。

### Euler：模型与工程

- T238 的 source-held-out、nested selection、3-model comparison 和 T255 batch-cluster bootstrap 可由固定 processed-data assets 重算。
- T255 初版报告曾指向不存在的 `v1.0.1` CSV 路径，且 verifier 没有检查 artifact path/hash；该问题已在当前 commit 修复。
- 现在 T255 report/receipt 绑定 registry hash、newline-normalized execution-module hash、paired-ablation hash、实际 CSV 路径和 CSV hash；strict verifier 已通过。
- 仍不能声称 donor-level effective n、raw-MS independent reproduction 或普遍 sequence superiority。

### Kant：EIC 编辑

- 决定：`MAJOR_REVISION`。
- 推荐主定位：computational methods + benchmark/resource；生物学结果仅为 source-conditional exploratory evidence。
- 若没有真实第三方 receipt，不建议以 biological discovery 或 universal prediction 论文投稿。
- 投稿前必须获得非作者 lockbox、无作者 accession-to-result reproduction、两个非作者用户/机构采用记录以及 DOI/immutable archive read-back。

## 复评评分（证据门槛口径）

下表是本轮用“真实 artifact/receipt 才计分”的保守评分，不把 issue、模板、作者重跑或 GitHub release 当成外部证据；与早期把“准备度”计入分数的快照不直接等价。

| 模块 | T257 保守分 | 主要依据 | 到 90 的最小条件 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 82 | T238/T249 provenance、4 source anchors、7 strict targets | donor/sample/batch crosswalk、endpoint compatibility、license/read-back 全闭合 |
| 统计分析设计 | 88 | estimand、fold-local target、nested selection、missingness 和 failure rules | 冻结完整 DAG、multiplicity/有限 null 口径并完成独立审计 |
| 统计执行与有效样本 | 82 | T238 已执行；T255 artifact binding 已修复；donor n 仍未解析 | clean replay、donor/biological-unit accounting、selection-aware uncertainty |
| 模型、消融与 OOD | 78 | 3 模型、paired ablation、negative control、source OOD | 预注册 OOD、保留负结果、补齐 selection-aware 和 biological-unit uncertainty |
| Protected lockbox | 0 | 当前只有 handoff，无非作者 receipt | 非作者持有 protected input 并提交 aggregate-only signed receipt |
| No-author reproduction | 0 | 当前只有作者侧运行与候选 handoff | 非作者从 fixed tag + public accession 独立重算并提交 receipt |
| 外部采用 | 0 | Issue #2 尚无非作者安装/使用 receipt | 两个不同非作者用户/机构完成不同真实任务 |
| DOI immutable archive/read-back | 10 | Git tag/release 已有，真实 DOI read-back 缺失 | 认证归档服务返回 DOI、archive hash 和 manifest read-back |

这个评分下的核心均值仍远低于强 Q1 生物学验证门槛，编辑决定保持 `MAJOR_REVISION`；内部方法/benchmark 质量可以继续提高，但外部门槛不能由作者侧计算预支。

## 本轮验证结果

- KAUST 全套测试：`584 passed, 13 skipped`；
- T255 targeted tests：`3 passed`；
- strict T255 verifier：`outer_folds=4 models=3 metric_rows=36 donor_level_effective_n_claimed=false scientific_submission_ready=false`；
- ruff check：通过；
- ruff format check：`384 files already formatted`；
- mypy：`Success: no issues found in 192 source files`；
- KAUST 工作树仅保留用户原有 `M reports/CONTRACT_AUDIT.md`，未被本轮修改。

## 最终门槛

在真实第三方 receipt 到达并通过审计之前，最终状态保持：

```text
paper_fulltext_and_pride_route=true
author_side_replay=true
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```
