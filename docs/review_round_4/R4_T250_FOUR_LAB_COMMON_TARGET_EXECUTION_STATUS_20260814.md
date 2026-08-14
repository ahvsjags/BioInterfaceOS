# R4 T250：四来源论文数据真实模型执行状态

状态：`T250_FOUR_LAB_COMMON_TARGET_EXECUTION_COMPLETED_EXPLORATORY`

T250 使用 T249 在模型执行前冻结的 7 个共同 accession，对四个公开论文/公共数据 source lineages 做 leave-one-laboratory-anchor-out。每个外层折内仅在开发来源上做 measurement-batch nested alpha selection；测试来源不参与 target membership、alpha selection 或 model selection。跨来源 abundance 不合并，只比较 source-local rank percentile。

## 执行闭环

| 项目 | 结果 |
|---|---:|
| 观测 | 783 |
| target | 7 |
| source/laboratory anchors | 4 |
| measurement batches | 115 |
| 模型 | 3 |
| 外层折 | 4 |
| bootstrap | 2,000 个 held-out measurement-batch cluster 重采样/折 |
| negative control | 256 次 within-development-batch permutation/折 |

Full sequence ridge 外层结果：

| held-out source anchor | batches | mean Spearman | 95% bootstrap CI |
|---|---:|---:|---:|
| Dalian University of Technology | 6 | 0.926 | 0.899–0.952 |
| University College Dublin / Conway Institute | 30 | 0.687 | 0.638–0.735 |
| University of Edinburgh-led study | 49 | 0.685 | 0.616–0.744 |
| University of Southern Denmark / Russian Academy of Sciences | 30 | 0.766 | 0.715–0.815 |

negative-control upper-tail p 值依次为 0.023、0.097、0.043、0.066。Dalian 折只有 6 个 measurement batches，结果不应被解释为稳定的 biological generalization；所有来源的 donor-level effective n 仍按公开 map 的实际可辨识程度报告，未把 technical batch 当 biological replicate。

## 证据边界

T250 把“没有真实实验数据”推进为“有真实论文/补充表/公共 accession 的可审计开发执行”，并关闭了内部的 target-freeze、模型拟合、外层来源留出、nested selection、uncertainty、ablation 和 negative-control 缺口。它仍不能关闭非作者 lockbox、无作者复现、外部采用或 DOI authenticated receipt；因此 `scientific_submission_ready=false` 保持不变。

## 复核入口

- protocol：`docs/data/R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_PROTOCOL.json`
- registry：`docs/data/R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_REGISTRY.json`
- audit code：`src/biointerfaceos/r4_t250_four_lab_common_target_execution.py`
- output：`reports/review_round_4/t250_four_lab_common_target_execution/v1.0.0/`
- CLI：`python -m biointerfaceos data verify-r4-t250-four-lab-common-target --strict`
