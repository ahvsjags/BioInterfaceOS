# BioInterfaceOS T191 多智能体编辑终审

日期：2026-08-14
候选版本：`v0.1.3-r10.3`（公开 Git tag；DOI pending）
结论：**Major Revision；当前不通过 `scientific_submission_ready`，不建议以“强 Q1 实证计算生物学论文”投稿。**

## 1. 终审范围

本轮综合 Singer、Carson、Euclid 三个独立审稿视角，并核对 T178 三实验室开发数据、T188/T190 PXD064962 次级敏感性分析、T189 外部证据 handoff、T191 外部执行 packet、公开候选 release manifest 以及 KAUST 执行记录。

本报告只把已经执行并可通过 hash/receipt 追溯的结果计入证据；外部 lockbox、无作者复现、用户采用和 DOI 没有收到真实凭证，因此保留为未完成，不以作者自运行结果替代。

## 2. 模块评分

| 模块 | 分数 | 编辑判断 |
|---|---:|---|
| 数据兼容性与样本基础 | 82/100 | 已有 PXD017052 与 PXD064962 的可重运行输入，以及 3 个开发期实验室锚点；但尚无可再分发、行级可追溯、至少 3 个独立生物学实验室共同 target 的确认性数据集。T178 的 Michigan State 条目是技术 pooled aliquot，不能单独计作独立生物学验证。 |
| 统计分析设计 | 90/100 | estimand、study-held-out/nested selection、cluster uncertainty、missingness、低覆盖敏感性、paired delta 和 selection-aware negative control 规则基本完整。 |
| 统计执行与有效样本 | 85/100 | T190 已真实执行：30 batches/units、15 targets、25/30 低于 primary coverage、5/30 达到高覆盖；cluster bootstrap、配对消融和负对照均有输出。由于数据是低覆盖 exploratory secondary analysis，不能升级为确认性主结果。 |
| 模型、消融与 OOD 证据 | 49/100 | T190 full ridge Spearman 0.4347，95% cluster bootstrap CI [0.3523, 0.5052]；composition 0.2023；paired delta 0.2325，CI [0.1993, 0.2663]；负对照 selection-aware p=0.0778。full 模型 MAE/RMSE 未优于 constant baseline，且尚无独立 OOD evaluator receipt。 |
| 独立评估 / lockbox | 4/100 | 协议、packet 和接收工具已准备；真实非作者 protected lockbox receipt 为 0。 |
| 外部科学复现 | 0/100 | wrapper 已能在 clean checkout 中执行测试、T190 evaluate 和 verify，但无无作者参与团队从原始输入起步的完成凭证。 |
| 用户采用与可用性 | 0/100 | adoption intake 模板已存在；两份独立外部采用 receipt 均未收到。 |
| DOI / 版本发布 | 35/100 | GitHub 仓库、公开 tag 和 hash manifest 已有；Zenodo/同等 DOI archive receipt 尚未取得，manifest 仍应保持 DOI pending。 |
| 强 Q1 综合成熟度 | 29/100 | 作为可审计 protocol/software candidate 有进展；作为强 Q1 实证计算生物学论文仍未达到投稿门槛。 |

## 3. 已完成且可信的证据

1. T190 PXD064962 已从官方 PRIDE API 发现并固定输入；数据许可为 CC0，raw `proteinGroups.txt`、source map、summary、metadata 均有 SHA-256。分析使用 30 个 batch/unit、技术重复分开排序后在 batch 内汇总，没有把技术重复当作独立样本。
2. T190 已固定 coverage 规则：`GE5_ALL` 作为 exploratory 全量结果，`GE5_LT10` 为低覆盖敏感性，`GE10_ONLY` 仅 5 个单位；nested alpha、cluster bootstrap 和 selection-aware permutation 已执行。
3. 外部 wrapper 已修复为真实展开 `output_root`，并在指定输出根目录重新执行 review tests、T190 evaluate、T190 verify 和 lockfile 检查。KAUST 最近作者烟雾运行通过 37 个测试，输出 hash 已生成。
4. T189 handoff、T191 packet、GitHub issue #2 和 release manifest 已经把外部任务写成可执行请求，而不是把“请求外部参与”冒充成“已完成外部证据”。

## 4. 仍然阻断投稿的硬门禁

- `T166/T167`：一份非作者 lockbox receipt，且必须对应固定 tag、冻结输入、独立输出和一次性评估记录。
- `T172`：两份来自不同外部项目/机构的 adoption receipt，包含独立安装、运行版本、输入起点和结果记录。
- `T186`：一次无作者参与的端到端科学复现，从公开原始输入开始，不得使用作者生成的中间结果。
- DOI：公开归档、版本 DOI、release asset 和 manifest hash 必须相互对齐。
- 数据基础：确认性论文仍需要至少 3 个独立生物学实验室共享冻结 target，并提供合法再分发与逐行 provenance；当前 T178 开发 ledger 不满足这一替代条件。

## 5. 编辑决定与下一轮唯一目标

编辑决定：**Major Revision / Reject-before-submission**。下一轮目标不是继续增加内部评分，而是取得上述不可由作者自证的外部证据，并在证据到位后重新运行同一评分表。只有当每个模块均达到 90/100 以上、所有硬门禁均有真实 receipt、`scientific_submission_ready=true` 且独立编辑复核通过，才可称为“稳投强 Q1”。

当前公开状态应保持：`PUBLIC_CANDIDATE_TAGGED_DOI_PENDING`；不得把 T190 的作者运行结果表述为独立验证或外部复现。
