# R4 T202：BioInterfaceOS 当前版本多智能体编辑复评

日期：2026-08-14。审查对象：当前工作树 `b4c71e7`、immutable release `v0.1.3-r10.15`，以及 T197/T198/T200/T201 的最新状态。

## 编辑共识

BioInterfaceOS 已经不再是只有 protocol/software 的概念原型：它具有冻结 target、行级 source maps、study-held-out、nested selection、cluster-aware uncertainty、真实模型、配对消融、负对照、OOD 和统计闭合执行。方法/软件论文具有实质贡献和投稿定位。

但是，出版级独立证据链仍未闭合。三位复评 agent 均确认以下事实仍为 false：

- `independent_validation=false`
- `external_scientific_reproduction=false`
- `external_user_adoption=0`
- `doi_archived=false`
- `scientific_submission_ready=false`

T201 的新论文数据候选审计提高了数据治理可信度，但因 185 个 protein rows、18 个 technical LFQ columns 只有 3 个冻结 target 重叠，且 0 个 measurement 达到每批 10-target 阈值，数据被正确排除；它不增加模型性能或独立验证证据。

## 三方评分

三份评分使用的权重不同，因此不强行平均为一个伪精确数字。它们共同给出两个有用的区间：

| 评价口径 | 得分 | 含义 |
|---|---:|---|
| 出版级独立证据成熟度（统计/复现审稿口径） | 56.1–57.7/100 | lockbox、非作者复现、采用和 DOI 门禁显著拉低总分 |
| 方法/软件论文成熟度（编辑宽口径） | 74.6/100 | 技术内核和内部设计较强，但尚未达到强 Q1 证据标准 |
| 生物学发现论文成熟度 | 约 55–58/100 | 缺乏独立生物学队列、机制和正交实验验证 |

## 分项共识

| 模块 | 当前共识 | 判断 |
|---|---:|---|
| 数据兼容性、许可和行级追溯 | 84–94 | 三来源 common target、CC-BY/CC0 source maps 和 T201 排除审计是强项；不应把 pooled/technical units 写成独立生物 n |
| 统计设计与统计闭合 | 84–90 | T197/T198/T200 后，study-held-out、nested、cluster-aware、missingness、multiplicity 和不确定性链条已明显增强 |
| 模型、消融、负对照和 OOD | 72–78 | 已从方案升级为真实作者运行；仍不等于独立外部确认，且 sequence 增量价值需要外部稳定证据 |
| 独立 lockbox 评估 | 10–30 | 只有 protocol/interface 和 handoff，没有非作者 evaluator receipt |
| 非作者科学复现 | 0–25 | GitHub、KAUST clean checkout 和作者测试不能替代无作者参与的端到端复现 |
| 外部用户采用 | 0–20 | 当前没有两名非作者用户的真实任务、日志、反馈或采用记录 |
| DOI 永久归档 | 68（准备度）但门禁未通过 | deposit 包已准备，Zenodo 正式 DOI receipt 尚未产生 |

## 当前编辑决策

- **方法/软件论文：** 可按计算生物学、bioinformatics、proteomics software/resource 方向准备投稿；应明确定位为“可审计、可复现、作者运行的多来源方法框架”。
- **Protocol/benchmark 论文：** 可作为方法学预注册或 Q1 边界方向；应将外部结果明确标为 exploratory。
- **生物学发现/临床转化论文：** 当前不建议投稿；证据不足以支持机制、临床效用或广泛泛化。
- **强 Q1 稳投：** 尚未达到。技术质量接近门槛，但出版级证据总分仍被外部硬门禁限制。

## 必须由真实外部主体关闭的硬门槛

1. 一次性 protected lockbox evaluator receipt：非作者持有输入，预先冻结 endpoint、容差、聚类和失败规则，作者不能读取中间结果，并提交带 hash、时间戳、环境和失败记录的 receipt。
2. 至少一个无作者参与的端到端科学复现：从固定 checkout 和原始公开输入开始，由独立团队报告环境、命令、输出、偏差和失败记录。
3. 两个非作者外部采用记录：不同机构或独立项目完成干净安装和真实任务，提交可核验日志、输出 hash、限制和反馈。
4. Zenodo 等正式 DOI receipt：公开、不可变、可解析，并与最终 immutable release、版本和归档 hash 绑定。
5. 最终稿件 claim audit：删除所有未经上述 receipts 支持的 `independent validation`、`external replication`、`community adopted`、`generalizable`、`clinical utility` 和 `lockbox verified` 表述。

## 结论

本轮共识是 `MAJOR_REVISION`，而不是 `scientific_submission_ready`。T197/T198/T200 应上调数据、统计执行和方法成熟度；T201 应上调数据排除纪律和 claim discipline；但任何作者运行、论文数据 OOD、GitHub release、KAUST clean checkout 或 DOI deposit package 都不得上调独立评估、外部科学复现或用户采用分数。
