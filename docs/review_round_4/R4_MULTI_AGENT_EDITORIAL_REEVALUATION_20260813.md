# BioInterfaceOS R4 多智能体编辑复评（2026-08-13）

## 结论

本轮完成了一个真实的工程改进：公开版本升级为 `v0.1.2-r5`，新增 cluster-sensitive OOD 审计、三类外部 receipt 的结构预检、哈希校验、非作者声明校验和不晋级输出；KAUST 锁定环境完成 `25 passed`。这提高了交付与审计完整性，但没有产生任何第三方事实。因此 `scientific_submission_ready` 仍为 `false`，稿件仍是方法/软件与可审计 benchmark 的 Major Revision，而不是强 Q1 生物学发现论文。

## 三类评审角色

| 角色 | 评审重点 | 当前判断 |
|---|---|---|
| 严格统计审稿人 | estimand、nested selection、cluster uncertainty、有效样本、模型和 OOD | 设计较强，但外部执行与独立有效样本仍未闭环 |
| 计算生物学期刊编辑 | 创新定位、增量价值、跨来源泛化、投稿层级 | 可继续按方法/软件论文推进；不能按独立验证或生物学机制论文包装 |
| 可复现性/开放科学审计员 | tag、KAUST replay、source hash、lockbox、无作者复现、采用 receipt | 软件路径可复现；第三方科学复现和真实采用仍为零证据 |

三名 agent 的独立综合判断存在量尺差异，但方向一致：严格强 Q1 证据分为 `28/100`；计算生物学方法/软件定位为 `54–72/100`；开放科学审计为 `45–56/100`；生物学发现稿约 `23/100`。差异来自“方法设计质量”和“第三方证据闭环”是否合并计分，不能解释为证据已经达到 90 分。

## Agent 复评中的关键新发现

- R4 的 134 个 measurement batches 中，部分来自 pooled plasma 的条件/技术重复；不能把 batch 数直接写成独立生物学样本数，需分别报告 condition、donor、laboratory 的 effective n。
- same-lineage OOD 中 full 模型 Spearman 约 `0.4002`，composition-only 约 `0.4049`，差值约 `-0.0047`，所以不能写成 sequence-driven 增量或机制证据。
- R4 的 rank-percentile estimand 是 source-local predictive estimand，不等价于总体 corona abundance、材料效应或机制 estimand；正文应收窄 claim。
- receipt preflight 的工程完整度可以评到约 `80/100`，但 protected lockbox、无作者复现和外部采用事实仍分别为 `4/100`、`0/100` 和 `0/100`（采用模块的 25 分只来自公开 handoff/可用性基础，不是第三方采用）。

## 保守模块评分

| 模块 | 当前分数 | 本轮变化 | 仍缺少的强 Q1 证据 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 58/100 | 不变 | 规模足够且独立于开发 lineage 的可重获外部来源、donor/cluster 独立性和冻结 primary OOD 门槛 |
| 统计分析设计 | 82/100 | 不变 | 第三方按冻结协议执行，并报告 batch/target/lineage/institution 有效单元和失败结果 |
| 统计执行与有效样本 | 40/100 | 工程交付增强，证据分不升 | 非作者执行的有效样本、missingness、CI、预注册 endpoint receipt |
| 模型、消融与 OOD 证据 | 42/100 | 不变 | 外部 held-out 中 full 相对 composition-only 的稳定增量、负对照和 OOD 不确定性 |
| 独立评估 / protected lockbox | 4/100 | 预检基础设施增强，证据分不升 | 非作者 evaluator、作者不可见 protected input、签名 aggregate receipt |
| 外部科学复现 | 0/100 | 不变 | 非作者 clean checkout、重获 accession、日志/输出 hash、结果和偏差 receipt |
| 外部用户采用 | 25/100 | handoff 公开化，证据分不升 | 至少两名非作者在不同环境完成不同任务并提交可核验使用记录 |

