# R4-T256：论文全文数据替代路线逐条完成审计

日期：2026-08-14  
状态：`IN_PROGRESS_EXTERNAL_GATES_UNVERIFIED`  
目的：把“没有新增湿实验样本”转化为可审稿、可复核、可复现的公开实验数据路线，并明确哪些要求已经由全文/补充材料/公共 accession 支持，哪些要求仍然必须由非作者第三方完成。

## 结论先行

全文论文、补充表和 ProteomeXchange/PRIDE accession 已经提供了真实的、可追溯的公开测量结果，足以支撑一个**paper-derived computational benchmark / reproducibility resource**。当前最强主路线是 T238：四个来源锚点、四个外层 source-held-out folds、7 个严格交集 canonical targets、783 个非重复 held-out 观测、nested selection、paired composition ablation、selection-reexecuted permutation control 以及 T255 的 measurement-batch cluster bootstrap。

这条路线解决了“没有可审计真实数据”的问题，但不能把作者自己运行的公开数据分析改写成非作者验证。因而当前不能声称四个独立生物学队列、lockbox、无作者复现、外部采用、DOI 归档或 `scientific_submission_ready=true`。

## 1. 数据替代方案的操作定义

本轮将“真实实验数据”限定为：

1. 已发表论文正文或补充材料中可定位的数值结果，或公共 accession 中可独立重新获取的作者结果/原始输入；
2. 每一行能回溯到 source、study、laboratory、sample/measurement batch、protein accession 和原始文件位置；
3. 允许的 license / access 条款已登记；
4. 在 target freeze 和模型执行前固定 inclusion、missingness、zero、rank 和 batch 规则；
5. 对不能公开再分发的材料只保留 hash、摘要和 analysis-only 结果，不把受限矩阵放进公开 release。

“全文报告了 n 个样本”不等于可用于模型的逐样本矩阵；“技术重复”不等于独立 donor；“作者重跑的 OOD”不等于外部验证。本审计强制保留这三个边界。

## 2. 逐条证据审计

| 要求 | 当前权威证据 | 状态 | 允许的论文表述 | 仍缺的硬证据 |
|---|---|---|---|---|
| 可追溯真实公开数据 | T222 paper-data fallback；T249/T238 source registries、source-cell maps、row ledgers | `VERIFIED_INTERNAL` | public paper-derived measurements / auditable source-cell provenance | 无新增湿实验样本；不能写成新采集队列 |
| 至少三个实验室锚点 | T192/T195/T249；T238 严格四来源路线 | `VERIFIED_INTERNAL` | four laboratory/source anchors | donor semantics 仍需按来源分别描述，不能统一写成四个 donor cohorts |
| 冻结共同 target | T249：4-source 严格交集为 7 个 target；T238 每个 outer fold 从 development sources 选择 9/9/10/10 targets | `VERIFIED_INTERNAL` | fold-local availability-aware target set | 7-target intersection 较保守，不能事后扩 target |
| source-held-out 可执行统计 | T238 protocol/report；4 folds、3,061 development rows、783 non-repeated held-out rows | `VERIFIED_INTERNAL` | exploratory source portability benchmark | 仍是 paper-derived/exploratory，不是临床泛化 |
| nested selection 不泄漏 | T238 development-only target selection；permutation null 每次重跑 selection | `VERIFIED_INTERNAL` | preregistered nested selection and re-executed null | 需外部团队复核执行，而非作者再跑 |
| cluster-aware uncertainty | T255 protocol/report；按 `(outer_fold, held_out_source, measurement_batch)` 聚类，2,000 次 percentile bootstrap | `VERIFIED_INTERNAL` | batch-cluster uncertainty intervals | 未产生 donor-level effective n；不能把 batch 数写成生物学 n |
| full/composition/constant 模型与 paired ablation | T238/T255 outputs；每 fold 三模型；negative control 保留 | `VERIFIED_INTERNAL` | predeclared model comparison with negative results retained | sequence increment 在若干来源为零或不稳定，不能预先写成 superiority |
| 真实 external OOD | T203 PMC10257194、T209 PMC13212878 等全文/补充矩阵的 author-run analysis-only routes | `PARTIAL_PUBLIC_DATA` | author-run paper-derived OOD / analysis-only sensitivity | 受限矩阵未进入公共 release；仍不是 independent validation |
| technical sensitivity | T246 PMC11328176（六个 core，技术重复）与 T177 PMC13106918（批次 OOD） | `PARTIAL_PUBLIC_DATA` | technical heterogeneity / endpoint stress test | 不能把 core 或技术重复计作独立生物学队列 |
| 候选来源的负结果审计 | T231/T232：PXD032162、PXD020584、PXD028310、PXD050779、PXD053359 等分层或排除 | `VERIFIED_INTERNAL` | prespecified exclusion and failure-boundary ledger | 不能因结果不理想重新放宽 admission threshold |
| 非作者 protected lockbox | T252 handoff；GitHub Issue #2 仅为招募与协调 | `MISSING_EXTERNAL` | 只能写“lockbox protocol prepared” | 非作者身份、COI、受保护 held-out input、aggregate receipt、失败记录 |
| 无作者参与的科学复现 | T252 handoff；固定 release `v0.1.3-r10.42` | `MISSING_EXTERNAL` | 只能写“reproduction package prepared” | 非作者团队从 accession/raw input 到结果的独立 receipt |
| 外部用户采用 | Issue #2 现有评论均为作者更新；没有非作者安装报告 | `MISSING_EXTERNAL` | 只能写“publicly available” | 至少两名非作者用户/机构完成不同任务并留下日志与输出 hash |
| DOI / immutable archive | GitHub release `v0.1.3-r10.42` 已公开；CITATION metadata 仍写 DOI pending | `PARTIAL_PUBLIC_DATA` | immutable Git tag/release | DOI 服务的真实 deposit 与 read-back manifest hash |
| 强 Q1 submission-ready | T238/T254/T255 均显式 `scientific_submission_ready=false` | `MISSING_EXTERNAL` | methods/benchmark/resource manuscript | 所有 external gates 真实 receipt + 最终多智能体复评 |

