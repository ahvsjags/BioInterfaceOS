# R4 T217：全文论文数据统计闭环执行记录

日期：2026-08-14
任务：T217
基线：T215/T216 的 T214 语义修正与 fresh replay 之后

## 目的

真实新实验样本当前不可得，因此本轮只使用已获得的公开全文论文、补充表格和其可追溯 source map。T217 不把论文报告单元改写成独立生物样本，也不通过重新命名制造第三方验证。它把现有论文数据重新组织为一套可审计的统计角色层级：一个 primary estimand、明确的 availability/missingness denominator、项目级 multiplicity ledger，以及禁止跨路线 pooling 的 claim boundary。

## 冻结的角色层级

| 路线 | 统计角色 | 是否 primary | 可报告内容 |
|---|---|---:|---|
| T195 | exact nine-target、leave-one-laboratory/source-anchor-out、measurement-batch cluster interval 的 full-minus-composition contrast | 是 | fold-specific effect 与 cluster interval；不汇总成跨来源 pooled effect |
| T197 | 与 T195 同 lineage 的 source-availability sensitivity | 否 | development target 到 held-out available target 的分母流和描述性效果 |
| T198 | 单篇论文队列的 qualification-threshold/missingness sensitivity | 否 | 5/7/10/12/15/20/25/30 阈值、缺失状态、保留批次和 biological-unit 计数 |
| T203 | 作者运行的 paper-data OOD | 否 | shared-target denominator、方向和批次计数；不称作独立外部验证 |
| T209 | 作者运行的 Manchester paper-data OOD | 否 | shared-target denominator、方向和 60 个 paper-anchored patient clusters；不称作独立外部验证 |

primary estimand 在模型拟合和 outer-fold evaluation 之前已经由 T195 冻结为 9 个 accession。T197/T198/T203/T209 不再与 T195 拼接为一个“多研究 pooled n”。

## 执行结果

严格命令：

```text
biointerfaceos data evaluate-r4-t217-statistical-amendment --strict
biointerfaceos data verify-r4-t217-statistical-amendment --strict
```

结果：

```text
R4_T217_STATISTICAL_AMENDMENT_VALID availability_rows=16 missingness_rows=149 multiplicity_rows=8 primary_estimand_frozen=true availability_denominators_audited=true missingness_policy_frozen=true project_multiplicity_ledger_frozen=true scientific_submission_ready=false
R4_T217_STATISTICAL_AMENDMENT_VERIFY_VALID availability_rows=16 missingness_rows=149 multiplicity_rows=8 primary_estimand_frozen=true availability_denominators_audited=true missingness_policy_frozen=true project_multiplicity_ledger_frozen=true scientific_submission_ready=false
```

生成的核心文件：

- `reports/review_round_4/t217_statistical_amendment/v1.0.0/primary_estimand_contract.json`
- `reports/review_round_4/t217_statistical_amendment/v1.0.0/availability_flow.csv`
- `reports/review_round_4/t217_statistical_amendment/v1.0.0/missingness_flow.csv`
- `reports/review_round_4/t217_statistical_amendment/v1.0.0/multiplicity_ledger.csv`
- `reports/review_round_4/t217_statistical_amendment/v1.0.0/execution_evidence.csv`
- `reports/review_round_4/t217_statistical_amendment/v1.0.0/t217_statistical_amendment_report.json`
- `reports/review_round_4/t217_statistical_amendment/v1.0.0/t217_statistical_amendment_receipt.json`

关键审计量：

- T195：3 个 source/laboratory anchors，各自 9/9 个 frozen targets；总计 809 observations、85 measurement batches。
- T197：3 个 outer folds，development target denominator 为 12、12、13，held-out available target 均为 9；保留为同一 T195 lineage 的 sensitivity。
- T198：8 个 qualification thresholds；threshold 10 保留 666/705 batches、141 个 biological units 和 17,026 observations。
- T198 missingness overall：23,970 source-map rows，其中 17,330 `POSITIVE_FINITE`、6,640 `AUTHOR_NA`，未发现当前 `AUTHOR_EXPLICIT_ZERO`；不做 imputation，不声明 MAR/MCAR/MNAR。
- T203：99 个 development canonical proteins 到 97 个 external shared proteins，45 个 reported measurement batches；45 不被当作 biological n。
- T209：99 个 development canonical proteins 到 25 个 external shared proteins，288 batches、4,150 observations、60 个 paper-anchored patient clusters；60 不被当作跨研究 replication n。
- multiplicity：primary family 1 个 endpoint 但不估计 p-value；T197 3 个 negative-control p-values 仅做 Holm QC；4 个 secondary routes 禁止 inferential p-values。

## 当前仍未关闭的硬门槛

T217 只解决统计设计和论文数据分母审计，不能替代新的独立实验或第三方运行。因此 receipt 继续固定：

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

T218 仍要求真实非作者 lockbox evaluator、从 accession 到结果的无作者科学复现，以及外部用户安装/任务/adoption receipts。只有这些真实第三方证据完成后，才允许重新评分并评估 strong-Q1 投稿门槛。
