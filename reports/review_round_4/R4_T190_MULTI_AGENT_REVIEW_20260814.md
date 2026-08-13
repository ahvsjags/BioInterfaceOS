# BioInterfaceOS T190 多智能体编辑复审

日期：2026-08-14
评审对象：T190 / PXD064962 UCD CC0 exploratory low-coverage sensitivity
评审性质：作者端实现与证据链复核；不等同于非作者 lockbox 或外部科学复现

## 编辑决定

T190 已把项目从“尚无真实模型执行”推进到“有真实公开来源、冻结模型、cluster-aware 不确定性、paired ablation、selection-aware negative control 和技术重复 QC 的 exploratory sensitivity”。但它没有关闭 primary OOD、非作者 lockbox、无作者科学复现、外部采用和 DOI 这些硬门禁。因此当前仍为 **Major Revision；scientific_submission_ready=false；不建议以强 Q1 完整研究投稿**。

## 当前综合评分

| 模块 | 当前分数 | 编辑解释 |
|---|---:|---|
| 数据兼容性与样本基础 | 88/100 | 新增 UCD/PRIDE PXD064962 CC0 行级表、source-cell map、registry/raw/metadata 哈希和 30 个 labelled biological units；低覆盖仍使其不能成为 primary OOD。 |
| 统计分析设计 | 90/100 | estimand、nested selection、cluster bootstrap、coverage strata、paired ablation、negative-control re-selection 和 claim boundary 已冻结。 |
| 统计执行与有效样本 | 84/100 | 3 个模型在 2,724 development observations 和 259 个 external batch-target observations 上真实执行；技术重复 QC 已报告 195 个双阳性、64 个单阳性、64 个 positive-zero discordance；仍为作者运行且 5 个 GE10 batches。 |
| 模型、消融与 OOD 证据 | 49/100 | GE5 exploratory full Spearman 0.43475 高于 composition-only 0.20230，paired delta 0.23245；但 negative-control p=0.07782，full 模型 MAE/RMSE 不优于 constant baseline，且不是 primary OOD。 |
| 独立评估 / protected lockbox | 4/100 | 尚无非作者 evaluator receipt、受保护输入或一次性签名 aggregate。 |
| 外部科学复现 | 0/100 | 尚无无作者 clean-checkout、环境重建、原始输入起步和端到端输出 hash 的第三方 receipt。 |
| 外部用户采用 | 0/100 | 尚无非作者机构的真实安装、任务、失败记录或 issue/PR 采用证据。 |
| DOI / immutable release | 20/100 | 已有可审计 artifact，但 T190 尚未进入带 DOI 的不可变版本发布。 |
| 强 Q1 综合成熟度 | 29/100 | 作者端方法和执行证据明显增强，但硬门禁仍决定投稿成熟度。 |

## T190 真实结果

- PXD064962 官方项目元数据标识为 CC0；本地保存 proteinGroups.txt、summary.txt、PRIDE metadata，并用 registry、raw、derived map、report 和 receipt 哈希闭环。
- 30 个 labelled patient/timepoint batches，259 个 batch-target observations，15 个 evaluated positive target accessions；25 个 batch 为 5–9 targets，5 个 batch 为 ≥10 targets。
- SEQUENCE_RIDGE_FULL：GE5_ALL subject-equal Spearman 0.4347488684，95% CI [0.3523081492, 0.5051861256]。
- SEQUENCE_RIDGE_COMPOSITION_ONLY：0.2022981196，95% CI [0.1119938579, 0.2774688779]。
- paired full-minus-composition delta：0.2324507488，95% CI [0.1993131289, 0.2662711316]。
- full 模型 MAE 0.3678278、RMSE 0.3996968，均没有优于 constant baseline 的 MAE 0.3550938、RMSE 0.3782953。
- selection-aware negative control：256 次、每次重新选择 alpha，upper-tail p=0.0778210；因此只能支持探索性相对排序信号，不能写成确认性泛化能力。

## 三个 agent 的主要意见

### Singer：数据口径与 provenance

- 技术重复应在原始列内分别排名，再在 batch 内对可用阳性 rank 求均值；实现符合。
- 必须避免声称“所有 multi-accession protein groups 均排除”。当前定量端点的准确说法是“恰好一个冻结 R3 target accession”；含额外非目标 identifier 的组仍可保留，映射到多个冻结 target 的组留在 audit-only。
- registry hash、source-audit receipt、raw table、metadata、source map 和 protocol 现已直接或间接闭环。
- receipt verify 是完整性验证，不等同于独立科学复现。

### Carson：统计执行

- nested alpha selection 只使用冻结 R3 development，PXD064962 只在模型冻结后评分；permutation 中重新选择 alpha，未发现 source abundance 进入特征选择。
- cluster bootstrap 的单位是 labelled patient/timepoint biological units，不是 60 个技术列、259 个 observations 或源细胞。
- GE5_ALL 是 exploratory ≥5 eligibility；GE10_ONLY 只有 5 个 units，不能替代 primary minimum。
- full 模型的 Spearman 相对 composition-only 更高，但误差指标不优于 constant baseline，正文必须同时报告。

### Euclid：编辑决定

- T190 提升作者端执行分，但不改变投稿决定：Major Revision，强 Q1 暂不建议投稿。
- lockbox、无作者复现、外部 adoption 和 DOI 仍是外部事件，不能由作者端 artifact 或多智能体 review 代替。

## 仍未关闭的硬门禁

1. 非作者 evaluator 用一次性 protected input 完成 lockbox，并提交签名 receipt。
2. 无作者团队从固定 checkout 和原始输入执行端到端流程，提交环境、日志、输出 manifest 和 hash。
3. 至少两家非作者机构完成真实安装/任务并留下可核验记录。
4. 将最终 manifest、代码、数据许可边界和 receipt 发布到实际 DOI 档案服务，并冻结版本。
5. 重新进行编辑门禁审查；只有上述事件真实存在后，才可能把对应分数推到 90 以上。

## 允许使用的结论

> 在一个具有 CC0 行级公开表的 UCD/PRIDE 来源上，BioInterfaceOS 完成了预先冻结的 exploratory low-coverage sensitivity：技术重复独立计算 source-local ranks，并在 labelled patient/timepoint batch 内对可用阳性重复求均值；在 30 个 ≥5-target batches 上，full sequence ridge 的排序相关性高于 composition-only，但结果不构成 primary OOD、独立验证、lockbox、无作者复现或 scientific submission readiness。

## 禁止使用的结论

- “T190 完成独立外部验证”；
- “PXD064962 是 primary OOD 成功证据”；
- “259 个独立患者”或“60 个独立样本”；
- “所有 multi-accession protein groups 已排除”；
- “negative-control p=0.07782 支持确认性模型能力”；
- “作者端 verify 等同于无作者科学复现”；
- “当前已达到强 Q1 稳投”。
