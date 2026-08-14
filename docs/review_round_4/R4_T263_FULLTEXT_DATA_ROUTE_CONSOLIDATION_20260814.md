# R4-T263：全文论文数据路线整合与真实生物学证据边界

日期：2026-08-14  
状态：`IN_PROGRESS_EXTERNAL_GATES_OPEN`  
承接：T230、T233、T249、T257、T260、T261

## 结论

通过论文全文、官方补充表和 PRIDE/ProteomeXchange 资产，项目已经获得了可复核的真实实验观测，并完成了真实模型、配对消融、负对照、OOD 和 cluster-aware 不确定性执行。当前最有价值的路线是：

> 把 BioInterfaceOS 定位为 paper-derived、source-conditional rank-portability benchmark；将 141-subject 论文队列作为 biological-unit OOD，将多实验室同一 pooled aliquot 作为 technical-center OOD，将 pooled/技术重复和 endpoint 不兼容数据保留为边界或负结果。

这解决了“没有真实数据就无法执行模型”的问题，但没有自动解决以下三项外部硬门槛：非作者 protected lockbox、无作者 accession-to-result reproduction、外部用户采用。论文数据不能替代这些第三方 receipt。

## A. 已经可以进入正文的真实论文数据

| 数据层 | 官方来源与许可 | 可核验单位 | 已完成执行 | 允许的结论 |
|---|---|---:|---|---|
| biological-cohort OOD | Nature Communications `PMC7376165` / PRIDE `PXD017052`，论文补充数据 | 141 个 individual subjects；666 个合格 measurement batches；17,026 个 observation；34 个 shared canonical proteins | constant、full sequence ridge、composition-only ridge、nested alpha、subject-equal cluster bootstrap、paired ablation、256 次 within-development-batch permutation | 真实 subject-level paper-cohort OOD；full Spearman `0.06845`，95% CI `[0.05253, 0.08293]`；paired full-minus-composition `0.02928`，95% CI `[0.02413, 0.03451]`；permutation `p=0.24125`，因此只能作 exploratory portability evidence |
| source-conditional common-target | Edinburgh、PMC6592156/Southern Denmark、Dalian、UCD 四个公开 source anchors | 7 个冻结 common targets；15,971 个 source rows；10,852 个 rank-eligible rows | T238/T249 source-held-out、nested selection、cluster uncertainty、paired ablation、negative control | source-local rank portability；不宣称四个独立 biological cohorts |
| technical-center OOD | 多中心 protein-corona 论文公开资产 | 12 个 core facilities；99 个 target；707 个 observation；同一 pooled aliquot | core-cluster bootstrap、nested selection、paired ablation、permutation | technical-center heterogeneity/robustness；不把 12 个 core 当作 12 个 biological cohorts |

关键 OOD receipt：

- `reports/review_round_4/pxd017052_nsclc_biological_ood/v1.0.0/r4_pxd017052_nsclc_biological_ood_report.json`
- `reports/review_round_4/three_lab_common_target/v1.0.0/`
- `reports/review_round_4/pmc13106918_technical_ood/v1.0.0/`

## B. 生物学单位审计的硬边界

T258 对四个 common-target anchor 的审计显示，source row 数量不能直接转成 biological effective n：

| 来源 | 论文/数据报告的样本语义 | 当前可编码 biological units | 处理决定 |
|---|---|---:|---|
| Edinburgh DS7545 | 论文报告 14 名志愿者，但公开 proteomics workbook 的 `EO*` 标签与临床 participant ID 没有可验证 crosswalk | 0 个可追溯 donor units；14 只能作为论文叙述背景 | 保留 source provenance，不写 donor-level n |
| PMC6592156 / PXD007648 | pooled normal human plasma，技术条件/重复 | 0 | source-local measurement batches；不写 donor n |
| Dalian PXD060795 | pooled/unspecified human plasma | 0 | exploratory source anchor；不写 biological replication |
| UCD PXD064962 | 可编码 neonatal patient/timepoint units，另有 technical replicates | 30 个 biological units | donor/timepoint 与 technical replicate 分开报告 |

因此，正文必须同时报告 `n_source_rows`、`n_measurement_batches`、`n_biological_units` 和 `n_laboratory_anchors`，禁止用 rows、batches 或 technical replicates 代替 biological effective n。

## C. 新一轮全文/公共数据反筛结果

### C1. PXD026615：独立实验室，但不能纳入当前 primary endpoint

University of Salamanca/CSIC 的全文和 PRIDE 资产真实存在，包含 human/rabbit/bovine plasma 的 corona 实验；但官方公开文件主要是 RAW、SEARCH、RESULT、PEAK 和 protocol/checksum 文件，没有可直接复用的 sample-design table 与 protein-level quantitative matrix。完整 mzIdentML 重处理后，human-corona 路线仍不能同时闭合 sample/batch/target 链路和当前最低共同 target 覆盖契约。

