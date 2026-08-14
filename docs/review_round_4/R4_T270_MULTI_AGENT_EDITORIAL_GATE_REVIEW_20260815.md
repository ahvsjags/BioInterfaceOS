# R4-T270：多智能体编辑门禁复审（2026-08-15）

## 审查对象

本轮面向 `v0.1.3-r10.51`、T250 public redistributable route、T265 biological-unit analysis-only supplement，以及当前外部 handoff / DOI 状态。五个角色独立阅读 protocol、registry、canonical reports、receipts 和代码后给出意见：

| 角色 | 智能体 | 独立判断 |
|---|---|---|
| Editor-in-Chief | Bohr | Major Revision / Resubmit Encouraged；不是 strong-Q1 ready |
| Statistical Editor | Ampere | T250 59/100；T265 67/100；Major Revision |
| Data/Domain Editor | Noether | T250/T265 分别约 70/75；独立性与许可边界仍是瓶颈 |
| Methods/Perspective Editor | Harvey | Major Revision；生物学 novelty、外部证据与 release completeness 不足 |
| Devil's Advocate | Galileo | gate-aware readiness blocked；最关键问题是把 source/lab anchor 误称为 biological cohort 的风险 |

这是基于当前证据的编辑预审，不是外部同行评审，也不产生独立验证 receipt。

## 统一评分（严格门禁口径）

| 模块 | 当前分数 | 评估口径 | 达到 90 的必要条件 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 78 | T250 有 4 个公开 source/lab anchors、7 targets、783 observations、115 batches；T265 有 3 labs、5 targets、246 biological units，但受限且非独立 | 至少 3 个真正独立 biological cohorts，行级 provenance、donor/unit 语义和可再分发许可同时闭合 |
| 统计分析设计 | 84 | estimand、outer held-out、nested selection、cluster uncertainty、missingness 规则已成文，但 target universe 条件化和 unit-level selection 尚未完全统一 | primary estimand 与 target freeze、inner split、null、ablation、CI 全部在同一 biological-unit 层级闭合 |
| 统计执行与有效样本 | 75 | T250/T265 均有真实 paper-derived 执行和 artifacts；T265 的 primary/secondary estimand 与 inner batch split 仍不一致 | biological-unit-grouped selection；主结果、CI、negative control、ablation 和有效 n 使用同一冻结 estimand；补足 end-to-end regression |
| 模型、消融与 OOD | 55 | OOD 异质性被保留，Manchester 为负；paired Spearman delta 为 0 只能说明该 rank metric 未见增量 | 补充 MAE/RMSE paired inference、practical margin、selection-aware null、多 target-universe sensitivity；按 source-conditional 口径报告负结果 |
| 独立评估 / lockbox | 0 | 目前只有 protocol、intake 和作者侧 candidate | 非作者 evaluator 在不接触答案的 lockbox 中完成一次性 receipt，并完成 identity/independence audit |
| 外部科学复现 | 0 | r10.51 fresh-clone run 是作者控制的 KAUST clean-room candidate | 无作者参与团队从原始公开输入开始完成复现，保留命令、环境、hash、差异解释和签署 receipt |
| 外部用户可用性与采用 | 0 | 尚无可核验外部安装、用户、issue/PR、引用或采用记录 | 至少两条来自不同外部用户/团队的独立安装与使用证据，包含版本、环境、任务、结果和身份审计 |
| DOI / 公开 release | 10 | immutable tag、manifest、archive 与 deposit metadata 已准备；尚无 authenticated archive read-back DOI | 完成可信存档上传，获得 DOI、immutable URL、deposit receipt，并使 metadata、manifest、archive、tag 可互相校验 |

严格综合成熟度：**未达到 strong-Q1 投稿门禁**。由于 lockbox、外部复现和外部采用是硬门槛，简单平均分不能掩盖这些 0 分项。

## 必须修订项

### A. 先统一统计 estimand

1. 将 biological-unit generalization 设为主张时，主报告、CI、negative control、paired ablation 和 inner selection 全部改为 biological-unit-grouped；否则把 biological-unit artifact 降级为 secondary，并删除跨 unit 泛化措辞。
2. 明确 T250 是 conditional strict-common-target portability：held-out source 通过 all-source target intersection 间接影响 target universe；不能称 prospective independent validation。
3. 处理 T250 UCD technical replicate 的重复计权；预先决定 fold / collapse / replicate weighting，并重算所有主要指标。
4. 完整报告 raw → positive finite → common target → qualified batch → model-eligible 的 coverage/missingness flow 与 sensitivity analysis。
5. 将 null metric 与 primary estimand 对齐，并明确 fixed-alpha conditional permutation 的限制；报告跨 fold/model multiplicity。
6. 除 Spearman 外增加 MAE/RMSE、paired CI 与 practical margin；当前 full-minus-composition 为 0 不得写成 sequence feature 已被验证或“没有任何信息”。

### B. 关闭外部证据硬门槛

7. 由非作者 evaluator 完成一次性 protected-data lockbox receipt；作者不能预先看到答案或修改输入。
8. 由无作者参与团队从原始公开输入启动 r10.51 helper，单独保存完整命令、环境、输入 hash、输出 hash、差异和签名。
9. 获取两个不同外部团队的真实安装/使用记录，区分“看到 GitHub”与“完成采用”。
10. 完成 DOI authenticated deposit read-back；在 DOI 未返回前保持 `doi_archived=false` 和 `scientific_submission_ready=false`。

## 当前允许的投稿表述

可以表述为：BioInterfaceOS 提供 provenance-grounded、可审计的 biointerface proteomics 分析框架，并在公开 paper-derived/source-mapped route 上完成了 source-conditional portability 的作者侧执行与异质性审计。

不可以表述为：四个独立 biological cohorts 已验证、sequence features 带来普遍增益、机制已被验证、存在独立 lockbox、已有外部科学复现、已有社区采用或已达到 strong-Q1 readiness。

## 编辑结论

当前决定：**Major Revision，暂缓投稿**。下一轮只有在上述外部证据全部取得、统计 estimand 统一并完成 DOI read-back 后，才重新运行五角色终审和 `scientific_submission_ready` 强门禁。

