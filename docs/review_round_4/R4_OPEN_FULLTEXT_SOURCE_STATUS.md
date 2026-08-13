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

## T176：PMC13106918 授权解析与技术来源审计（2026-08-13）

Zenodo record `16813857` 的公开 API 已核验为 `open`、`CC-BY-4.0`，因此此前的 dataset-level license HOLD 已解除。完整 `MaxQuant_txt.zip`、`proteinGroups.txt`、`summary.txt` 和 `parameters.txt` 均已按 SHA-256 核验，并与压缩包内对应文件逐字节一致。

在冻结 R3 feature table 上采用更保守的规则：去除 `Reverse=+` 与 `Potential contaminant=+`，去除 `CON__`，只保留恰好映射到一个 R3 accession 的 protein group，不合并多 target，不插补缺失。结果为：751 个 protein-group 行、20 个技术测量批次、53 个唯一 target、1,060 个源单元格、451 个正值、16 个达到每批至少 10 个正 target 的批次。该来源来自 RCSI/DCU，一个 pooled material 包含八名供体，五种消化流程各四个技术重复；因此 biological unit 仍为 1，不能写成独立供体验证、独立 evaluator、lockbox 或无作者复现。

可复核产物：

- 注册表：`docs/data/R4_T176_PMC13106918_TECHNICAL_SOURCE_REGISTRY.json`
- 单元格账本与 receipt：`reports/review_round_4/pmc13106918_source_audit/v1.0.0/`
- CLI：

```bash
uv run biointerfaceos data audit-r4-pmc13106918-source --assets-root data/raw/r4_candidate_pmc13106918 --strict
uv run biointerfaceos data verify-r4-pmc13106918-source --assets-root data/raw/r4_candidate_pmc13106918 --strict
```

T176 将数据兼容性和可审计性从候选筛选推进到“授权已解析、源单元格已冻结”的技术候选，但不关闭 independent lockbox、no-author reproduction、external adoption 或 DOI 门槛；`scientific_submission_ready` 继续为 `false`。

## T177：PMC13106918 technical OOD 执行

已在 T176 的冻结 source-cell map 上执行单独的 T177 protocol：不使用原始 LFQ 跨研究尺度，只在每个外部技术批次内部重新计算正值 midrank percentile；模型只在冻结的 R3 development population 上 nested-select alpha 并最终 refit。执行得到 2,724 个 development observations、418 个外部 target observations、16 个符合每批至少 10 个正 target 的 technical batches、3 个模型（constant、full sequence ridge、composition-only ridge）、paired ablation、batch-cluster bootstrap 和 256 次 within-batch permutation negative control。

该执行是实际模型结果，但结果不支持夸大结论：full sequence ridge 的外部批次均值 Spearman 为 `0.0240`（95% bootstrap interval `[-0.0254, 0.0854]`），composition-only 为 `-0.0296`；paired full-minus-composition 差为 `0.0536`（95% interval `[0.0192, 0.0876]`），而开发集内批次置换 negative-control 上尾 `p=0.3268`。因此 T177 证明统计执行、模型、消融和负对照链条已可重跑，但没有产生独立生物学验证或稳健的正向外部科学结论。

可复核产物：

- 协议：`docs/data/R4_T177_PMC13106918_TECHNICAL_OOD_PROTOCOL.json`
- 模型报告、receipt 和全套 CSV：`reports/review_round_4/pmc13106918_technical_ood/v1.0.0/`
- 重跑命令：

```bash
uv run biointerfaceos data evaluate-r4-pmc13106918-technical-ood --strict
uv run biointerfaceos data verify-r4-pmc13106918-technical-ood --strict
```

T177 只能提高“统计执行/模型证据”这一作者运行模块的可审计性；因为 biological unit=1、laboratory anchor=1、model execution 仍为作者运行，独立 lockbox、无作者复现、外部采用和 `scientific_submission_ready` 仍未关闭。

## T178：三独立实验室共同 target admission closure

对 R3 当前主 ledger 重新执行了跨实验室 admission audit，而不是沿用旧报告中的“identified/not yet admitted”文字。三个明确 CC-BY 来源及其行级 source-cell map 均通过 registry、source-audit report、receipt 和 SHA-256 核验：Seer/Broad、Michigan State multi-core、OUHSC。三者的共同 target intersection 为 `99` 个 UniProt accession；共同且 rank-eligible 的 observations 为 `2,724`，覆盖 `47` 个 measurement batches；三份 source-cell map 合计 `20,469` 个源单元格。

这关闭了“是否已经有至少三个独立实验室共同真实 target”的资产审计缺口，但不把 Michigan State 的 12 个 core facility 写成 12 个生物学 cohort，也不把三实验室 development population 写成 protected lockbox 或无作者复现。所有源仍使用 source-local rank estimand，原始量纲不跨研究合并。

可复核产物：

- 注册表：`docs/data/R4_T178_THREE_LAB_COMMON_TARGET_ADMISSION.json`
- 报告与 receipt：`reports/review_round_4/three_lab_common_target/v1.0.0/`
- 命令：

```bash
uv run biointerfaceos data audit-r4-three-lab-common-target --strict
uv run biointerfaceos data verify-r4-three-lab-common-target --strict
```
