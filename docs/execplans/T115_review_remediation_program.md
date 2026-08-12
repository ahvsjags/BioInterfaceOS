# T115 — 第二轮审稿整改计划

## 目的

把 2026-08-12 五位独立评审提出的 Critical/Major findings 变成版本化、可验证、不可静默规避的项目合同。T115 不声称修复了实证问题；它只建立后续 T116–T128 的任务、证据类别、门禁和诚实的失败路径。

## 输入

- `review_panel_20260812/BioInterfaceOS_multi_agent_editorial_review_zh.md` 的综合判断；
- T105–T114 的稿件、release、claim audit、clean-room 和 final audit；
- 项目现有不可变历史与 T000–T114 任务链。

## 范围

1. 新建 `docs/review_round_2/REMEDIATION_MATRIX.md`，将每项 Critical/Major finding 映射至后续任务、证据和验收；
2. 新建 `docs/review_round_2/ACCEPTANCE_GATES.yaml`，形成 machine-readable gate registry；
3. 在 `GOAL.md` 中加入第二轮硬约束、阶段与完成定义；
4. 在 `TASKS.tsv` 中增加 T115–T128，在 `PROJECT_STATE.yaml` 中将 T115 设为当前任务；
5. 保留 T000–T114 全部历史记录，不修改历史 receipt 或以新标签覆盖历史含义。

## 明确不在范围内

- 不把 fixture 转化、伪装或重新命名为真实观测；
- 不生成、填充或修改任何声称的 empirical result；
- 不在没有独立 evaluator 的情况下使用 `replicated`、`refuted` 或 law-discovery 状态；
- 不删除负结果、失败或旧审计记录。

## 执行步骤

1. 从评审报告提取所有 Critical/Major issue，并为每一项建立至少一个任务 owner；
2. 对每项任务写明 inputs、outputs、command、acceptance 和 failure policy，避免把“文件存在”误作“证据成立”；
3. 将 P0、P1、P2 按依赖排序：P0 先修语义/发布/图件；P1 需要真实数据、统计和独立 evaluator；P2 只在 P1 evidence pass 后重构论文与发布；
4. 定义二叉路径：真实实证 path 或诚实 software/protocol path，禁止没有证据的中间措辞；
5. 运行 execution-pack 校验、TSV 唯一 ID/依赖校验和 YAML parse；
6. 提交本任务，随后把 T115 标为 DONE，并仅将无依赖的 P0 任务置为 READY。

## 验收标准

- `REMEDIATION_MATRIX.md` 覆盖所有评审 Critical/Major finding，且每项包含 severity、owner task、验证证据和失败后的公开定位；
- `ACCEPTANCE_GATES.yaml` 有至少语义、发布、真实数据、统计、lockbox、图件、稿件、外部复现和最终编辑复审九类 gate；
- T115–T128 的依赖图无环，T128 依赖所有可能影响投稿结论的任务；
- `GOAL.md` 明确禁止 fixture-to-empirical 的语义升级；
- 新的项目状态仍为 `IN_PROGRESS`，不因创建计划而宣布完成。

## 失败处理

若任务或门禁定义无法覆盖某一 finding，立即保持 T115 为 ACTIVE，并新增整改任务；不得把 finding 归为“minor”或在 release 中隐去。
