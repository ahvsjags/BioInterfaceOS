# BioInterfaceOS R4 多智能体编辑复评

**复评状态：`MAJOR_REVISION`**  
**复评日期：2026-08-13**  
**评审角色：统计审稿人、计算生物学副编辑、可复现性与出版完整性审计人**

## 一、编辑结论

新增公开全文与 PRIDE 数据提高了来源可追溯性、许可审计和作者端可运行性，但没有产生真正的非作者 lockbox receipt，也没有产生非作者团队的端到端科学复现。因此，当前证据不能支持“已独立验证”“已完成外部复现”“广泛泛化”或强 Q1 生物学发现主张。

当前最合理的稿件定位是：

> 具有冻结 benchmark、嵌套选择、cluster-aware 不确定性和可审计执行协议的计算方法/软件或 benchmark 论文；Dalian PXD060795 仅作为小样本探索性外部敏感性分析。

当前不建议按以下定位投稿：已完成独立外部验证的通用平台、corona 驱动的生物学机制论文、临床转化或 deployment-ready 系统。

## 二、三位评审的独立评分

| 评审视角 | 综合分 | 当前决定 | 主要理由 |
|---|---:|---|---|
| 统计审稿人（严格证据分） | 28/100 | 探索性方法报告/内部 benchmark | Dalian 只有 6 个 valid corona batches；sequence-ridge 没有稳定优于 composition-only；没有独立 lockbox 或外部复现。 |
| 计算生物学副编辑（方法论文定位） | 72/100 | 可按 Major Revision 继续，方法学 Q1 方向 | 方法新颖性、冻结 99-target benchmark、nested selection 和内部设计较强；外部有效性与独立性不足。 |
| 可复现性与出版完整性审计 | 52/100 | 可作为可审计方法/资源论文继续评估 | KAUST 17/17 tests 与字节校验支持内部可复现性，但不等于第三方复现；采用证据为零。 |

三者不是同一量尺：72 分是“收窄论断后的方法论文可投稿性”，52 分是“出版级复现与采用闭环”，28 分是“所有强 Q1 外部证据门槛同时计入后的严格分”。本项目的强 Q1 决策采用最严格的门槛规则，而不是用方法新颖性抵消独立证据缺失。

## 三、按原始工作模块的当前工作分

| 模块 | 当前分 | 已有证据 | 尚未关闭的缺口 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 58 | R3 冻结 99 targets、2,724 development observations、47 batches、3 lab anchors；Dalian PXD060795 有 27 个直接共享 accession、6 个合格 corona batches、109 个 observations。 | Dalian 未达到 primary OOD 的 12-batch 目标，且 donor-level independence 未报告；R4 大样本新增来源主要与 Michigan State lineage 相同。 |
| 统计分析设计 | 82 | frozen estimand、nested selection、missingness 规则、cluster-aware uncertainty、paired ablation 和 permutation protocol 已设计。 | 设计强不等于确认性证据；需把 batch、target、lineage、institution 的有效独立单位和多重比较规则写入预注册并由第三方执行。 |
| 统计执行与有效样本 | 40 | R3/R4 作者运行结果、Dalian 小样本敏感性结果和 KAUST 17/17 tests 已执行。 | 仍缺独立单位层面的确认性 effective-n 报告；Dalian 仅 6 batches，ρ=0.2323，置换检验 p=0.0929，只能作 exploratory。 |
| 模型、消融与 OOD 证据 | 42 | R4 same-lineage OOD 评估与 full/composition-only/negative control 已执行。 | R4 full ρ≈0.4002 低于 composition-only ρ≈0.4049；Dalian full-minus-composition≈0.0006，不能证明 sequence 或 corona 特异增量。 |
| 独立评估 / lockbox | 4 | lockbox handoff 和 intake 接口已准备。 | 目前没有非作者 evaluator、受保护数据、预注册 primary endpoint、签名 receipt 或不可回溯审计记录。 |
| 外部科学复现 | 0 | 有公开来源、代码、环境和作者端重跑路径。 | 没有无共同作者团队从 accession/代码/环境开始的独立 checkout、日志、输出 hash 和结果报告。 |
| 用户可用性与采用 | 25 | 仓库和测试可运行，许可证与来源清单逐条审计。 | 没有非作者真实用户、独立安装报告、issue/PR、独立引用或外部项目采用记录；下载量本身不计为采用。 |

## 四、必须保留的负结果与证据边界

以下事实不得为了提高投稿评分而删除：

- PXD060795 是小样本 exploratory sensitivity analysis，而不是独立 lockbox 或完整外部复现。
- PMC11544298 是作者运行、same-lineage 的 OOD stress test，不得升级为 independent validation。
- R4 中 sequence-ridge 没有显示稳定、预设且可重复的 composition-only 增量。
- 两个候选来源因数据集许可证为空或缺少样本级 human quantitative target 而暂不纳入；这是正确的数据治理决定，不得将其写成“已验证来源”。
- `scientific_submission_ready` 在第三方 receipt 和独立复现产生前必须保持 `false`。

摘要、结论和标题当前禁止使用：`independently validated`、`externally replicated`、`third-party confirmed`、`robust across cohorts`、`generalizes broadly`、`clinically useful`、`deployment-ready`、`community adopted`、`lockbox-verified`。

## 五、当前可以使用的保守表述

> The released workflow and CC0 workbook are auditable and reproducible under the reported KAUST test environment, with 17/17 tests passing.

> In a small-sample exploratory analysis of PXD060795, the observed Spearman correlation was 0.2323; this result is not used to support broad generalization.

> PMC11544298 was evaluated as an author-run, same-lineage OOD stress test and should not be interpreted as independent external replication.

## 六、编辑决定

**当前决定：Major Revision，不按强 Q1 生物学发现论文投稿。**

如果立刻投稿，只能将稿件收窄为方法/软件、可审计 benchmark 或数据资源型论文，并明确外部结果为 exploratory。若目标是“稳投强 Q1”且保留外部验证/普适性主张，必须先完成下一节中的全部硬门槛；单纯再增加作者运行的公开论文数据不会关闭 lockbox 和独立复现门槛。