## 3. 目前可采用的三层数据架构

### A. 主分析层：可公开再分发、严格 source-held-out

只使用 T238 固定的四来源路线。它的价值不是伪造“大样本”，而是提供一条可审计的 availability-aware rank portability 分析：

- 4 个 held-out source folds；
- 3,061 个 development observations；
- 783 个不重复 held-out observations；
- 115 个 measurement-batch clusters；
- 每个 fold 只用 development source 冻结 target 和选择超参数；
- 结果同时报告 full、composition-only、constant baseline、paired ablation、permutation null 与 batch-cluster CI。

### B. 外部敏感性/OOD 层：真实数据，但不能改变主分析 contract

T203、T209、T246、T177 等来源仍然有科学价值，但由于 endpoint、license、donor semantics 或公开矩阵条件不同，只能作为 paper-derived OOD、technical sensitivity 或 failure-boundary evidence。它们不能增加主分析的 effective n，也不能补发独立验证 receipt。

### C. 外部证据层：必须由第三方产生

lockbox、无作者复现、外部采用和 DOI read-back 不可能仅通过再下载一篇论文获得。项目可以把输入、协议、容器、验收 schema 和 handoff 准备好，但 receipt 的身份和运行必须来自项目控制范围之外。

## 4. 为达到各模块 90 分的最小闭环

以下是“数据路线”和“投稿路线”分开的硬条件：

| 模块 | 90 分最低条件 | 论文全文数据能否单独完成 |
|---|---|---|
| 数据兼容性与样本基础 | >=3 个实验室锚点、统一 endpoint、冻结 target、每行 provenance、独立单位语义完整 | 基本可以把当前内部证据推到高 80；若坚持 donor-level biological claim，仍不足 |
| 统计分析设计 | estimand、nested selection、cluster uncertainty、missingness、failure rules 在执行前固定 | 可以；当前设计已有强证据 |
| 统计执行与有效样本 | 所有冻结路线一次性重算，报告 cluster/donor/unit accounting 与完整 CI | 可以补强执行；不能把技术 batch 变 donor n |
| 模型、消融与 OOD | 成对 ablation、简单基线、负对照、至少一个预注册 OOD，保留负结果 | 可以补强到接近投稿要求；不能承诺 sequence superiority |
| protected lockbox | 非作者一轮盲评 receipt，含失败和 aggregate-only 输出 | 不能；必须外部参与 |
| no-author reproduction | 非作者从固定 tag + accession 独立重建结果 | 不能；必须外部参与 |
| 外部采用 | 两个非作者环境真实安装并执行不同任务 | 不能；必须外部参与 |
| DOI/archive | 真实 deposit 后 immutable read-back hash | 不能；必须外部服务操作 |

因此，合理的目标不是“用论文数据把所有分数人为改到 90”，而是：

1. 用论文全文数据把内部科学核心做成可复核的高质量 benchmark/resource；
2. 用固定公开 release 招募第三方完成四个外部门槛；
3. 在 receipt 到齐后再运行最终五角色编辑复评；
4. 若外部门槛在预定窗口内仍没有真实参与者，诚实地将稿件定位为 methods/resource，而不是强 Q1 biological discovery。

## 5. 当前不可夸大的分数快照

T239/T253 的保守快照为：

- 数据兼容性与样本基础：82；
- 统计分析设计：88；
- 统计执行与有效样本：77；
- 模型、消融与 OOD：75；
- protected lockbox：12；
- no-author reproduction：8；
- 外部采用：46；
- DOI immutable archive/read-back：25；
- 描述性总体均值：51.6；决策：`MAJOR_REVISION`。

T255 增加了 cluster-aware uncertainty artifact，但在五角色复评重新核验前不预发新的分数。外部四项仍保持未验证，不能因 GitHub release、作者运行、模板或 issue 招募记录而上调到 90。

## 6. 当前固定交付与复核入口

- T238 主分析 protocol/report/ledger：`docs/data/R4_T238_*` 与 `reports/review_round_4/t238_four_source_availability_execution/v1.0.0/`
- T249 四来源 common-target audit：`docs/data/R4_T249_*` 与 `reports/review_round_4/four_lab_common_target/v1.0.0/`
- T254 全文数据证据包：`docs/data/R4_T254_FULLTEXT_PAPER_DERIVED_EVIDENCE_PACKAGE_20260814.json`
- T255 cluster uncertainty：`docs/data/R4_T255_CLUSTER_UNCERTAINTY_*` 与 `reports/review_round_4/t255_cluster_uncertainty/v1.0.0/`
- 外部 handoff：`docs/external/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.md`、`docs/review_round_4/R4_T252_CURRENT_EXTERNAL_HANDOFF_20260814.md`
- 固定公开 release：[`v0.1.3-r10.42`](https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.42)，commit `ea00be2a3cfa61fe770f5020bc9cfd3a24246083`
- GitHub coordination issue：[#2](https://github.com/ahvsjags/BioInterfaceOS/issues/2)

本审计的机器可读版本为 `docs/data/R4_T256_REQUIREMENT_BY_REQUIREMENT_COMPLETION_AUDIT_20260814.json`。当前硬门槛仍为 `scientific_submission_ready=false`。
