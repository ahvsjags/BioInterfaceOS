# R4 T211：论文数据驱动的多智能体终审与强 Q1 改进目标

日期：2026-08-14  
审查基线：`cb6a3d18666e901eb6d8f3d3e79ad5dbd9384fa6`（T209 Manchester v1.1 修正后）  
审查角色：统计学主编、计算生物学编辑、可复现性/开放科学审稿人、devil's-advocate 高影响力期刊审稿人  
审查方式：四个独立代理分别读取当前仓库、数据注册表、执行报告、KAUST 验证状态和公开版本信息；本报告仅整合共识，不把代理意见当作外部科学验证。

## 1. 编辑结论

**当前决定：NOT READY — MAJOR REVISION。**

BioInterfaceOS 已经从“只有协议、没有真实结果”推进到：

- 使用公开论文全文及其补充数据重建了可追溯的 processed-data 分析路径；
- 完成了三来源共同 target 的开发/可迁移性分析；
- 完成了 PMC10257194 论文队列和 Manchester 论文队列的 author-run OOD；
- 对 Manchester 公开矩阵与论文临床队列的 `HA5` 不一致进行了 hash-bound reconciliation；
- 在 KAUST 上完成严格数据校验、测试和 Python 编译；
- 明确保留 `independent_validation=false`、`external_scientific_reproduction=false`、`external_user_adoption=false`、`doi_archived=false` 和 `scientific_submission_ready=false`。

当前最准确的论文定位是：

> 一个具有行级 provenance、许可证感知、冻结 target、nested selection、cluster-aware uncertainty 和多来源 paper-data reanalysis 的可审计 protein-corona proteomics rank-portability 方法/软件框架。

它还不是生物学机制、临床标志物或“sequence features 普遍优于 composition-only”的研究。

## 2. 论文全文数据能解决什么，不能解决什么

### 2.1 可以解决的证据问题

论文全文和补充数据能够提供真实实验产生的 processed measurements，足以支持：

1. 对来源、论文、补充表、worksheet、行/列、样本标识和 hash 的逐项 provenance 审计；
2. 公开数据上的冻结 target、source-local ranking、paired ablation 和 study-held-out sensitivity；
3. 研究/来源/实验室层面的结果方向比较和负向结果披露；
4. 缺失、正值筛选、可用性选择和队列计数的 reconciliation；
5. 软件、数据指针、执行 receipt 和统计结果的可复核性；
6. 作为 methods/software 论文的经验性 benchmark 和 failure-boundary 证据。

### 2.2 不能替代的证据

论文表格不等于 raw mass-spectrometry files、完整 acquisition log、未公开 QC、未观测缺失机制或新实验。仅由作者重新运行公开论文数据，也不能产生：

- 非作者 protected lockbox evaluator receipt；
- 无作者参与的端到端科学复现；
- 外部用户真实安装、任务运行和 adoption receipt；
- 正式 DOI/archive receipt；
- 正交 binding assay、干预证据、机制验证或临床效用。

因此，新增论文数据应被命名为 `published-data reanalysis`、`paper-attached processed matrix` 或 `analysis-only external dataset`，不得命名为 `new raw experimental validation` 或 `independent biological validation`。

## 3. 当前数据和执行证据

| 证据路线 | 当前结果 | 合法支持的结论 | 不支持的结论 |
|---|---:|---|---|
| T192/T195 三来源共同 target | 3 个 laboratory/source anchors，9 个共同 accession，809 observations，85 measurement batches，3 个 leave-one-lab folds | 可审计的跨来源 portability sensitivity | 3 个独立生物学队列、独立生物学验证、普遍人群泛化 |
| T203 PMC10257194 | 4,362 source cells，97 shared proteins，45 units/batches；full 0.1773，composition 0.1532，delta +0.0241，CI [0.0202, 0.0284] | 一个论文队列上的 author-run exploratory OOD，full/composition 方向为正 | protected lockbox、无作者复现、独立验证、机制 |
| T209 Manchester v1.1 | 排除未被 Supplementary Data 3 锚定的 HA5；60 paper-anchored units，288 batches，4,150 target cells；full 0.2918，composition 0.3514，delta -0.0596，CI [-0.0786, -0.0409] | 另一个论文队列上的 author-run OOD，并暴露 sequence increment 的失效边界 | full model 普遍优于 composition、稳定机制或临床效用 |
| T197/T198/T200 | target availability、coverage threshold、missingness、estimand、multiplicity/closure receipt 已通过 | 统计执行路径和审计工程可运行 | 缺失机制无偏、完整 multiplicity 已统一、独立性已证明 |
| KAUST clean checkout | 关键 strict verify、4 个回归测试和 compileall 通过 | 作者控制环境内的软件/数据管线可复现 | 无作者科学复现、外部采用 |

