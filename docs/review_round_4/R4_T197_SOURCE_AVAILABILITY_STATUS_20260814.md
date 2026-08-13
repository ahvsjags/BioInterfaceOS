# T197：外层留出 source-availability 敏感性执行

日期：2026-08-14。T197 是对 T195 严格共同 target 敏感性分析的统计边界修正，不替换 T193/T195 的历史 receipt。

## 执行结果

- 三个 outer folds，逐折 leave-one-laboratory-anchor-out。
- 每一折的 target set 只取另外两个 development sources 的 rank-eligible canonical accession 交集；held-out source 不参与 target membership、alpha selection 或 model selection。
- development-only target 数分别为 12、12、13；held-out source 实际可用 target 为 9、9、9。
- 共输出 2,792 条 fold-specific row-traceable observations、85 个 measurement batches、3 个模型。
- 负对照为 3 个 outer folds × 256 次 within-development-batch permutation，每次置换重新执行 nested alpha selection。

## 结果边界

T197 的 held-out batch Spearman 为 Edinburgh `0.4081`、Dalian `0.8349`、UCD `0.2473`；full-minus-composition 差异分别为 `0`、`0.0048`、`-0.0001`。结果支持 source-local rank portability 的探索性敏感性，不支持 sequence feature 的确认性增量，也不建立 independent biological validation、lockbox、无作者复现或投稿就绪。

机器入口：

- `biointerfaceos data evaluate-r4-t197-source-availability --strict`
- `biointerfaceos data verify-r4-t197-source-availability --strict`
- `reports/review_round_4/t197_source_availability_execution/v1.0.0/`

