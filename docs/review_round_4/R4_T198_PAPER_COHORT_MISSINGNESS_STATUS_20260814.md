# T198：论文队列缺失与有效样本敏感性执行

日期：2026-08-14。T198 使用 CC-BY-4.0 论文附属的 PMC7376165 Supplementary Data 5 行级 source-cell map，对 T181 的 141-subject cohort 做预注册阈值敏感性；不修改 T181 primary receipt。

## 执行结果

- 覆盖阈值为 `[5, 7, 10, 12, 15, 20, 25, 30]` 个 mapped positive proteins per subject-particle batch。
- primary `>=10` 复现为 17,026 observations、666 measurement batches、141 biological units。
- 阈值从 5 提高到 30 时，qualified batches 从 705 降至 274，biological units 从 141 降至 110；因此 effective n 与 informative missingness 不再被隐藏在单一 primary 阈值中。
- source map 中保留并报告 6,640 个 `AUTHOR_NA`；没有把 NA 或 explicit zero 当作正值，也没有做插补。
- primary 阈值下 full model 的 subject-equal mean Spearman 为 `0.06845`，selection-aware permutation upper-tail `p=0.26848`；full-minus-composition batch mean difference 为 `0.02681`，95% bootstrap interval `[0.02262, 0.03099]`。

## 结果边界

阈值敏感性提升了缺失机制与有效 n 的可审计性，但由于该 cohort 仍是 author-run、同一 laboratory lineage，不能升级为 independent validation、protected lockbox、无作者复现或投稿就绪证据。

机器入口：

- `biointerfaceos data evaluate-r4-t198-paper-cohort-missingness --strict`
- `biointerfaceos data verify-r4-t198-paper-cohort-missingness --strict`
- `reports/review_round_4/t198_paper_cohort_missingness/v1.0.0/`

