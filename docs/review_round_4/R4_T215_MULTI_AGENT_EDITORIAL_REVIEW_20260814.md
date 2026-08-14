# R4 T215：T214 语义修正、KAUST fresh replay 与下一轮强 Q1 改进目标

日期：2026-08-14  
评审基线：`b80e47352ca775b7aa0b67825bc5ae488160c773`  
评审角色：统计学主编、计算生物学编辑、开放科学/复现性审稿人、devil's advocate  
评审原则：只按当前可核验事实评分；作者运行、agent 评审和 GitHub 发布不替代第三方科学证据。

## 1. 综合编辑决定

**Major Revision — NOT READY。**

四个角色在 T215 新证据上的判断为：

| 角色 | 强 Q1 综合成熟度 | 核心判断 |
|---|---:|---|
| 统计学主编 | 58 | 统计语义和审计边界改善，但 estimand、effective n、multiplicity 和独立性仍不足 |
| 计算生物学编辑 | 58 | methods/software 有潜力；biological discovery 约 29，不成立 |
| 开放科学/复现性 | 56 | fresh replay 成立，但仍是作者控制环境；外部硬门禁未关闭 |
| Devil's advocate | 50 | 语义修正不是新生物学证据；仍有选择偏倚、伪精度和版本绑定风险 |
| **保守共识** | **56** | **强 Q1 不建议现在投稿** |

更准确的当前定位是：

> paper-data-grounded, source-conditional, auditable protein-corona rank-portability benchmark/software framework

不是独立生物学验证、机制发现或“sequence features 普遍优于 composition-only”的实证论文。

## 2. T215 已经真实完成的工作

### 2.1 T214 v1.1 语义修正

- 将 5 条主记录明确命名为 `primary effect units`，不再报告为 5 项独立研究；
- T197 保留为 T195 同一 lineage 的 source-availability sensitivity，不重复计入 primary evidence；
- T203 的 45 个数量保留为 `reported_paper_unit_count`，并标记为 `paper_reported_measurement_batch_count_not_biological_n`；
- 对 T195/T197 未解析的 biological unit 显式标记为 unresolved；
- T198 八个 threshold 被明确标记为 T200 subject-equal primary estimand 之外的 secondary batch-level missingness sensitivity；
- 保留 T203 正向和 Manchester T209 负向结果，禁止 pooled p-value、random-effects meta-inference 和 universal superiority claim。

### 2.2 KAUST fresh replay

T215 在 `/ibex/user/xup0a/BioInterfaceOS-r3-real-data-execution-20260814-clean` 的新 `v1.1.0` 输出目录中执行：

```text
PRE_EXEC_OUTPUT_ABSENT=true
HEAD=b80e47352ca775b7aa0b67825bc5ae488160c773
evaluate → verify → pytest (3 passed) → compileall
FRESH_REPLAY_COMPLETE=true
effect_rows=8; effect_units=5; positive=2; negative=1
```

五个输出文件的 SHA-256 已记录在 [T215 fresh replay receipt](R4_T215_KAUST_FRESH_REPLAY_RECEIPT_20260814.json) 中。该 receipt 的证据等级是：

```text
AUTHOR_RUN_ENGINEERING_REPLAY_OF_PAPER_DERIVED_ANALYSIS
```

它证明当前代码路径可以从不存在的输出目录重新生成 T214 审计结果；不证明原始论文数据的无作者重建、不证明独立科学复现，也不产生新的 biological effective n。

## 3. 模块评分

| 模块 | T215 分数 | 90 分缺口 |
|---|---:|---|
| 数据兼容性、许可证与行级 provenance | 86 | T203 为 analysis-only；Manchester 许可边界和可再分发边界仍需外部可核验确认 |
| 统一 estimand 与统计设计 | 82 | T195/T197/T198/T203/T209 的独立单位、聚合和 null policy 仍不可交换 |
| nested selection 与泄漏控制 | 82 | 不同路线的 alpha/selection policy 尚未收敛为一个预注册 primary family |
| lineage 与 biological independence | 62 | 三个 laboratory/source anchors 不是三个独立 biological cohorts |
| effective biological n 与不确定性 | 72 | 已停止错误推断，但 unresolved donor、pooled material 和 technical replicate 仍使跨来源 effective n 不可识别 |
| missingness / target availability bias | 74 | threshold sensitivity 不是 MNAR、IPW、pattern-mixture 或 bounds 校正 |
| multiplicity 与 null calibration | 58 | T200 的局部 bookkeeping 尚未覆盖全项目 primary/sensitivity family |
| source-conditional heterogeneity | 83 | 描述性范围已完整；仍无统一 estimand 下的 formal interaction/hierarchical parameter |
| 模型、消融、负对照与 OOD | 78 | T203 正向、T209 负向均为作者运行的 paper-data OOD，方向异质且非独立验证 |
| 统计审计与作者环境 replay | 88 | fresh replay 已通过，但需要进入新的 immutable release，并清理残余 study-level 命名和伪精度展示 |
| claim discipline | 94 | 当前边界较强；仍需全文持续禁止把 effect unit、batch count 或 paper OOD 写成独立验证 |
| 公共版本绑定 | 42 | r10.18 不含 T214/T215；需要新的不可变版本 |
| 非作者 protected lockbox | 10 | 没有非作者 evaluator receipt |
| 无作者科学复现 | 5 | 没有从原始 accession 到结果的无作者团队 receipt |
| 外部用户采用 | 0 | 没有非作者安装、真实任务和 adoption receipt |
| DOI / archive | 15 | 没有真实 DOI locator 和 archive receipt |
| **强 Q1 综合成熟度** | **56** | 外部硬门禁、有效样本量和正式统计统一性仍未关闭 |
| **biological discovery / mechanism** | **29** | 没有机制、因果、正交实验或临床终点证据 |