最重要的科学结论不是“full model 在所有来源有效”，而是：

> sequence-level increment 在不同来源中的方向和大小不稳定；BioInterfaceOS 的可发表价值应转向识别这种 source-dependent portability 与失效边界。

## 4. 多智能体综合评分

分数为编辑保守评分，不是简单平均；lockbox、无作者复现、采用和 DOI 等硬门禁会对强 Q1 综合成熟度产生非线性影响。

| 模块 | 当前分数 | 90 分门槛 | 编辑判断 |
|---|---:|---:|---|
| 数据兼容性、许可证和行级 provenance | 85 | ≥90 | source registry、cell map、hash 和 analysis-only 边界较强；Manchester matrix 许可证仍不明确 |
| 独立生物学样本基础/有效 biological n | 35 | ≥90 | 809 observations/85 batches 不能等于 biological n；Dalian pooled、Edinburgh donor unresolved、UCD technical replicate |
| Estimand 与统计设计 | 85 | ≥90 | T200 较强，但 T195/T203/T209 的 primary aggregation/null policy 尚未完全统一 |
| 统计执行完整性 | 80 | ≥90 | 真实数据、bootstrap、OOD 和负对照已执行；统计假设、selection bias 和 full multiplicity 仍需强化 |
| Missingness/availability bias | 74 | ≥90 | 审计完整，但尚未完成 MNAR/pattern-mixture/bounds 或正式 availability correction |
| 模型、消融与 OOD | 73 | ≥90 | 结果真实且含正负方向，但缺少统一 baseline、study-by-model interaction 和正式异质性汇总 |
| 方法/软件创新 | 72 | ≥90 | provenance、claim gate 和统计审计有方法学价值；ridge/sequence descriptor 组合本身不是新算法 |
| 生物学新发现/机制 | 22 | ≥90 | 当前没有机制、因果、正交实验或临床终点证据 |
| Claim discipline | 93 | ≥90 | 当前最强；明确没有把 paper OOD 写成 independent validation |
| 软件公开发布/版本一致性 | 64 | ≥90 | 当前 HEAD `cb6a3d1` 含 T209，但 public `v0.1.3-r10.16` 仍绑定旧 commit `82c5b21` |
| 独立 lockbox evaluator 实证 | 10 | ≥90 | 只有 protocol/schema 和内部工程 receipt，无非作者 evaluator receipt |
| 无作者科学复现 | 5 | ≥90 | KAUST 是 author-run engineering verification，不是 no-author reproduction |
| 外部用户采用 | 0 | ≥90 | GitHub Issue #2 仍是招募请求，没有独立安装/任务 receipt |
| DOI/archive | 18 | ≥90 | deposit package 已准备，但 `doi=null`、`archive_locator=null` |
| 强 Q1 综合成熟度 | **54** | ≥90 | 当前为成熟的作者控制型 methods/audit package，尚非稳投强 Q1 实证论文 |

## 5. 四个代理共同确认的拒稿风险

### CRITICAL：不能把实验室锚点写成独立生物学队列

T192/T195 的三个 anchor 代表数据来源/实验室 lineage，而不是三个独立 donor-resolved biological cohorts。缺失的 donor ID、pooled plasma 和 technical replicates 不能从蛋白表格中推断或创造。

**必须执行：**所有结果并列报告 row、measurement batch、biological unit、donor/study unit，并在标题、摘要、结果中使用 `laboratory/source anchor` 与 `paper-derived processed data`。

### CRITICAL：不能把 measurement batch 写成 biological n

