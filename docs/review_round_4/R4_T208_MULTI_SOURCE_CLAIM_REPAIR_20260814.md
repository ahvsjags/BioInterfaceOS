# R4 T208：多来源 OOD 结果汇总与 claim repair

日期：2026-08-14。本文档只汇总已存在的、作者控制环境中执行的 OOD 结果，不能替代非作者 lockbox、无作者复现、外部采用或 DOI receipt。

## 目的

将公开论文/作者公开矩阵产生的正向、负向和未定结果放入同一结果边界，防止只报告有利队列。所有跨来源比较仍使用冻结的 R3 target ledger 和 sequence feature table；不把不同论文的原始 abundance scale 拼接，不把纵向列或技术重复当作独立生物学样本。

## 已核验结果

| 来源 | 证据角色 | 独立层级 | 外部观测 | 主要结果 | 允许的解释 |
|---|---|---:|---:|---|---|
| PMC13212878 / Manchester | analysis-only OOD | 61 patient clusters / 289 measurement batches | 4,169 | full ridge patient-equal mean Spearman `0.2942`；composition-only `0.3527`；paired full-minus-composition `-0.0586`，95% CI `[-0.0778, -0.0402]`；selection-reexecuted negative-control `p=0.0311` | 新实验室公开矩阵上的探索性 OOD；是对“sequence full 特征普遍增益”的负向证据，不是失败后可删除的结果 |
| PMC10257194 / NaY plasma | analysis-only OOD | 45 biological units / 45 measurement batches | 4,362 | full ridge mean batch Spearman `0.1773`；composition-only `0.1532`；paired增量 `0.0241`，95% CI `[0.0202, 0.0284]` | 单论文来源的作者运行 OOD；支持有限的队列特异性增量，不是独立验证 |
| T192/T195 three-source intersection | development/portability sensitivity | 3 laboratory anchors；pooled、donor-unresolved、technical-replicate caveats | 809 | 9 frozen common accessions，85 measurement batches，leave-one-laboratory-anchor-out 执行 | 可追溯的开发/可迁移性证据；不能称为三独立生物学实验室验证 |

## Claim repair

1. 禁止主张“full sequence model 在所有外部来源中优于 composition-only”。Manchester 结果明确反驳该强主张。
2. 若保留生物学主张，只能写成“在预先定义的若干论文队列中观察到来源依赖的、方向不一致的探索性增量”；需要对来源、测量平台、纵向结构和许可边界分层报告。
3. T185/T186 的 61 个 patient clusters 不能被写成 289 或 4,169 个独立 biological replicates；T203 的 45 个 units 也不能替代非作者验证。
4. PMC13212878 文章为 CC-BY-4.0，但作者矩阵仓库没有明确 repository license，因此 raw matrix、source map 和派生数值继续保持 analysis-only，不进入可再分发 release。
5. 在任何真实外部 receipt 到达前，以下门禁仍为 false：`independent_validation`、`protected_lockbox_evaluator_receipt`、`external_scientific_reproduction`、`external_user_adoption`、`doi_archived`、`scientific_submission_ready`。

## 可复核证据

- Manchester source registry：`docs/data/R4_T185_MANCHESTER_NANOOMIC_SOURCE_REGISTRY.json`
- Manchester OOD protocol：`docs/data/R4_T186_MANCHESTER_NANOOMIC_BIOLOGICAL_OOD_PROTOCOL.json`
- Manchester OOD receipt/report：`reports/review_round_4/manchester_nanoomic_ood/v1.0.0/`
- PMC10257194 registry/protocol/report：`docs/data/R4_T203_PMC10257194_NAY_LUAD_PAPER_SOURCE_REGISTRY.json`、`docs/data/R4_T203_PMC10257194_NAY_LUAD_PAPER_OOD_PROTOCOL.json`、`docs/review_round_4/R4_T203_PMC10257194_PAPER_OOD_STATUS_20260814.md`
- KAUST strict checks：`verify-r4-manchester-nanoomic-source`、`verify-r4-manchester-nanoomic-ood`、`verify-r4-pmc10257194-paper-source`、`verify-r4-pmc10257194-paper-ood`

## 当前决定

该汇总提高结果披露和 claim discipline 的完整性，但不关闭任何真实外部证据门禁；编辑决定继续为 `NOT_READY / MAJOR_REVISION`。

## 固定版本的公开交付增强

为降低外部复现的下载歧义，GitHub release `v0.1.3-r10.16` 已上传与 DOI deposit package 同一份压缩包及 SHA-256 sidecar。压缩包 `92,534,896` bytes，SHA-256 为 `bbd5827d6a66dc047f68f5d2ed2ce43722555fde5db60b50e349f72fc22f40d9`。这只是公开 release asset，不是 DOI archive receipt，也不构成外部复现、采用或独立评估。
