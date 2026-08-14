# R4 T209：Manchester 论文队列锚定修正与 v1.1 OOD

日期：2026-08-14。

## 触发问题

PMC13212878 正文与 Supplementary Data 1–3 报告的患者数为 prostate 26、bladder 23、head-and-neck 11，总计 60。原始公开矩阵的头颈文件还包含 `HA5`，但该 ID 不在 Supplementary Data 3 的临床患者 ID 列表中；旧 v1.0 source map 因此把未锚定矩阵列计入 61 个 biological units。

这不是可以通过改写摘要解决的数字差异。为避免把未由论文临床表锚定的列当作 biological unit，T209 将 `HA5` 作为明确、可追溯的排除项，并重新生成 source map、source receipt 和 OOD 结果。

## 锚定证据

- 论文正文：`https://pmc.ncbi.nlm.nih.gov/articles/PMC13212878/`
- 官方 supplementary archive：`data/raw/r4_candidate_pmc13212878/supplementary.zip`
- archive SHA-256：`85c8fd52abb30d47fb9b584054b1d7d90c15a4c3af75235b0da0200ca5fb094d`
- Supplementary Data 3 中的头颈 ID：HA1、HA2、HA3、HA4、HA7、HA8、HA9、HA11、HA13、HA14、HA18；`HA5` 不在其中。
- 锚定规则：`docs/data/R4_T210_MANCHESTER_PAPER_COHORT_ANCHOR_REGISTRY.json`

## v1.1 严格执行结果

| 指标 | v1.0（含未锚定 HA5） | v1.1（paper-anchored） |
|---|---:|---:|
| source cells | 193,971 | 193,360 |
| positive source cells | 177,636 | 177,067 |
| biological units | 61 | 60 |
| measurement batches | 289 | 288 |
| positive target cells | 4,169 | 4,150 |
| shared canonical proteins | 25 | 25 |

v1.1 使用冻结 R3 development-only fit、leave-one-measurement-batch-out nested alpha selection、full/composition-only/constant 三模型、60-unit cluster bootstrap、paired ablation和每次置换重新选择 alpha 的 256 次 negative control。

- full ridge patient-equal mean Spearman：`0.2918`，95% CI `[0.2590, 0.3218]`
- composition-only：`0.3514`，95% CI `[0.3134, 0.3892]`
- paired full-minus-composition：`-0.0596`，95% CI `[-0.0786, -0.0409]`
- selection-reexecuted negative-control upper-tail `p=0.0311`
- 结果仍为 `EXTERNAL_PUBLIC_ANALYSIS_ONLY`、`independent_validation=false`、`external_scientific_reproduction=false`、`scientific_submission_ready=false`。

## 结论与边界

1. v1.1 修复了 paper-reported cohort count 与 raw matrix column 的不一致；不能把 60 个 paper-anchored units 写成 61。
2. 排除 HA5 不改变负向 OOD 方向，反而使结论更保守：在这个 Manchester 队列中 full sequence model 没有优于 composition-only。
3. 该修正只提高作者运行分析的输入定义和可追溯性，不产生独立 evaluator、无作者复现、外部采用或 DOI 事实。
4. v1.1 仍未进入不可变 `v0.1.3-r10.16` tag；最终发布必须将 T209 代码、protocol、anchor registry、report 和 manifest 绑定到同一个新 tag。

## 可复核命令

```text
python -m biointerfaceos data audit-r4-manchester-nanoomic-source --assets-root data/raw/r4_candidate_pmc13212878/author_repo --strict
python -m biointerfaceos data verify-r4-manchester-nanoomic-source --assets-root data/raw/r4_candidate_pmc13212878/author_repo --strict
python -m biointerfaceos data evaluate-r4-manchester-nanoomic-ood --strict
python -m biointerfaceos data verify-r4-manchester-nanoomic-ood --strict
pytest -q tests/review_round_4/test_r4_manchester_nanoomic.py
```
