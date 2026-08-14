# R4-T223：论文全文数据补强后的多角色编辑复审

日期：2026-08-14  
输入：T222 'FROZEN_PUBLIC_PAPER_DATA_FALLBACK' ledger、四条公开论文数据路线、KAUST strict replay、T221 外部证据门槛。  
审查方式：五个互不替代的编辑角色分别按证据评分；分数只反映当前可核查 artifact，不把作者运行、Codex 运行或 GitHub/KAUST 运行当作第三方证据。

## 1. 本轮新增的可审计事实

T222 将公开全文、Supplementary Data 和公共 accession 重新获取路线固化为 4 条 route、4 个 source registry、8 个 source map、4 个结果报告，共 16 个 hash-bound references：

| 路线 | 证据角色 | 当前可核查量 | 允许的结论 |
|---|---|---:|---|
| T178 三实验室共同 target | development compatibility | 3 个 laboratory anchors、99 targets、2,724 observations、47 batches、20,469 source cells | 开发集跨来源兼容性与逐行 provenance |
| T195 三实验室执行 | author-run exploratory portability | 9 个冻结 targets、809 observations、85 batches、3 outer folds、3 models | source-held-out exploratory execution |
| T181 论文附带 biological cohort | author-run paper OOD | 141 biological units、666 个合格 batches、17,026 observations、34 shared targets | paper-attached OOD 与 effective-n accounting |
| R3-T155 silver paper OOD | external reproduction candidate | 30 batches、953 observations、50 shared targets | 可供无作者 accession-to-result 复现的候选入口 |

所有 route 的 independent_validation、protected_lockbox_evaluator_receipt、external_scientific_reproduction、external_user_adoption、doi_archived 和 scientific_submission_ready 均保持 false。这是本轮最重要的 claim boundary。

## 2. 五个评审角色的独立判断

### Agent 1：统计编辑

**评分：92/100（统计模块）**

estimand、study-held-out、nested selection、batch/cluster uncertainty、missingness、multiplicity 和 source-by-model heterogeneity 已形成可审计闭环。T222 没有改变 primary estimand，也没有因加入论文数据而重新选择终点。扣分点是部分论文来源没有可解析的 donor ID，不能将 measurement batch 直接升级为 biological n；MNAR 仍是边界敏感性而不是已识别机制。

**编辑意见：**统计设计和执行足以支撑 computational benchmark / portability paper，但不能支撑跨研究 biological effect 的 confirmatory pooling。

### Agent 2：计算生物学领域编辑

**评分：91/100（模型、消融与 OOD）**

full、composition-only、constant baseline、paired ablation、within-batch permutation、多个 paper OOD 路线和不确定性输出均存在；同时保留了 Manchester 等负向或 near-zero 结果，降低了选择性报告风险。扣分点是不同论文的 assay、样本单位和实验室谱系仍不完全同构，结果更适合表述为 source-conditional portability，而不是普适生物机制。

**编辑意见：**当前最强贡献是“可审计的跨来源 protein-corona portability workflow”，不是材料机制发现。

### Agent 3：开放科学与复现编辑

**评分：94/100（数据许可、provenance 与工程 replay）**

T222 对每条路线绑定了全文 locator、许可证边界、source registry、source maps、输出报告和 SHA-256。KAUST clean checkout 已通过 T222 strict verify；R3/R4 回归套件为 57 passed、4 skipped，跳过项均因 analysis-only 资产未进入 clean public checkout 而明确排除。扣分点是 T222 尚未成为新的 immutable release/DOI 版本，当前仍属于 branch-level evidence。

**编辑意见：**“没有湿实验数据”已经被转化为可审计的 public paper-data fallback；但必须把原始材料、可再分发材料和 analysis-only 材料的边界保持在正文和 release 中。

### Agent 4：数据审计编辑

**评分：95/100（样本语义与 claim discipline）**

本轮将 laboratory anchor、measurement batch、biological unit、paper-attached cohort 和 external reproduction candidate 分开记账，避免把重复测量冒充独立样本。T181 的 141 biological units 和 T195 的 85 batches 没有被合并成一个虚假的总 biological n；silver route 也只被定义为候选复现入口。

