# R4 T214：来源/研究级异质性审计执行报告

日期：2026-08-14  
执行状态：`T214_SOURCE_HETEROGENEITY_COMPLETED_EXPLORATORY`  
执行命令：

```bash
python -m biointerfaceos data evaluate-r4-t214-source-heterogeneity --strict
python -m biointerfaceos data verify-r4-t214-source-heterogeneity --strict
```

## 目的和边界

T214 将 T211 要求的 source-by-model interaction/heterogeneity 审计落实为可复现程序。它只读取已经完成的 T195、T197、T198、T203 和 T209 receipt，不重新拟合模型、不改变冻结 target、不新增实验，也不把不同数据 lineage 做 pooled inference。

输入和输出均带 SHA-256。T203 的 CC-BY-NC-ND 论文数据及 Manchester 未明确许可的矩阵/派生结果仍为 analysis-only；T214 的数值输出不得被解释为 raw-data release 或独立验证。

## 执行结果

### 主研究级 effect table

主表保留 5 个不重复的描述性研究/来源单元：

| 来源 | 单元语义 | full − composition | 95% CI | 证据等级 |
|---|---|---:|---|---|
| T195 Dalian anchor | laboratory/source anchor；pooled/unspecified biological material | +0.0048 | [-0.0222, 0.0317] | development exploratory |
| T195 UCD anchor | laboratory/source anchor；technical replicate caveat | 0.0000 | [0.0000, 0.0000] | development exploratory |
| T195 Edinburgh anchor | laboratory/source anchor；donor ID unresolved in current map | 0.0000 | [0.0000, 0.0000] | development exploratory |
| T203 PMC10257194 | paper-attached processed cohort；author-run OOD | +0.0241 | [0.0202, 0.0284] | analysis-only exploratory |
| T209 PMC13212878 | 60 paper-anchored patient clusters；author-run OOD | -0.0596 | [-0.0786, -0.0409] | analysis-only exploratory |

结果计数：2 个正向、2 个近零、1 个负向；effect range `0.0837021`。这直接排除了“full sequence model 普遍优于 composition-only”的表述。

### 敏感性路线

- T197 的 3 个 source-availability fold 被单独保存为 sensitivity；它们与 T195 使用同一三来源 lineage，因此没有重复计入主研究级表；
- T197 的 effect 范围为约 `-0.000105` 到 `+0.004762`；
- T198 八个 coverage thresholds 均保留，full-minus-composition 范围为 `+0.024199` 到 `+0.033323`；这些是 missingness sensitivity，不是 confirmatory p-value family。

### 预先冻结的 pooling policy

T214 明确禁止：

- 把 T195 与 T197 作为六个独立实验室/研究合并；
- 把 T203 与 T209 的不同论文队列压成单一 pooled p 值；
- 把 measurement batches 或 source cells 当作 biological n；
- 用 T203 正向结果掩盖 T209 负向结果；
- 把 descriptive heterogeneity 改写成 independent validation 或 biological mechanism。

## 验收和产物

- `R4_T214_SOURCE_HETEROGENEITY_PROTOCOL.json`：主 estimand、输入 hash、路线分类和禁止 pooled inference 规则；
- `reports/review_round_4/t214_source_heterogeneity/v1.0.0/study_level_effects.csv`：8 条保留的路线/来源 effect rows；
- `.../missingness_threshold_sensitivity.csv`：8 个 T198 threshold rows；
- `.../heterogeneity_summary.json`：主研究级计数、范围和路线摘要；
- `.../t214_source_heterogeneity_report.json` 与 `.../t214_source_heterogeneity_receipt.json`：程序报告和 hash receipt；
- 新增 T214 CLI 和 2 个回归测试；本地测试 `4 passed`，compileall 通过；
- KAUST 上必须用同一 commit 重新执行，且仍保持 `scientific_submission_ready=false`。

## 结论

T214 将跨来源结果从“叙述性冲突”提升为可审计的 source-conditional heterogeneity 证据。它提高了统计执行和 claim discipline，但不能关闭独立 evaluator、无作者复现、外部采用、DOI 或 scientific-submission gate。
