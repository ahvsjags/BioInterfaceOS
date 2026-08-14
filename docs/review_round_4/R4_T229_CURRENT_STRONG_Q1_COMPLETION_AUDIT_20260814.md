# R4-T229：当前强 Q1 目标逐项完成审计

日期：2026-08-14。审计对象：不可变 `v0.1.3-r10.28`、KAUST clean replay、当前 GitHub/receipt 状态。

## 判定规则

本审计区分作者运行、公开工程证据和真正的非作者证据。任何 receipt、下载、GitHub issue、Codex/KAUST replay 或论文数据再分析，都不会自动满足非作者门禁。

| 目标模块 | 当前判定 | 当前证据 | 当前分数/门禁 | 仍需什么 |
|---|---|---|---:|---|
| 可再分发共同 target 与来源兼容性 | 部分完成 | T222 四路线、三实验室 99-target ledger、source registries/maps、许可边界 | 94/100 | 对“独立实验室/生物学独立性”的最终 claim 仍需保守限定 |
| 预注册统计设计 | 已完成 | estimand、nested selection、study-held-out、cluster uncertainty、missingness/T217 protocol | 90+/100 | 最终编辑复核 |
| 统计执行与 effective n | 已完成（作者运行） | T195/T197/T198/T200/T217 receipts；KAUST replay | 90+/100 | 最终 release 与外部 receipt 绑定后的复核 |
| 模型、配对消融、负对照、OOD、不确定性 | 已完成（探索性作者运行） | 三模型、paired ablation、permutation negative control、PMC6592156 fresh OOD replay | 90+/100 | 不得把作者运行升级为独立验证 |
| 非作者 lockbox evaluator | 缺失 | receipt template 与 preflight schema 已存在；没有真实 evaluator receipt | 10/100 | 1 个非作者、protected held-out input、signed aggregate receipt、archive locator |
| 无作者原始输入复现 | 工程路径完成，科学证据缺失 | r10.28 clean clone：49 passed/13 explicit skipped；fresh source audit/OOD 成功 | 15/100 | 真实无作者团队重新获取输入并提交签名 receipt |
| 外部用户采用 | 缺失 | adoption intake、Issue draft、安装脚本已准备；Issue #2 仍为旧文本且无外部响应 | 0/100 | 2 个非作者用户/机构、不同真实任务、环境与输出 hash |
| 版本 DOI/archive | 归档准备完成，receipt 缺失 | GitHub release、tarball/manifest hash、R10_28 DOI metadata | 25/100 | 真实归档服务返回 DOI、immutable record、上传后 hash read-back |
| 强 Q1 综合成熟度 | 未通过 | R4-T223 strict composite 70/100；外部四门禁仍 false | 70/100 | 所有外部门禁真实验证后重新多智能体编辑复审 |

## 当前强门禁

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

## 已验证的 r10.28 工程状态

- immutable tag target：`5f72487023f80dd37d6b550b97638fb0246eb3fa`。
- source/provenance commit：`b676433d85837e78c5502c0e75012ae2275c4992`。
- clean public tag replay：`49 passed, 13 skipped`，无失败。
- fresh source audit：30 batches、13,485 source cells、9,357 positive source cells。
- fresh external OOD：2,724 development observations、953 external observations、50 shared proteins、30 batches、3 models。
- GitHub release tarball API digest：`sha256:f83388c9f7ec67e55aa941871867e20b3f69ed81e5f7a9cbee04accf7885e5a0`。

## 结论

BioInterfaceOS 已从 protocol/software-only 推进到可审计的公开论文数据研究候选，并且固定版本的 clean replay 与外部复现工程入口已通过验证；但目标“稳投强 Q1”尚未完成。唯一能关闭剩余四个外部门禁的证据是由真实非作者主体和归档服务产生的可审计 artifact，不能由作者继续运行或论文数据 fallback 替代。