**编辑意见：**数据审计已达到投稿级方法附件标准；正文还应在主结果表中显示每个 route 的 unit semantics 和禁止的外推范围。

### Agent 5：Devil’s Advocate / 强制反驳编辑

**评分：58/100（强 Q1 可接受性）**

最强反驳是：作者可以从全文补充表中获得真实测量值，但仍由作者决定数据入口、预处理、模型运行和解释；因此 paper-derived data 证明的是“公开数据上的可复核分析”，不能单独证明独立 evaluator 的性能、无作者科学复现、外部用户采用或生物学重复。若稿件把四条路线写成“external validation”，审稿人会要求降级结论甚至拒稿。

**必须保留的负面结论：**T222 不能关闭 protected lockbox、no-author reproduction、external adoption 或 DOI archive 四个硬门槛。任何把这些字段改成 true 的行为都必须等待真实第三方 receipt，而不能通过新增论文数据绕过。

## 3. 当前模块评分

| 模块 | T221 | T223 | 评分依据 |
|---|---:|---:|---|
| 数据兼容性、许可与逐行 provenance | 92 | **94** | T222 四条 route、16 个 hash-bound references、8 个 source maps、许可证和 unit semantics 均入 ledger |
| 统计分析设计 | 90 | **90** | primary estimand、nested selection、cluster uncertainty、missingness 与 multiplicity 已冻结 |
| 统计执行与有效样本 | 91 | **92** | T195/T181/T194/T217 均有真实 paper-derived 执行和有效 n 记账；donor ID 缺失仍限制外推 |
| 模型、消融、负对照、OOD 与不确定性 | 91 | **92** | 多模型、paired ablation、permutation、paper OOD 和负向结果均有报告 |
| 来源异质性与 claim discipline | 93 | **95** | route、lab、batch、biological unit 与 reproduction candidate 分层，禁止 pooled biological inference |
| 工程审计与 KAUST replay | 94 | **95** | strict verify、hash-bound receipt、57 passed/4 skipped，analysis-only 排除有明确理由 |
| immutable public version binding | 92 | **92** | 当前 T222 在新分支，尚未绑定新的不可变 release 与 DOI |
| 非作者 protected lockbox evaluator | 10 | **10** | 没有真实非作者 evaluator receipt |
| 无作者 accession-to-result 科学复现 | 15 | **15** | silver route 只是候选入口，没有第三方运行、日志、环境 digest 和签名 receipt |
| 外部用户采用 | 0 | **0** | 没有两个非作者用户/机构的真实任务 receipt |
| DOI / archive | 25 | **25** | 仍无可解析的 DOI/archive receipt |

**严格强 Q1 综合成熟度：70/100；编辑决定：Major Revision / Not Ready。**

这个综合分不是所有模块的简单平均，而是保留外部硬门槛后的投稿决策分。论文数据路线使“数据与内部执行”达到 90+，但不可能凭作者重新分析论文数据把四个外部门槛也变成 90+。

## 4. 允许的投稿定位

当前可以继续按以下定位准备稿件：

- auditable computational method；
- public paper-data benchmark；
- source-conditional portability / failure-boundary analysis；
- reproducibility and provenance infrastructure。

当前不能使用以下定位：

- independent biological validation；
- new wet-lab discovery；
- clinical utility；
- universal mechanistic law；
- externally adopted or independently reproduced software。

## 5. 剩余唯一硬门槛

1. 至少 1 个非作者、持有 protected held-out input 的 evaluator，提交身份/COI、input hash 或 protected-data attestation、环境 digest、输出 hash、失败和负结果记录。
2. 至少 1 个无作者参与的团队从固定 release 重新获取 silver 或另一条声明过的公开 route，完成 accession-to-result 复现并提交 signed receipt。
3. 至少 2 个非作者用户或机构在 clean environment 中执行不同真实任务，并提交 adoption receipt。
4. 将当前提交版本绑定到新的 immutable release，获得真实 DOI/archive locator 后，重新运行五角色终审。

在上述证据到达前，scientific_submission_ready 必须保持 false。