T209 的 288 batches 属于 60 个 paper-anchored patient clusters；T198 的 666 qualified batches属于 141 个 biological units。bootstrap 次数不会增加独立生物学个体。

**必须执行：**主分析优先以 biological-unit/patient cluster 汇总；batch 只作为测量层不确定性；对无法恢复 donor 层级的来源明确标记 `donor unresolved`。

### CRITICAL：OOD 不是 independent validation

T203 和 T209 都是作者访问公开论文数据后执行的 analysis-only OOD。它们是重要的 transportability evidence，但不是非作者 lockbox、独立 evaluator 或无作者复现。

**必须执行：**统一使用 `author-run paper-cohort OOD`，把 `independent validation` 仅保留给未来非作者保护数据 receipt。

### MAJOR：full/composition 方向跨来源异质

T203 delta 为正，而 T209 delta 为负，T197 的部分 held-out source 近零。若继续主张普遍 sequence superiority，必然被拒稿。

**必须执行：**以 effect size/CI 和 source/study interaction 为主结果；统一 primary endpoint；将历史固定 alpha 的 permutation 结果降为 exploratory，不能拼成 confirmatory family。

### MAJOR：analysis-only 数据不能自由再分发

PMC10257194 为 CC-BY-NC-ND；Manchester author matrix repository license 未明确。raw workbook、source map 和 numeric derivative 必须留在 analysis-only 路径。

**必须执行：**公开 accession、下载脚本、source map schema、hash 和许可证指针；不把受限数据打包进入 Apache-2.0 release 或 DOI 数据附件。

## 6. T211 新一轮改进目标

### 目标定义

在不虚构新实验、外部参与或第三方回执的前提下，将 BioInterfaceOS 重构为：

> **paper-data-grounded, source-conditional, auditable protein-corona rank-portability benchmark/software paper**

并使所有“我们可控制的模块”达到至少 90 分；对于 lockbox、无作者复现、外部采用和 DOI，建立可验证的交付包并等待真实第三方/归档服务产生 receipt。只有所有硬门禁真实通过，`scientific_submission_ready` 才能变为 true。

### P0：统一论文主 estimand 与 claim boundary（可由本地完成）

- 冻结唯一主 estimand：以 study/paper-derived source 为外层单位，以 biological unit/patient cluster 为独立层，以 source-local rank Spearman 为 primary metric，以 full-minus-composition 为主要 contrast；
- 将 T195/T203 的 fixed-alpha permutation 标为 descriptive/exploratory；
- 将 T197/T198/T209 的 selection-reexecuted null policy 统一到同一 protocol；
- 在 README、manuscript outline、registry、receipt 和 release manifest 中禁止 `independent validation`、`three independent biological cohorts`、`universal superiority`、`mechanism`、`clinical utility`。

**验收证据：**一份统一 statistical closure amendment、全仓库 claim grep 无越界词、所有 primary/sensitivity/OOD 路线均指向同一 estimand。

### P1：用全文数据正式执行 source/study heterogeneity（可由本地完成）

- 对 T195、T197、T203、T209 以 study/source 为单位汇总 effect size 和 CI；
- 报告 source-by-model interaction、研究级权重、patient/biological-unit cluster sensitivity；
- 给出 positive、near-zero、negative 的完整 forest/table，而不是只强调 T203 正向结果；
- 将结论改为“可诊断的条件性 portability”，并提供最小实际有意义增量的预设阈值。

**验收证据：**带 hash 的 heterogeneity report、study-level table/forest artifact、统一模型比较测试和回归测试。

### P1：补强 paper-data 有效样本与缺失敏感性（可由本地完成，能力有限）

- 对每条来源报告 row/batch/biological unit/donor/study 五层 n；
- 增加 coverage threshold、pattern-mixture、worst-case bounds 或 inverse-probability sensitivity（仅在字段允许时）；
- 对 target availability 公开被排除集合、排除原因及 detection/abundance/sequence covariate 分层；
- 对 donor unresolved、pooled、technical replicate 做显式降权或限制性解释。

**能力边界：**没有原始检测限、完整 donor manifest 或 pooled sample 拆分信息时，只能证明“已审计敏感性”，不能声称 MNAR 已被消除或 biological independence 已恢复。

### P1：增加方法学 head-to-head baseline（可由本地完成）

