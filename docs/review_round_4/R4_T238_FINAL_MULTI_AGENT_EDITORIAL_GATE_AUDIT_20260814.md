# R4-T238：终态多智能体编辑门禁审计

日期：2026-08-14  
固定对象：当前工作分支 `r3-real-data-execution-20260813`，HEAD `3d62ad9`，论文数据替代路线 R4-T192/T193/T195，固定 release `v0.1.3-r10.28`。

## 编辑结论

**决定：Major Revision / Not submission-ready**  
**严格综合成熟度：70/100（门禁型综合，不是简单模块平均）**  
**`scientific_submission_ready=false`**

BioInterfaceOS 已经不再是 protocol/software-only：作者侧已有真实公开 proteomics、三来源共同 target、冻结 estimand、study-held-out/nested/cluster-aware execution、真实模型、配对消融、负对照、OOD 和不确定性结果。当前不能进入强 Q1 稳投状态的原因集中在外部证据和工程质量闭环，而不是缺少更多作者侧 paper-data reruns。

## 多智能体 panel

### Agent A：数据来源与可审计性编辑

**评分：94/100**

支持证据：

- T192 注册了 Edinburgh DataShare、Dalian PRIDE 和 UCD PRIDE 三个独立 laboratory anchors；
- 9 个共同 canonical accession 已按来源内 positive finite rank eligibility 冻结；
- source bytes、license、source-cell map、worksheet/row/coordinate 和 hash 已记录；
- T236 进一步核对 Edinburgh 论文的 14 名志愿者/13 人完成三次访视，但拒绝把 opaque `EO` token 推断成 donor ID。

扣分：Dalian 是 pooled/unspecified plasma，Edinburgh proteomics column 到 participant code 的 crosswalk 不公开，UCD replicate columns 是技术重复。因此是“跨来源真实 target”而非“三个 donor-level biological cohorts”。

### Agent B：统计设计编辑

**评分：92/100**

支持证据：

- target universe 和共同 target 在模型拟合前冻结；
- outer leave-one-laboratory-anchor-out；
- inner leave-one-batch-out nested selection；
- measurement-batch cluster bootstrap；
- missingness、effective-n、negative-control 和 paired ablation 规则有协议和 receipt。

扣分：部分来源的 biological-unit 语义只能停留在 batch/source level，最终投稿需把 estimand 和 effective-n 表格按来源拆开。

### Agent C：统计执行编辑

**评分：91/100（作者侧）**

支持证据：T193/T195 已执行 3 个 outer folds、85 个 measurement batches、809 行共同观测、nested selection、2,000 次 cluster bootstrap 和 256 次 within-batch permutation，并保存报告、ledger、receipt 和 hash。

扣分：作者侧执行不能升级成第三方验证；最终稿需把作者运行、外部复现和 lockbox 结果分栏呈现。

### Agent D：模型、消融、负对照与 OOD 编辑

**评分：91/100（作者侧）**

支持证据：T193/T195 运行 constant、full sequence ridge、composition-only ridge；T181、T203、T209 等公开论文队列提供 subject/batch-aware OOD、paired ablation、negative control 和 uncertainty artifacts。

扣分：部分 OOD route 是 analysis-only 或 same-lineage；不得写成 clinical validation、independent validation 或 biological replication。

### Agent E：非作者 lockbox 编辑

**评分：10/100**

已有 T218/T234 handoff protocol、固定 release、输入边界和 receipt template；但目前没有非作者 evaluator、protected held-out input、aggregate signed receipt 或 identity/COI audit。

### Agent F：无作者科学复现编辑

**评分：15/100**

已有固定 tag、独立重新获取公开输入的脚本、环境和 hash 记录规范；但当前没有无作者团队从 clean checkout 开始的真实 receipt。

### Agent G：外部用户采用编辑

**评分：0/100**

仓库公开和 GitHub Actions 运行不等于采用。目前没有两个不同非作者用户/机构、两个真实任务、独立安装日志和输出 hash。

### Agent H：版本归档与 DOI 编辑

**评分：25/100**

已有固定 tag `v0.1.3-r10.28`、release manifest、许可边界和 DOI metadata preparation；但没有真实归档服务返回的 DOI、immutable record locator 和上传后 hash read-back。

### Agent I：工程质量编辑

**评分：35/100**

科学 review-round 4 测试为 53 passed；但 GitHub CI 当前在 Ruff 失败，审计结果为 923 条 lint 错误，隔离安全修复和格式化后仍有 868 条，mypy 仍有约 174 条错误。质量规则没有被放宽，但完整 `make check` 尚未通过。

## 要求—证据—状态矩阵

| 目标要求 | 权威证据 | 当前状态 |
|---|---|---|
| 至少 3 个独立实验室共同真实 target | T192 registry/report/receipt | 已完成，限定为 exploratory cross-source portability |
| 预注册 study-held-out/nested/cluster-aware 统计 | T193/T195 protocol、ledger、receipt | 作者侧已完成 |
| 真实模型/消融/负对照/OOD/不确定性 | T195、T181、T203、T209 receipts | 作者侧已完成 |
| 非作者一次性 lockbox | T218/T234 protocol | 未完成，无真实 receipt |
| 无作者原始输入起步复现 | T218/T234、`scripts/r4_external_reproduction.sh` | 未完成，无外部团队 receipt |
| 公开仓库 | GitHub repository and branch | 已有，但 main/branch release governance 尚未完成 |
| 版本 DOI | release manifest / DOI preparation metadata | 未完成，只有 preparation |
| 独立安装 | T234 commands | 脚本已准备，无非作者安装 receipt |
| 外部用户采用 | T218 adoption intake | 未完成，0/2 |
| 最终多智能体编辑复审 | 本 R4-T238 | 已完成，但结论为 Major Revision |
| `scientific_submission_ready=true` | T218 gate predicate | 未满足，必须保持 false |

## 最短真实闭环

1. 取得一份非作者 lockbox evaluator receipt；
2. 取得一份无作者团队复现 receipt；
3. 取得两份不同非作者用户/机构采用 receipt；
4. 完成真实 DOI archive 和 hash read-back；
5. 在授权后修复 923 Ruff / 约 174 mypy 问题，运行完整 `make check`；
6. 对新的真实 artifact 重新执行本 panel，并且只有所有门禁验证通过后才改变 `scientific_submission_ready`。

## 不得使用的替代证据

Codex/KAUST replay、作者侧 clean-room、GitHub Actions、GitHub stars/issues、空 receipt、模板、公开链接、论文 measurement batches 或 DOI preparation package 均不能替代四个外部硬门禁。

## 权威入口

- `docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json`
- `docs/data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_REGISTRY.json`
- `docs/review_round_4/R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_STATUS_20260814.md`
- `docs/review_round_4/R4_T236_EDINBURGH_DONOR_MAPPING_AUDIT_20260814.md`
- `docs/review_round_4/R4_T237_CI_QUALITY_GATE_AUDIT_20260814.md`
- `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json`
- `docs/external/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.md`
