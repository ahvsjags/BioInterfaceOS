# R4 T220 多智能体编辑复审：公开论文数据路线后的当前投稿状态

日期：2026-08-14  
评审版本：`v0.1.3-r10.23`，目标提交 `8658e19aff649d260798c9e0672738ff79e37df5`  
评审框架：统计主编、计算生物学编辑、开放科学/复现审稿人、方法学审计员、devil's advocate 五个角色；按当前可核验证据计分，不把作者运行、agent 评审或 GitHub 招募贴当作第三方证据。

## 1. 编辑结论

**决定：Major Revision / Not Ready for strong-Q1 submission。**

当前最准确的论文定位是：

> paper-derived, source-conditional, auditable protein-corona rank-portability benchmark/software framework

T217 已把主 estimand、target availability、missingness、nested selection 和 multiplicity 的执行协议固定并在 KAUST fresh replay 中通过；T218/T220 又把公开论文数据的真实 OOD 路线、无作者复现入口、immutable release、tarball、manifest 和 checksum 绑定起来。这些工作显著提升了“可审计方法/软件论文”的可信度。

但公开论文全文和 accession 数据不能凭空产生：

- 非作者 protected lockbox evaluator receipt；
- 非作者从 accession 到结果的科学复现 receipt；
- 两个非作者机构的真实任务采用 receipt；
- biological independence、donor/patient-level effective n 和新的生物学验证。

因此，`scientific_submission_ready` 仍必须为 `false`，不能声称所有模块已达到 90 分或已经稳投强 Q1。

## 2. 五角色独立评分

| 角色 | 分数 | 主要判断 |
|---|---:|---|
| 统计主编 | 67 | estimand 和执行审计明显增强，但 biological unit、MNAR 边界和全项目 multiplicity 仍未完全闭合 |
| 计算生物学编辑 | 70 | 有真实公开数据、模型对照和正/负 OOD，但尚不能支持机制发现或普适 superiority |
| 开放科学/复现审稿人 | 66 | r10.23 版本、manifest、checksum、KAUST replay 和具体 PMC6592156 路线完整；第三方 receipt 尚为空 |
| 方法学审计员 | 64 | claim boundary 和 provenance 较强，但跨 laboratory anchor 仍不等于独立 biological cohort |
| Devil's advocate | 52 | 最关键结果仍由作者运行；selection、source composition、technical batch 与 donor 层级可能混淆 |
| **保守共识** | **64** | **方法/软件论文有强 Q1 潜力，但当前仍为 Major Revision / Not Ready** |

## 3. 模块评分

| 模块 | T215 基线 | T220 当前 | 90 分缺口 |
|---|---:|---:|---|
| 数据兼容性、许可与行级 provenance | 86 | **88** | 至少三个真正独立 biological cohort，且 donor/patient/sample 层级可追溯；当前部分来源是 pooled 或 technical replicate |
| 统一 estimand 与统计设计 | 82 | **86** | 把 primary family、source interaction、biological unit 和不可识别边界进一步合并为单一预注册协议 |
| nested selection 与泄漏控制 | 82 | **84** | 需第三方按固定版本复跑并提交输出 hash；当前主要是作者/KAUST replay |
| lineage 与 biological independence | 62 | **62** | 必须补齐 donor/patient-level 独立性；全文数据不能替代缺失的 biological replication |
| effective biological n 与不确定性 | 72 | **78** | 明确 donor-level n、study-level replication n、technical batch n，并用相应 cluster bootstrap/敏感性界限报告 |
| missingness / target availability bias | 74 | **82** | 需要 MNAR、pattern-mixture、IPW 或可识别 bounds 的正式敏感性结果，而不只是 threshold sensitivity |
| multiplicity 与 null calibration | 58 | **78** | 需要覆盖全部 primary/sensitivity/OOD family 的预先冻结 alpha、gatekeeping 和负对照校准 |
| source-conditional heterogeneity | 83 | **85** | formal source-by-model interaction 或明确降级为 descriptive audit |
| 模型、消融、负对照与 OOD | 78 | **84** | 至少一个独立外部 evaluator 或无作者复现 receipt；目前 OOD 仍为作者运行 |
| 统计审计、KAUST replay 与工程复现 | 88 | **94** | 当前已接近闭合；还需把第三方环境 receipt 绑定同一 release |
| claim discipline | 94 | **96** | 保持禁止把 batch、reported n 或 paper OOD 写成 biological replication/effective n |
| immutable public version binding | 42 | **92** | r10.23 已有 tag、GitHub release、manifest、tarball 与 SHA-256；需归档服务返回真实 DOI/archive receipt |
| 非作者 protected lockbox | 10 | **10** | 仍无非作者 evaluator receipt |
| 非作者 accession-to-result reproduction | 5 | **15** | 已有 PMC6592156 具体公开路线，但仍无非作者独立输出、环境 digest、偏差和签名 receipt |
| 外部用户采用 | 0 | **0** | 仍无两个非作者机构的安装、真实任务、日志和输出 hash |
| DOI / archive | 15 | **25** | 已生成投递包；尚无 DOI locator、archive receipt 和 immutable deposit hash |
| **强 Q1 综合成熟度** | **56** | **64** | 外部证据硬门槛、biological n、全局统计闭环仍未关闭 |
| **biological discovery / mechanism** | **29** | **29** | 当前没有机制实验、因果验证或临床终点证据；不应按 discovery paper 投稿 |

## 4. 公开全文数据路线的真实贡献

T218 绑定了一个可实际执行的无作者候选路线：CC-BY-3.0 的 PMC6592156 银纳米颗粒-人血浆公开补充数据。该路线具备文章定位、补充数据 endpoint、许可边界、source audit、目标映射和固定运行命令，历史作者运行结果仅作为 comparison metadata，不作为验收 receipt。

这条路线解决的是“无作者团队可以拿到什么、如何从 accession 复现到结果”的可执行性问题；它没有解决“已经有无作者团队完成复现”的证据问题，也没有把技术批次变成独立 donor/cohort。

## 5. 四个硬门禁

```text
independent_validation = false
protected_lockbox_evaluator_receipt = false
external_scientific_reproduction = false
external_user_adoption = false
doi_archived = false
scientific_submission_ready = false
```

## 6. 达到 90+ 的可验证终止条件

1. 第三方 protected lockbox evaluator 提交一次 aggregate receipt、环境 digest、命令、输出 hash、偏差记录和 COI/身份声明。
2. 非作者团队从 PMC6592156 supplementary endpoint 独立下载、校验、运行并提交 accession-to-result receipt。
3. 两个非作者用户/机构在 clean environment 中完成不同真实任务，并分别提交安装日志、任务日志、输出 hash、失败记录和 COI。
4. 至少三个独立 biological cohort 具备 laboratory → study → donor/patient → sample → batch → observation 层级；否则将结论明确降级为 source-conditional technical audit。
5. 统一 primary family 的 multiplicity、missingness/MNAR bounds、effective-n 和 source-by-model interaction 结果，并由第三方按同一 immutable release 复跑。
6. 归档服务返回真实 DOI、版本绑定和可解析 archive locator。
7. 最后一轮五角色复审中，所有投稿模块均达到 90+ 且无任何硬门禁为 false。

在上述条件完成前，最合适的投稿方向是 computational methods/software、benchmark 或 reproducibility 取向的期刊；不是 biological mechanism、clinical utility 或“sequence model universal superiority”论文。
