# R4-T247 多智能体编辑复审：论文全文数据补强后

日期：2026-08-14  
复审对象：`BioInterfaceOS` 当前工作树及 T246 论文全文数据路线  
复审决定：`MAJOR_REVISION`  
`scientific_submission_ready=false`

本轮采用角色分离的编辑复审：主编、统计方法审稿人、蛋白质组/纳米生物界面审稿人、可复现性与软件资源审稿人、反方审稿人，以及综合编辑。各角色只依据已存在的 source maps、固定协议、运行 receipt、CI 与论文全文数据，不把作者运行结果改写成独立验证。

## 本轮新增证据

- `PMC11328176` 的 CC-BY 补充表已从 PMC AWS 取得真实 XLSX 字节，形成 2,217 行归一化 core×accession map。
- 6 个 blinded core、3 个技术重复和 70 个冻结 target overlap 已进入审计；203 个 core-level target observations 完成六折 nested ridge、composition ablation、每折 256 次置换负对照和 2,000 次 core-cluster bootstrap。
- 全序列 ridge 平均 held-out Spearman 为 `0.509683`，core-cluster 95% bootstrap 区间 `[0.391177, 0.612970]`；paired full-minus-composition 平均为 `0.076958`。
- `PMC9047655` 的八供者候选被正确保留为生物学上下文，但因公开 SI 没有 donor×protein 的冻结 target 数值矩阵而排除出模型 ledger。

## 角色评分

| 角色 | 综合分 | 结论 | 主要理由 |
|---|---:|---|---|
| 主编（EIC） | 58 | Major Revision | 方法框架和工程执行已具备资源论文潜力，但 lockbox、无作者复现、外部采用和 DOI 仍是硬门槛 |
| 统计方法审稿人 | 92 | Strong after revision | estimand、target freeze、nested selection、cluster uncertainty、missingness、negative control 和 paper-data execution 已闭合；core cluster 不能替代 donor cluster |
| 蛋白质组/纳米生物界面审稿人 | 84 | Major Revision | technical multicore evidence 很强，三来源 common target 可复核；生物学独立队列与跨实验室 donor-level common target 仍不足 |
| 可复现性/软件资源审稿人 | 76 | Major Revision | CI、clean-checkout 路径、source hashes 和公开 release 较强；缺真实 non-author install/task receipt、DOI read-back 和社区采用 |
| 反方审稿人 | 44 | Reject at present | 任何“independent validation”“external replication”“community adopted”或“generalizable”表述在当前 receipts 下都不可接受 |
| 综合编辑 | 60 | Major Revision | 可作为审计型方法/资源稿继续推进，不能作为已完成强 Q1 实证稿提交 |

## 模块门槛

| 模块 | 本轮分数 | 目标 | 编辑判断 |
|---|---:|---:|---|
| 数据兼容性与样本基础 | 88 | 90 | 许可证、source-cell map、3-source common target 和第二 multicore source 已加强；严格 biological effective n 仍受 pooled/unspecified 与 donor crosswalk 限制 |
| 统计分析设计 | 94 | 90 | 已超过门槛 |
| 统计执行与有效样本 | 92 | 90 | 已超过门槛；报告 core-level 与 biological-unit-level 的不同含义 |
| 模型、消融、负对照与 OOD | 90 | 90 | 论文数据模型执行已扩展；结果仍为 author-run exploratory evidence |
| 独立 lockbox 评估 | 12 | 90 | 未达标：无非作者 protected evaluator receipt |
| 外部科学复现 | 8 | 90 | 未达标：无无作者 accession-to-result receipt |
| 外部用户采用 | 46 | 90 | 未达标：没有两名非作者用户/机构的安装、任务、反馈和输出 hash |
| DOI/不可变归档 | 25 | 90 | 未达标：没有正式 DOI archive/read-back receipt |

## 综合编辑决定

当前工作已经从 protocol-only 明确推进到“可追溯论文数据 + 真实模型执行”的 exploratory resource evidence，但尚未达到强 Q1 稳投的外部证据闭环。T246/T247 不能自行把四个外部模块提升到 90；这些分数必须由真实非作者主体或认证归档服务产生。

### 必须完成的 P0 条件

1. 在一个新的 immutable release 中绑定 T192/T195、T180/T181、T194、T200、T203、T209、T246 execution artifacts 与所有 hash。
2. 由非作者 evaluator 持有 protected held-out/unseen input，返回含身份、COI、环境 digest、命令、输出 hash 和偏差记录的一次性 lockbox receipt。
3. 由无作者参与团队从公开 accession/release 起步完成 accession-to-result scientific reproduction receipt。
4. 获得两个不同非作者用户或机构的独立安装和真实任务记录。
5. 完成 DOI/归档服务的正式 deposit 与 read-back hash receipt。
6. 以以上 receipt 为输入重新运行最终编辑门禁，任何未关闭的独立性表述从论文中删除或降级为 exploratory。

### 禁止的处理

- 不把 `PMC11328176` 的六个 core 写成六个 donor cohort。
- 不把 `PMC9047655` 的八供者叙述当作冻结蛋白 target matrix。
- 不把 author-run、CI、GitHub issue、KAUST replay 或 agent review 当作第三方科学复现。
- 不在缺少外部 receipt 时声称 `scientific_submission_ready=true`。

## 最终判断

`MAJOR_REVISION`。当前最合理的投稿定位是审计型计算生物学方法/资源稿；若目标是强 Q1 稳投，仍需完成 P0 外部证据闭环。