- 固定同一 target、同一 outer split、同一 primary endpoint；
- 比较 constant、composition-only、length/charge/hydrophobicity 等低维 baseline、随机序列负对照和现有可获得 workflow；
- 报告 calibration/coverage、运行成本、失败率和 source-dependent performance，而不只报告单一 Spearman。

**验收证据：**预注册 baseline table、paired contrasts、negative controls、完整失败列表和 reproducible command。

### P2：完成版本、发布和 DOI 绑定（本地可完成前半段；归档 receipt 需外部服务）

- 生成包含 T209 v1.1 的新 immutable release（计划 `v0.1.3-r10.17`）；
- 将 source commit 写入 manifest，生成 archive、sidecar SHA-256、release notes 和 clean-checkout 验证；
- 同步 README、Issue #2、KAUST 分支和报告中的版本指针；
- 提交 Zenodo/等效服务后，只有收到真正 DOI/archive locator 才将 `doi_archived` 改为 true。

### P0 外部证据交付包（不能由本地完成，必须由真实第三方完成）

1. 非作者 evaluator 持有 protected input，按 T166 一次性运行并签名 aggregate receipt；
2. 无作者参与团队从 immutable release 和公开 accession clean checkout 起步完成端到端科学复现；
3. 至少两个非作者用户完成独立安装和真实任务，提交环境、命令、日志、输出 hash、失败说明和身份/COI 声明；
4. 独立编辑/审计者核验身份、版本、receipt hash 和 DOI 后，才可更新 hard gates。

本地可以准备 handoff、schema、命令、预检器和空模板；本地不能填写第三方身份、生成 protected data receipt 或把作者运行改名为 external evidence。

## 7. 目标达成条件与投稿路线

### 仅使用论文数据时的可行路线

即使不新增湿实验，完成 P0/P1/P2 后，最有竞争力的路线仍是 methods/software 或 reproducibility/benchmark 论文。论文主标题和摘要应围绕：

- auditability；
- provenance；
- license-aware data reuse；
- source-conditioned portability；
- positive/negative OOD；
- failure-boundary diagnosis。

### 生物学强 Q1 路线的不可替代条件

若目标是生物学发现、机制或临床强 Q1，仅靠论文全文数据不能达到 90 分；还需要正交实验、donor-resolved independent cohort、机制/临床终点以及真实第三方复现。没有这些证据，不应使用 biological-discovery 叙事投稿。

## 8. 最终 gate ledger

```text
data_compatibility_and_provenance = 85/100
statistical_design = 85/100
statistical_execution = 80/100
model_ablation_and_ood = 73/100
independent_validation = false
protected_lockbox_evaluator_receipt = false
external_scientific_reproduction = false
external_user_adoption = false
doi_archived = false
scientific_submission_ready = false
```

**T211 结束状态：**已完成多智能体终审、证据等级重分类和新一轮改进目标定义；未将任何不可由当前作者控制范围产生的外部事实标记为完成。下一步应先完成 T211 P0/P1 的统计统一、异质性报告和版本绑定，再等待真实第三方回执后复审。

## 9. 主要证据入口

- [T195 三来源共同 target 执行](R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_STATUS_20260814.md)
- [T200 统计闭合](R4_T200_STATISTICAL_CLOSURE_STATUS_20260814.md)
- [T203 PMC10257194 OOD](R4_T203_PMC10257194_PAPER_OOD_STATUS_20260814.md)
- [T208 跨来源 claim repair](R4_T208_MULTI_SOURCE_CLAIM_REPAIR_20260814.md)
- [T209 Manchester 队列校正](R4_T209_MANCHESTER_COHORT_RECONCILIATION_20260814.md)
- [T166 外部 evaluator/reproduction protocol](../data/R4_T166_EXTERNAL_EVALUATOR_AND_REPRODUCTION_PROTOCOL.json)
- [T167 外部采用 intake](../data/R4_T167_EXTERNAL_USER_ADOPTION_INTAKE.json)
- [PMC10257194](https://pmc.ncbi.nlm.nih.gov/articles/PMC10257194/)
- [PMC13212878](https://pmc.ncbi.nlm.nih.gov/articles/PMC13212878/)