## 4. 必须继续保持为 false 的硬门禁

```text
independent_validation = false
protected_lockbox_evaluator_receipt = false
external_scientific_reproduction = false
external_user_adoption = false
doi_archived = false
scientific_submission_ready = false
```

KAUST fresh replay、作者自测、内部 prelock、agent 评分和 GitHub Issue 招募均不能替代这些门禁。

## 5. R5 强 Q1 改进目标

### 总目标

建立 `R5_STRONG_Q1_SUBMISSION_READY` 证据链：在论文全文/补充材料可公开取得而真实新实验暂时不可得的前提下，完成“来源条件化、可审计方法软件论文”的全部本地统计闭环；同时把必须由第三方产生的证据明确交付，不伪造、不用作者运行替代。

只有以下条件全部满足，才允许将综合模块报告为 `>=90` 并把 `scientific_submission_ready` 改为 `true`：

1. 统一且带时间戳/hash 的 primary estimand、selection、missingness 和 multiplicity protocol；
2. 至少三个真正独立研究/实验室队列具有明确的 `laboratory → study → donor/patient → sample → batch → observation` 层级；若只能使用论文派生数据，必须把不能证明 biological independence 的路线永久降级为 descriptive；
3. 正确的 biological-unit、patient/donor、batch、study/laboratory 分层 n 和 uncertainty，明确区分 `reported n`、`effective n` 与 `study-level replication n`；
4. 统一 primary estimand 下的 formal source-by-model interaction，或明确放弃 formal inference 并将论文定位为 descriptive audit；
5. 全部候选 target、排除原因和 availability flow，配套 IPW、pattern-mixture、MNAR bounds 或等价敏感性分析；
6. 非作者 protected lockbox evaluator 的一次性 aggregate receipt；
7. 至少一个无作者参与的原始 accession 到结果科学复现 receipt；
8. 至少两个非作者用户/机构的真实安装、任务、日志、输出 hash、失败记录和身份/COI 记录；
9. 同一 immutable release、tarball、manifest、checksum 和正式 DOI/archive receipt；
10. 最后一轮多智能体编辑复审中每个投稿模块均达到 90 以上，且没有任何 claim-boundary 回退。

## 6. 下一轮优先级

### P0：本地可完成

- 修正残余 `study_level_effects.csv` 等命名，改为 `effect_unit_descriptive_audit.csv`；
- 增加有限位数的 presentation fields，保留 raw audit fields；对 `[0,0]` 明确写成 degenerate computational interval，不解释为零 biological uncertainty；
- 统一 primary estimand、nested selection、null policy 和 multiplicity family；
- 完成 target-availability denominator、排除流图、pattern-mixture/MNAR bounds 或诚实的不可识别性界限；
- 重新从空目录执行完整链路，并将 receipt 绑定到新 immutable release。

### P0：必须由第三方完成

- 非作者 protected lockbox evaluator；
- 无作者端到端科学复现；
- 两个非作者用户/机构采用；
- DOI 服务返回可解析 locator、版本 DOI 和 archive hash。

### P1：投稿前整合

- 全文标题、摘要、图注和结论只使用 `paper-derived processed-data reanalysis`、`source-conditional portability` 和 `failure-boundary` 叙事；
- 明确声明论文数据不能替代 raw acquisition、QC、完整 missingness mechanism、正交实验或因果验证；
- 把 T203 正向与 T209 负向放在同一主结果框架中；
- 删除任何暗示“五项独立研究”“effective n=批次数”“KAUST=独立复现”的表述。

## 7. 投稿判断

当前：

```text
methods/software：有强 Q1 潜力，但 Major Revision / Not Ready
biological discovery：Reject / 不建议投稿
```

在真实第三方 receipt 到位前，最诚实的投稿方向是 computational methods/software、reproducibility 或 benchmark 取向；不能以 biological mechanism、clinical utility 或 universally superior sequence model 为主张投稿。
