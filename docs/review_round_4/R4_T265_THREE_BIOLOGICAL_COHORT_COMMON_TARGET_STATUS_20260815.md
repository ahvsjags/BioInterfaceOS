# R4-T265：三独立实验室 biological common-target 执行状态

日期：2026-08-15  
状态：`EXECUTED_ANALYSIS_ONLY_CROSS_ENVIRONMENT_REPRODUCED`

## 结论

T265 从论文全文、补充表和既有 source-cell audit 中冻结了三个具有明确 biological-unit 编码的独立实验室来源，并在模型执行前计算严格的 canonical-accession 交集：

`P11021`, `P11166`, `P26038`, `P55072`, `P61981`

本路线得到 5 个共同 target、4,085 条 source-map common rows、3,853 条模型有效观测、246 个 biological units 和 916 个满足至少 3 个共同 target 覆盖要求的 measurement batches。source-held-out、nested selection、within-batch negative control、paired composition ablation 和 biological-unit cluster bootstrap 均已执行并通过 receipt verify。

这解决了此前“只有 pooled/technical source、没有三实验室共同 biological target、没有真实模型执行”的主要证据缺口，但这些数据仍是论文数据的 analysis-only 使用，不能被表述为作者新采集的实验数据，也不能替代非作者 lockbox、无作者复现或外部采用证据。

## 三个 cohort

| 来源 | 实验室锚点 | biological units | common rows | 模型观测 | qualified batches | 许可证/边界 |
|---|---|---:|---:|---:|---:|---|
| PXD017052 / PMC7376165 | Seer / Broad | 141 | 2,820 | 2,592 | 585 | CC-BY-4.0；本路线 analysis-only |
| PMC10257194 | Tianjin University / Tianjin Medical University | 45 | 225 | 225 | 45 | CC-BY-NC-ND-4.0；不再分发原始数据 |
| PMC13212878 | University of Manchester NanoOmics Lab | 60 | 1,040 | 1,036 | 286 | 论文 CC-BY；作者矩阵仓库未声明单独许可证，analysis-only |

Manchester 的重复 timepoint 按 paper-anchored patient ID 聚合为 biological unit；PXD017052 的多粒子条件按 subject 聚合。所有 source-local raw scale 均未跨研究拼接，endpoint 是每个 measurement batch 内的 source-local positive rank percentile。

## 留一实验室结果

| held-out laboratory | full-model biological-unit mean Spearman | 95% cluster-bootstrap CI | full-minus-composition | negative-control p |
|---|---:|---:|---:|---:|
| Seer / Broad | 0.1744 | [0.1305, 0.2217] | 0.0000 | 0.0039 |
| Tianjin | 0.5044 | [0.4156, 0.5844] | 0.0000 | 0.0039 |
| Manchester | -0.5070 | [-0.5942, -0.4150] | 0.0000 | 0.6537 |

Manchester 的反向结果和三组 full-minus-composition 为零必须保留。正文只能声称 source-conditional rank portability is heterogeneous，不能声称 universal superiority、机制验证或临床效用。

## 跨环境复现闭环

- 本地 commit：`bb957bc2`（已同步到 GitHub branch `r3-real-data-execution-20260813`）。
- KAUST 任务目录：`/ibex/user/xup0a/BioInterfaceOS-r4-paper-data-fallback-20260814`。
- 本地与 KAUST 的 T265 `v1.0.0` 目录 11 个输出文件逐文件 SHA-256 完全一致。
- 两端严格 verify：`R4_T265_BIOLOGICAL_COMMON_TARGET_VERIFY_VALID`。
- 本地测试：`1 passed`；KAUST 测试：`1 passed`；相关 `ruff check` 通过。
- 详细 SHA-256 对账见 `R4_T265_CROSS_ENVIRONMENT_REPRODUCIBILITY_RECEIPT_20260815.json`。

## 可复核资产

- Protocol：`docs/data/R4_T265_THREE_LAB_BIOLOGICAL_COMMON_TARGET_PROTOCOL.json`
- Registry：`docs/data/R4_T265_THREE_LAB_BIOLOGICAL_COMMON_TARGET_REGISTRY.json`
- Code：`src/biointerfaceos/r4_t265_biological_common_target.py`
- Report：`reports/review_round_4/t265_biological_common_target/v1.0.0/t265_biological_common_target_report.json`
- Receipt：`reports/review_round_4/t265_biological_common_target/v1.0.0/t265_biological_common_target_receipt.json`
- Biological-unit cluster summary：`reports/review_round_4/t265_biological_common_target/v1.0.0/biological_unit_cluster_summary.json`

执行命令：

```text
python -m biointerfaceos data evaluate-r4-t265-biological-common-target --strict
python -m biointerfaceos data verify-r4-t265-biological-common-target --strict
```

## 编辑评分更新

| 模块 | T264 保守分 | T265 后建议分 | 当前判断 |
|---|---:|---:|---|
| 数据兼容性与样本基础 | 85 | 92 | 三个 biological-unit cohort 的共同 target、row-to-batch crosswalk 和真实模型观测已闭合；两个来源仍为 analysis-only |
| 统计分析设计 | 88 | 94 | 增加 biological-unit cluster estimand、留一实验室、nested selection 和缺失覆盖规则 |
| 统计执行与有效样本 | 86 | 92 | 3,853 条模型观测、246-unit cluster bootstrap 和分 cohort 结果已执行 |
| 模型、消融与 OOD | 84 | 91 | 增加三 cohort OOD 与 Manchester 负结果；仍不能声称 universal superiority |
| 独立 lockbox 评估 | 0 | 0 | 尚无非作者 protected evaluator receipt |
| 外部科学复现 | 0 | 0 | 尚无无作者 accession-to-result receipt |
| 外部用户采用 | 0 | 0 | 尚无两份非作者安装/运行 receipt |
| DOI immutable archive/read-back | 10 | 10 | 尚无正式 DOI deposit/read-back |

因此 `scientific_submission_ready` 必须继续保持 `false`。T265 解决的是 biological common-target 和真实模型执行缺口；lockbox、无作者复现、外部采用与 DOI 仍需真实外部主体返回可验证证据，不能由论文数据替代。
