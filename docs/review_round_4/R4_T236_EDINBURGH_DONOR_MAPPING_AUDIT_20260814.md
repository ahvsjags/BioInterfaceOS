# R4-T236：Edinburgh 论文全文与 proteomics 样本映射审计

日期：2026-08-14  
状态：`PAPER_UNIT_COUNT_VERIFIED_SAMPLE_CROSSWALK_NOT_PUBLIC`

## 目的

核对 Edinburgh DS7545 是否可以把公开 proteomics workbook 的列级样本进一步恢复为 donor/participant-level cluster，从而改进 effective biological n 和三来源共同 target 的生物学独立性表述。

## 可核验事实

### 论文全文

Nature Nanotechnology 论文 `10.1038/s41565-023-01572-3` 报告：

- 14 名年轻健康志愿者参加重复访视；
- 13 名志愿者完成全部 3 次访视；
- 筛查后为参与者分配 participant code；
- 研究采用 air、s-GO、us-GO 的随机交叉设计。

论文入口：

`https://www.nature.com/articles/s41565-023-01572-3`

### 公开数据包

DS7545 的 `blood_proteomics_data.xlsx` 有三个工作表：

- `sGO 0h v 6h`；
- `usGO 0h vs 6h`；
- `identification`。

proteomics 列头示例为：

```text
20210324_6pm_KostarelosK_OkweloguE_EO4
20210324_6pm_KostarelosK_OkweloguE_EO21
20210324_6pm_KostarelosK_OkweloguE_EO24
```

当前行级 map 的 `measurement_batch_id` 保留这些完整列头，例如：

```text
R4_EDINBURGH_SGO_20210324_6pm_KostarelosK_OkweloguE_EO4
```

但 workbook、README 和当前 source-cell map 均没有公开以下任一项：

- `EO4` 等 token 到 participant code 的明确 crosswalk；
- participant code 到 donor/subject cluster 的可审计表；
- 每个 proteomics batch 的 participant-level visit key；
- 允许用列名推断 participant identity 的数据字典。

## 判定

1. 论文层面可以确认 Edinburgh study 的设计包含 14 名志愿者、重复访视和 participant code，因此不能把 Edinburgh 研究描述为无 biological-unit 设计。
2. 数据包层面只能确认 49 个 source measurement batches 和 23 个 rank-eligible target accession；公开输入不足以把这 49 个 batch 安全压缩为 14 个 participant clusters。
3. `EO4`、`EO21` 等是 source-reported opaque sample tokens。在没有 crosswalk 前，不得把数字部分解释为 donor ID、visit ID 或 biological replicate ID。
4. 因此当前 T192/T193/T195 的 Edinburgh cluster uncertainty 必须继续以 source measurement batch 为可审计 cluster，并将 participant-level effective n 标记为 `UNRESOLVED_FROM_PUBLIC_PROTEOMICS_MAP`。
5. 这不会撤销 Edinburgh 作为独立实验室 anchor，也不会撤销 9 个共同 target；它只限制 biological independence 和 effective-n 的 claim 强度。

## 可允许的论文表述

> Edinburgh source 的原始论文报告 14 名志愿者和重复交叉访视，但公开血液蛋白组表未提供 participant-code 到 proteomics-column 的公开 crosswalk。因此本研究保留 49 个可追溯 measurement batches 作为 source-local clusters，不把其转换为 14 个可验证的 donor-level clusters。

## 不能采用的修复

- 不从 `EO` 编号顺序、文件列顺序或作者姓名字符串推断 participant identity；
- 不用论文中其他临床 source-data 表的 participant 行顺序回填 proteomics 样本；
- 不把 14 名论文志愿者直接写入 T193/T195 的 proteomics effective n；
- 不把论文报告的 biological independence 自动转移到没有 crosswalk 的蛋白组矩阵。

## 对强 Q1 门禁的影响

该任务增加了一个可复核的边界审计和负结果，不能单独关闭 lockbox、无作者复现、外部采用或 DOI 门禁。T192/T193/T195 仍属于 `DEVELOPMENT_OBSERVATION` / `EXPLORATORY_CROSS_SOURCE_RANK_PORTABILITY`，`scientific_submission_ready=false` 保持不变。

## 本地证据

- `data/raw/r4_candidate_edinburgh_ds7545/blood_proteomics_data.xlsx`
- `data/raw/r4_candidate_edinburgh_ds7545/README.txt`
- `data/raw/r4_candidate_edinburgh_ds7545/derived/R4_EDINBURGH_DS7545_source_cell_map.csv`
- `docs/data/R4_T156_EDINBURGH_CLINICAL_SOURCE_REGISTRY.json`
- `docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json`
