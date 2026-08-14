# T238：四源 fold-local target membership 执行状态

日期：2026-08-14。T238 是对 T250 四源 paper-data 执行的统计敏感性补强，不替换 T250 的 immutable receipt，也不把作者运行升级为外部验证。

## 输入与边界

- 四个来源均来自公开论文全文、补充表或公开 accession 的已审计 source map：Edinburgh、Dalian、UCD 和 PMC6592156。
- 每个 outer fold 的 target set 只取其余三个 development source 的 rank-eligible canonical accession 交集；held-out source 不参与 target membership、alpha selection 或 model selection。
- 四源数据的 pooled plasma、条件批次和 technical replicate 语义保留；measurement batch 是不确定性 cluster，donor-level effective n 仍 unresolved。
- 主模型为 sequence-feature ridge，composition-only 为成分消融，constant mean 仅作为不定义 Spearman 的基线；source-local rank 不进行跨源 abundance-scale pooling。
- 64 次 permutation 仅作为有限 Monte Carlo QC null，并非确认性 p-value；paired ablation 与 batch bootstrap 使用 2,000 次重采样。

## 已闭合结果

正式输出目录：`reports/review_round_4/t238_four_source_availability_execution/v1.0.0/`。

| 项目 | 结果 |
|---|---:|
| fold ledger rows (development + held-out, repeated by outer fold) | 3,844 |
| development observations in fold ledgers | 3,061 |
| held-out test observations without development duplication | 783 |
| outer held-out source folds | 4 |
| development-only target counts | 9 / 9 / 10 / 10 |
| held-out available target count | 每折 7 |
| measurement-batch clusters | 115 |
| models | 3 |
| nested alpha selection | 是 |
| negative-control alpha re-execution | 是，每次 permutation |
| independent validation | false |
| external scientific reproduction | false |
| external user adoption | false |
| scientific submission ready | false |

sequence ridge 的 held-out batch Spearman 为 Edinburgh `0.6845`、PMC6592156 `0.7662`、Dalian `0.9262`、UCD `0.6865`。full-minus-composition 的 paired delta 只有 Edinburgh 为正（`+0.1201`，95% batch-bootstrap CI `0.1006–0.1439`），其余三折为 `0`；因此 T238 不支持“sequence feature 在所有来源上具有普遍增量”的表述。

## 审稿解释

T238 解决的是 target membership 在 outer split 后的条件泄漏疑问，并把四源 route 的有效样本边界、低覆盖 Dalian fold 和 selection-aware null 公开化。它提高的是内部统计设计与 paper-data compatibility 的可审计性，不产生新的生物学实验，不产生 donor-independent cohort，不产生 non-author lockbox、no-author reproduction、外部安装/采用或 DOI archive read-back。

因此，本文在真实第三方 receipts 到齐前仍只能按 exploratory computational/paper-data analysis 投稿，不能标记 `scientific_submission_ready=true`。

机器入口：

- `python -m biointerfaceos data evaluate-r4-t238-four-source-availability --strict`
- `python -m biointerfaceos data verify-r4-t238-four-source-availability --strict`
