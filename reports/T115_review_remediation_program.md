# T115 — 第二轮审稿整改合同：完成记录

日期：2026-08-12
状态：DONE（规划和治理任务；不代表任何实证 finding 已修复）

## 交付

1. `GOAL.md` 升级为 `1.1.0-revision2`，加入 fixture/软件重放/科学证据隔离、公开发布、统计、独立 lockbox、稿件体裁和最终复审的硬门禁；
2. `TASKS.tsv` 新增 T115–T128，将所有五位评审的 Critical/Major findings 映射为带依赖、验收和失败路径的任务；
3. `docs/review_round_2/REMEDIATION_MATRIX.md` 建立 R2-01 至 R2-09 的问题—任务—证据—fallback 对照；
4. `docs/review_round_2/ACCEPTANCE_GATES.yaml` 建立语义、公开发行、图件、真实数据、统计、独立 lockbox、文献、稿件、外部复现和编辑复审门禁；
5. T116 被设为下一项 READY 任务，其执行计划已冻结在 `docs/execplans/T116_semantic_evidence_separation.md`。

## 校验

`python scripts/validate_execution_pack.py`：129 tasks，0 errors，1 existing readiness warning。
任务图检查：ID 无重复、TSV 字段数正确、所有依赖可解析。

## 诚实状态

R2-01 至 R2-09 当前均为 `OPEN`。本任务只确保它们不能被静默忽略；fixture 结果、确定性软件重放、独立科学复现和 scientific-law evidence 仍然被明确分开。项目维持 `IN_PROGRESS`。

## 下一步

执行 T116，以 schema、migration、manuscript/release guard 和回归测试阻止 fixture-to-empirical 的语义升级。T117、T118、T119 继续保持 BLOCKED，直到其依赖和单独执行计划被激活。