处理决定：`NOT_ADMITTED_LOW_CORONA_COVERAGE_AND_ENDPOINT_MIXTURE`。它是已完成的负筛查证据，不增加 primary common-target、effective n 或 independent validation 分数。

### C2. PXD007648：真实 protein-corona 数据，但与既有 Southern Denmark anchor 同源

ProteomeXchange 记录明确描述 60 nm silver nanoparticle 与 human blood plasma 的 protein corona，提交机构为 University of Southern Denmark；它与 `PMC6592156` 路线属于同一实验室/研究谱系，并且研究使用 pooled plasma。它可作为既有 source anchor 的官方 accession 入口和技术重复审计，不是新的独立实验室 biological validation。

### C3. PXD043058：有人体 donor，但 endpoint 是 extracellular vesicle，不是当前 nanoparticle-corona endpoint

King’s College London 的全文报告 healthy、vaccinated 和 COVID-recovered donors，PRIDE 中有公开蛋白质组数据；但其研究对象是 extracellular vesicles，不能在没有预注册 endpoint mapping 的情况下并入当前 nanoparticle protein-corona target。它最多是 domain OOD 候选，不进入 primary model 或 common-target effective n。

### C4. PXD077545、PMC10871276、PMC12305297：不满足独立且可再分发的 primary 证据契约

- `PXD077545` 有真实 human-plasma samples，但仍属于 Michigan State lineage，不能作为新的 independent laboratory。
- `PMC10871276` 的数据入口指向 MassIVE，论文数据许可/公开条件与当前可再分发 primary asset 契约不一致，且未形成已验证 donor-to-batch common-target map。
- `PMC12305297` 的 human plasma 主要是购买的 plasma/方法路线，研究谱系仍与 Michigan State 相关，不能关闭新的 independent human-lab gate。

这些结果全部保留为公开候选筛查/边界证据，不静默纳入模型。

## D. 对审稿分数的严格更新

本 T263 不因“发现更多论文”而机械提高分数。T257 的保守强 Q1 评分继续有效：

| 模块 | T257 保守分 | T263 证据变化 | 是否达到 90 |
|---|---:|---|---:|
| 数据兼容性与样本基础 | 82 | 141-subject OOD 已真实执行；common-target 的 donor crosswalk 仍不完整 | 否 |
| 统计分析设计 | 88 | OOD、nested selection、cluster uncertainty 和 missingness 边界得到真实数据检验 | 否，需独立复核后再计分 |
| 统计执行与有效样本 | 82 | 已有 141 biological units、666 batches、17,026 observations 的真实执行 | 否；仍需独立来源/独立复核 |
| 模型、消融与 OOD | 78 | real biological-cohort OOD、technical-center OOD 和 negative controls 已有 receipt | 否；结果总体 exploratory 且未跨独立实验室复现 |
| Protected lockbox | 0 | handoff 与 preflight 已完成，无 evaluator receipt | 否 |
| 无作者科学复现 | 0 | clean-room 脚本和固定 release 已完成，无非作者 receipt | 否 |
| 外部采用 | 0 | issue/task catalog 已准备，无真实安装/任务 receipt | 否 |
| DOI immutable archive/read-back | 10 | GitHub immutable tag 已存在，正式 DOI/archive read-back 仍缺 | 否 |

结论仍为 `MAJOR_REVISION_EXTERNAL_GATES_UNVERIFIED`，`scientific_submission_ready=false`。内部模型证据已从“没有真实结果”升级为“有真实 paper-derived 结果但 claim 受限”；外部硬门槛没有被纸面数据替代。

## E. 解决路径与退出条件

### 已解决

1. 用公开全文/补充数据建立了真实 source rows、measurement batches 和 biological-unit OOD。
2. 完成了真实模型、配对消融、负对照、OOD、cluster-aware uncertainty 和 failure/coverage accounting。
3. 将 paper-derived cohort、technical center、pooled material、donor/timepoint 和 technical replicate 分层。
4. 将不能纳入的全文/PRIDE 候选固定为带理由的 negative result，避免 cherry-picking。

### 仍必须由外部真实参与者或归档服务完成

1. 非作者 evaluator 在预先冻结协议下持有 protected/unseen input，并返回带身份、COI、effective n、ablation、null、OOD 和失败记录的签名 aggregate receipt。
2. 非作者团队从固定 tag 和公开 accession 独立下载、运行并返回 accession-to-result receipt。
3. 两个不同非作者用户/机构在 clean environment 完成真实任务并提供环境、输入和输出 hash。
4. DOI/immutable archive 服务返回 DOI、版本 locator、manifest hash 和 read-back receipt。
5. 上述四项全部核验后，才运行最终五角色编辑复评；在此之前不得设置 `scientific_submission_ready=true`。

## 机器可核验状态

```text
paper_fulltext_real_data_available=true
paper_derived_biological_cohort_ood=true
paper_derived_technical_center_ood=true
common_target_biological_unit_boundary_audited=true
new_independent_laboratory_primary_admitted=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```