严格强 Q1 门禁综合分仍按最弱证据项判定为 `28/100`。这些不是同一量尺，不能用编辑视角的较高分抵消 lockbox、复现和采用的零分。

## 本轮新增、可核查的交付

- GitHub 版本化 handoff tag：`v0.1.2-r5`（固定 checkout，不使用移动的 `main`）。
- R4 receipt 结构预检：`src/biointerfaceos/r4_external_receipt_preflight.py`。
- CLI：`biointerfaceos data preflight-r4-external-receipts --strict`。
- 提交模板：`docs/data/R4_T172_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json`。
- 外部 handoff：`docs/external/INDEPENDENT_REPRODUCTION_AND_USER_HANDOFF.md`。
- 契约测试：本轮新增 cluster-sensitive 审计及 2 项测试；KAUST review_round_3 + review_round_4 总计 25 项通过。

预检唯一的通过状态是 `STRUCTURALLY_COMPLETE_PENDING_IDENTITY_REVIEW`。它只验证结构、字节哈希、声明的保护措施和 aggregate-only 字段；它不会认证身份，不会证明独立性，不会把作者 OOD 变成外部复现，也不会把 GitHub Issue 或下载量变成采用证据。

## 投稿决策

当前可以准备方法/软件、可审计 benchmark 或资源型稿件，正文必须把 Silver、Dalian 和 same-lineage 结果写成 exploratory/author-run，并删除 `independently validated`、`externally replicated`、`broadly generalizes`、`clinical utility` 等表述。

只有以下三类真实外部 artifact 到达并通过身份/范围审计后，才允许重新评分并考虑强 Q1：

1. 非作者 protected lockbox evaluator receipt；
2. 非作者端到端科学复现 receipt；
3. 至少两名非作者独立使用 receipt。

在这些 receipt 到达之前，不能通过改权重、补模板、作者重跑、合成数据或删除负结果把模块分数人为推到 90 分以上。

## Effective-n and missingness audit

The frozen R4 same-lineage candidate is now audited without changing the
primary endpoint. The aggregate artifact reports 8,064 source rows, 8,019
analysis-candidate rows, 7,075 rank-eligible rows, 142 measurement batches,
and 134 batches meeting the primary ten-protein threshold. It contains five
biological units but only one laboratory anchor: 106 primary batches are from
the pooled unit and 28 from four donor-labelled units. The source contains 956
`SOURCE_NA` rows; no missing values are imputed.

Protocol: `docs/data/R4_T174_OOD_EFFECTIVE_N_MISSINGNESS_PROTOCOL.json`.
Report: `reports/review_round_4/small_molecule_corona_effective_n/v1.0.0/r4_external_effective_n_missingness_report.json`.
This strengthens effective-n transparency but does not create independent
cross-laboratory evidence or raise `scientific_submission_ready`.

## Cluster-sensitive paired OOD audit

To prevent the 106 pooled measurement batches from dominating the same-lineage
OOD summary, the frozen R4 result is now summarized at the five biological
units and with a paired full-minus-composition ablation. The unit-weighted
mean Spearman is 0.2229 for `SEQUENCE_RIDGE_FULL` and 0.2346 for
`SEQUENCE_RIDGE_COMPOSITION_ONLY`. The unit-weighted paired delta is -0.0118
with a 2000-resample biological-unit bootstrap 95% interval of -0.0295 to
0.0111; the batch-weighted delta is -0.0047. Donor-labelled units have
deltas of -0.0261, -0.0328, -0.0280 and +0.0302, while the pooled unit is
-0.0022. Thus the added sensitivity analysis does not support a stable
sequence-specific gain, and it remains exploratory.

Protocol: `docs/data/R4_T175_OOD_CLUSTER_SENSITIVITY_PROTOCOL.json`.
Report: `reports/review_round_4/small_molecule_corona_cluster_sensitivity/v1.0.0/r4_external_cluster_sensitivity_report.json`.
This is still one-laboratory, author-run, same-lineage evidence; all
independent-validation, external-reproduction and submission-readiness flags
remain false.
