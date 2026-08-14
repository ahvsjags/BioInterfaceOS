# R4-T274：固定 target panel 的 coverage / availability sensitivity

T274 对 T273 五个固定 targets 在 minimum positive targets-per-measurement-batch = 3、4、5 下进行预模型 coverage sensitivity。该分析只描述可用性和排除路径，不假设 MCAR、MAR 或 MNAR。

| source | threshold 3: batches / rows / units | threshold 4 | threshold 5 |
|---|---|---|---|
| Seer/Broad | 585 / 2,592 / 141 | 522 / 2,403 / 140 | 315 / 1,575 / 133 |
| Tianjin | 45 / 225 / 45 | 45 / 225 / 45 | 45 / 225 / 45 |
| Manchester | 286 / 1,036 / 60 | 178 / 712 / 37 | 0 / 0 / 0 |

结论：T273 的 threshold=3 规则对 Seer/Broad 与 Manchester 的 retained coverage 有明显影响；Manchester 在 threshold=5 下没有 qualified batch。因此不能把 T273 结果解释为对所有 target-availability 规则都稳定，也不能把 strict common-target route 当作无选择的总体估计。

Canonical descriptive artifact：`reports/review_round_4/t274_coverage_sensitivity/v1.0.0/coverage_sensitivity.csv`；报告：`t274_coverage_sensitivity_report.json`。

该 sensitivity 不关闭非作者 lockbox、无作者复现、外部采用或 DOI 门禁，`scientific_submission_ready=false`。
