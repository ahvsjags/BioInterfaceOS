# R4-T273：biological-unit-primary 统计重分析状态

## 执行闭环

T273 保留 T265 的三个 paper-derived source maps 和五个预冻结 target，但修复了统计编辑指出的层级不一致：

- inner alpha selection：5-fold grouped cross-validation，所有 measurement batches belonging to one biological unit remain in one inner fold；
- primary estimand：先在 biological unit 内对 qualified batch metrics 求均值，再对 biological units 等权求均值；
- primary CI：2,000 次 biological-unit bootstrap；
- paired ablation：在 biological-unit 层级同时报告 Spearman、MAE、RMSE 差值；
- negative control：每个 within-batch permutation 都重新执行 grouped alpha selection，并在 biological-unit primary estimand 上计算 null；
- coverage：记录 raw → rank-eligible → common rows → qualified batch/unit → model-eligible 的 flow，并明确这不是 MCAR/MAR/MNAR 模型。

## 结果

| held-out laboratory | biological units | full mean Spearman | 95% CI | full − composition Spearman |
|---|---:|---:|---|---:|
| Seer/Broad | 141 | 0.1744 | [0.1300, 0.2151] | 0.0000 |
| Tianjin | 45 | 0.5044 | [0.4089, 0.5822] | 0.0000 |
| Manchester | 60 | −0.5070 | [−0.5987, −0.4173] | 0.0000 |

Selection-aware null one-sided upper-tail p values are 0.0039, 0.0078 and 0.6848 respectively. The Manchester negative result is retained as heterogeneity evidence; it does not support universal superiority or a mechanistic claim.

MAE/RMSE paired differences are numerically near zero in all folds. Therefore the result does not show sequence-specific incremental predictive value under the tested endpoints; it only shows that the current full and composition models have indistinguishable rank performance in this fixed panel.

## Evidence boundary and score update

T273 improves the author-side statistical execution evidence, not the external evidence gates. Conservative current scores are:

| module | score |
|---|---:|
| data compatibility and sample foundation | 78 |
| statistical analysis design | 91 |
| statistical execution and effective n | 91 |
| models, ablation and OOD | 72 |
| non-author lockbox | 0 |
| no-author reproduction | 0 |
| external adoption | 0 |
| DOI authenticated archive | 10 |

The full T273 output remains analysis-only because the Tianjin source is CC-BY-NC-ND and the Manchester matrix has no asserted repository license. The cross-environment receipt at `R4_T273_CROSS_ENVIRONMENT_REPRODUCIBILITY_RECEIPT_20260815.json` proves author-side byte identity only.

`scientific_submission_ready` remains `false`.
