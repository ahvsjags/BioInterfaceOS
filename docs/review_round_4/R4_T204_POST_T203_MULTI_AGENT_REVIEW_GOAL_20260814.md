# R4 T204：T203 后多智能体编辑复审目标

日期：2026-08-14。

## 目标

在纳入 PMC10257194 论文全文数据的作者运行 OOD 后，重新由统计、计算生物学编辑、可复现性与出版完整性 agent 独立评分。每个 agent 必须同时评估：

- 数据兼容性、许可与行级追溯；
- estimand、nested selection、study-held-out、cluster uncertainty、missingness 与 multiplicity；
- 真实模型、配对消融、OOD、负对照和有效样本；
- protected lockbox、无作者科学复现、外部采用和 DOI 归档；
- claim discipline：不得把作者运行的论文 OOD 当作独立外部验证。

## 必须输出

1. 每个 agent 的模块化分数、证据路径和扣分原因；
2. T203 带来的增量分数与尚未解决的硬门禁；
3. 强 Q1 投稿建议：`READY`、`MAJOR_REVISION` 或 `NOT_READY`；
4. 更新后的 `independent_validation`、`external_scientific_reproduction`、`external_user_adoption`、`doi_archived` 和 `scientific_submission_ready` 状态。

## 固定边界

T203 是 CC-BY-NC-ND 论文补充材料的 analysis-only OOD：45 个 biological units、97 个共同 target、4,362 个正值 source cells。raw 数据、derived map 和数值输出不进入可再分发 release。没有真实非作者 receipts 之前，任何 agent 都不得给出 90+ 的出版级总分或 `scientific_submission_ready=true`。
