# R4 公开全文真实数据扩充：审计状态与边界

状态：`IN_PROGRESS`。本轮只接纳作者提供的、允许再分发的原始补充材料，并把每个数值追溯到源文件、工作表、行、列和原始值。它解决的是“没有可审计真实实验数据”的一部分缺口；它不把公开论文数据伪装成新做实验，也不把作者运行写成独立验证。

## 已冻结的新增来源

| 来源 | 可再分发性与原始资产 | 审计得到的真实量化单元 | 与 R3 的关系 | 可主张 / 不可主张 |
|---|---|---:|---|---|
| Edinburgh DataShare `ds/7545`；关联论文 PMC11106005，DOI `10.1038/s41565-023-01572-3` | 数据集与论文均为 CC-BY-4.0；`blood_proteomics_data.xlsx`、`README.txt` 已以 SHA-256 冻结 | 1,478 蛋白行、49 个样本批次、983 个映射源单元格（932 个正值）、23 个 R3 共有 canonical proteins | 独立的临床前/后暴露人血浆蛋白组来源；量纲、终点和设计不同，不能并入冻结的 R3 corona-rank target | 可以作为单独 R4 临床可迁移性数据候选；不能报告为 R3 外部 OOD、lockbox 或独立复现 |
| PMC11544298，DOI `10.1038/s41467-024-53966-z` | 论文为 CC-BY-4.0；官方补充包及 `MOESM3`、`MOESM5`、`MOESM7` 三份工作簿均以 SHA-256 冻结 | 2,168 直接映射蛋白行、142 个全部测量批次；去除 plasma-alone 后 136 个冠层批次，其中 134 个满足每批至少 10 个可排序共有蛋白；8,064 源单元格（7,075 个正值）；97 个 R3 feature-table canonical proteins | 新的、小分子调控冠层机制数据候选。作者单位包含 Michigan State University，与 R3 的 Michigan State 来源同一实验室谱系 | 可以作为**新的、须预注册的 R4 协议**中的同谱系补充；增加的独立实验室锚点为 0，不能补足 R3 的独立实验室证据，也不得事后并入 R3 训练/模型选择 |

## 固定的数据处理规则

- 仅接受完整、单一的 UniProt accession；分号分组、蛋白组/基因组标识和不能直接映射到冻结 R3 feature table 的行均不合并、不猜测。
- 原始工作簿中的文字 `NA` 被记为 `SOURCE_NA`，从排序中排除；不改为 0，也不插补。
- plasma-alone 对照保留在总账本中，但不进入小分子冠层候选批次。
- 只有在独立的 R4 protocol 先冻结 target、split、选择规则和统计 estimand 后，才允许拟合模型；在此之前 `model_fitted=false`。

## 可复核产物

- Edinburgh 注册表：`docs/data/R4_T156_EDINBURGH_CLINICAL_SOURCE_REGISTRY.json`
- 小分子冠层注册表：`docs/data/R4_T157_SMALL_MOLECULE_CORONA_SOURCE_REGISTRY.json`
- Edinburgh 单元格账本与 receipt：`reports/review_round_4/edinburgh_clinical_source_audit/v1.0.0/`
- 小分子冠层单元格账本与 receipt：`reports/review_round_4/small_molecule_corona_source_audit/v1.0.0/`
- 可重复核命令：

```bash
uv run biointerfaceos data audit-r4-edinburgh-clinical-source --assets-root data/raw/r4_candidate_edinburgh_ds7545 --strict
uv run biointerfaceos data audit-r4-small-molecule-corona-source --assets-root data/raw/r4_candidate_pmc11544298 --strict
```

## 对强 Q1 门槛的影响

这两套数据把“公开全文/补充材料中能否获得行级人血浆真实数据”的答案从猜测变为可复核资产，因而可提升数据基础和数据兼容性；但不能使以下分项达标：独立 lockbox、无作者外部科学复现、公开 DOI、外部安装/使用与引用。故 `scientific_submission_ready` 仍必须为 `false`，R3 的历史结果保持冻结。

下一道不可绕过的门槛是：在这两套来源之外，找到并冻结至少一个**不同于 Michigan State、Seer/Broad、OUHSC 及 Gorshkov 团队谱系**、具备可再分发行级人血浆冠层数据的来源；随后以预先公布的 R4 protocol 进行分析。独立 evaluator 和外部复现仍须由非作者团队完成。
