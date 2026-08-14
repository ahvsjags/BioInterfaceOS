# R4-T231：全文与 PRIDE 候选的定量重筛与边界判定

日期：2026-08-14。目的：在无法取得新的内部实验数据时，对公开论文全文、补充数据和 PRIDE 结果文件做进一步的可重获性、样本单位、定量端点和冻结 target 覆盖审计。该任务只允许把真实、可追溯的公开资产放入相应的敏感性/OOD层；不把“论文中报告了样本数”改写成跨实验室共同 target 证据。

## 结论先行

本轮没有找到可以诚实关闭“3 个独立实验室、同一可比 endpoint、每个 source-cell 至少 10 个冻结共同 target”门槛的新来源。相反，本轮把几个容易被误用的候选明确分层：

1. `PXD032162`（Helmholtz Centre for Environmental Research/UFZ）是可重建的独立实验室公开蛋白 corona 结果，具有 8 个 TMT mix、4 个时间点和 16 个 raw-file 级别的设计信息；但全局只有 8 个冻结 target 被正向观测到，每个 mix/channel 的最大交集也是 8，不能进入 primary common-target endpoint。
2. `PXD020584`（Semmelweis University/RCNS/Hungary）是真实的人体样本 EV-corona 研究；全文报告健康受试者和 RA 患者，并明确给出 dC 组 HS `n=12`、RA `n=10`。然而它的研究对象是 extracellular vesicles，不是当前纳米材料 corona 主 endpoint；当前可重获 XLSX 主要是鉴定与搜索指标，没有 source-matched、跨研究可比的连续 corona 定量矩阵。因此只能作为 biological/domain-OOD 候选，不能增加主分析有效 n。
3. `PXD028310` 的小型结果表只有 144 个 accession、4 个冻结 target 交集，且论文路线使用 pooled serum；它不能提供 donor-level independent validation。
4. `PXD050779` 与 `PXD053359` 是 top-down/proteoform identification 资产，未形成当前 protein-level common-target quantitative matrix，保留为非纳入结果。

这轮工作提高了作者侧真实数据与负结果的可审计性，但没有生成非作者 lockbox receipt、无作者科学复现、外部用户采用或 DOI 归档。因此 `scientific_submission_ready` 仍为 `false`。

## A. PXD032162：可重建，但只能作为敏感性/OOD来源

### 可核验来源与资产

- 论文全文：[Nano Today article PDF](https://www.research.unipd.it/retrieve/a1b58045-3b1c-4489-b195-5e92cdae832c/1-s2.0-S1748013224003220-main.pdf)。
- 数据记录：[PRIDE PXD032162](https://www.ebi.ac.uk/pride/archive/projects/PXD032162)。
- 数据集索引：[OmicsDI PXD032162](https://www.omicsdi.org/dataset/pride/PXD032162)。
- 实验设计文件：`data/raw/r4_candidate_screen_round5/PXD032162/ExperimentalDesign.xlsx`，SHA-256 `74e7914b56a754a1771a9c3d82acf3dbe5f5d0cdab5ddb3918cec52b51bdbefd`。
- 校正因子文件：`data/raw/r4_candidate_screen_round5/PXD032162/CorrectionFactorsTMT.xlsx`，SHA-256 `e1008ea85ee6f15311371132cbd6e748f951fca103136182d355bdf716538c86`。
- 作者 QuantSpectra：`data/raw/r4_candidate_pxd032162_ufz/Proteinkorona_Nanoplastik_static_QuanSpectra.txt`，242,655,101 bytes，SHA-1 `acff791876dd37d1d08395852c35b48b363be643`，与 PRIDE API 标识一致。
- 作者 MZID：`data/raw/r4_candidate_pxd032162_ufz/Proteinkorona_Nanoplastik_static.mzid.gz`；解压后 236,353,579 bytes，SHA-1 `414a437b9c75d3047a9eee1c187552b932d99042`，与 PRIDE API checksum 一致。

### 设计与重建结果

论文和设计表支持 PS/PVC nanoplastic 在 human plasma 中的 5 min、1 h、6 h、24 h 时间点；TMT 设计包含 8 个 mix、每个 mix 2 个 raw file，共 16 个 raw-file 级别资产。MZID 解析使用 `PeptideEvidenceRef -> PeptideEvidence -> DBSequence accession` 的显式链路，避免把 peptide reference 错当作 protein accession。

| 审计项 | 结果 |
| --- | ---: |
| QuantSpectra 行数 | 723,192 |
| raw-file 标识数 | 16 |
| MZID DBSequence accession 数 | 300 |
| rank-1 passed SII | 123,905 |
| scan-to-accession 映射数 | 123,792 |
| 全局正向观测 protein accession 数 | 300 |
| 与冻结 R3 99-target ledger 的正向交集 | 8 |
| mix/channel groups | 80 |
| 单个 mix/channel 的最大冻结 target 交集 | 8 |
| 达到预设至少 10-target batch 要求的 groups | 0 |
| 当前 admission | `SENSITIVITY_ONLY_NOT_ADMITTED` |

这不是“没有真实数据”：它是一个真实、可追溯且可重建的独立实验室数据集。但低 target overlap 使它不能支持当前主 endpoint 的跨来源共同 target 模型，也不能把 8 个 TMT mix 当作 8 个独立实验室或 8 个独立 donor。允许的用法是：作为预先声明的 domain-OOD/sensitivity source，报告 coverage failure 和外部设计差异；不允许用它补足 primary effective n 或声称关闭 independent validation。

## B. PXD020584：真实生物学样本，但 endpoint 不同

### 全文样本语义

- 论文全文：[Journal of Extracellular Vesicles article](https://isevjournals.onlinelibrary.wiley.com/doi/10.1002/jev2.12140)。
- 数据记录：[ProteomeXchange PXD020584](https://proteomecentral.proteomexchange.org/cgi/GetDataset?ID=PXD020584)。

全文说明共纳入 20 名 healthy subjects 和 17 名 RA patients；用于 differential centrifugation 的 plasma-coated mEV 分析为 HS `n=12`、RA `n=10`，另有 HS 的 DGUC/SEC 分支各 `n=3`。这确认了该论文存在人体 biological units，但它的对象是 THP1/platelet extracellular vesicles 在 EV-depleted plasma 中的 corona，不是当前纳米材料/particle primary endpoint，故不能把 HS/RA sample label 直接当作当前模型的 material feature 或共同 batch covariate。

### 本地公开资产扫描

本地保存了 PRIDE 公开的 54 个 `.xlsx` 结果资产，总字节数 1,249,755；其中部分下载文件无法作为完整 OOXML workbook 解压，失败文件名和异常被保留在工作区，不以缺失静默替代。可读文件的字段包括 `Entry Name`、protein identification、score、peptide count、sequence coverage 等；`Entry Name` 通过本地 UniProt human mapping 转换为 canonical accession 后，得到以下 bounded screen：

| 审计项 | 结果 |
| --- | ---: |
| 公开 XLSX 资产数 | 54 |
| 可映射 accession 的蛋白 union | 451 |
| 与冻结 R3 target ledger 的 union overlap | 39 |
| 论文明确的 dC biological units | HS 12；RA 10 |
| 是否形成跨研究可比连续定量矩阵 | 否 |
| 是否属于当前纳米材料 primary endpoint | 否 |
| 当前 admission | `DOMAIN_OOD_ONLY_PENDING` |

这里的 39 个 union overlap 不能被误报为 39 个共同 target：它们来自不同 EV 类型、健康/RA、nascent/coated/washed/pellet/fraction 结果表的并集，缺少一个已经冻结的同尺度 source-cell observation matrix。它可以支持后续预注册的 endpoint-transfer/OOD 研究，但不能增加当前 primary model 的 target count、effective n 或 independent-lab common-target score。

## C. PXD028310、PXD050779、PXD053359：小资产负结果

| accession | 局部审计结果 | 判定 |
| --- | --- | --- |
| PXD028310 | 论文：[PMC8467878](https://pmc.ncbi.nlm.nih.gov/articles/PMC8467878/)；`30ppm__Ta_to_T1_.xls` 含 144 个 unique accession，与冻结 target 仅 4 个交集；SHA-256 `bb07a9ac2e766f340e40203276ff2ac5e257641a8c736651a1dd8b8d59743c6f`；研究设计使用 pooled serum，不能建立 donor-level map | `NOT_ADMITTED_POOLED_LOW_COVERAGE` |
| PXD050779 | `Proteoform_identifications_TopPIC.xlsx` 是 top-down proteoform identification 资产，不是当前 protein-level common-target matrix | `NOT_ADMITTED_PROTEOFORM_ONLY` |
| PXD053359 | `05292024_S4_1ul_1.tsv` 为 proteoform identification 结果，未提供当前 endpoint 所需的 row-traceable protein-level quantitative matrix | `NOT_ADMITTED_PROTEOFORM_ONLY` |

## D. 对“用全文论文数据解决真实数据缺口”的最终边界

公开论文和 PRIDE 数据可以解决以下作者侧工作：真实数据下载、全文设计核对、字节/哈希复核、样本单位语义审计、target mapping、模型/OOD 执行，以及对不满足 admission contract 的候选给出可复核的负结果。它不能凭作者单方面重分析生成以下外部证据：

- 非作者控制的 protected lockbox evaluator receipt；
- 无作者参与、从公开输入到结果的独立科学复现 receipt；
- 外部用户在不同环境中的独立安装/使用 artifact；
- DOI 归档后的 immutable read-back receipt。

因此本轮的硬门槛状态为：

```text
paper_fulltext_and_pride_rescreened=true
additional_real_public_assets_reconstructed=true
new_independent_laboratory_primary_admitted=false
paper_data_primary_common_target_closure=false
author_side_real_data_execution_supported=true
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

下一步仍是两条并行路线：将 PXD032162 作为固定的 paper-data OOD/sensitivity artifact 保留；同时完成真正的非作者锁箱、无作者复现、外部采用和 DOI 归档。若要把 PXD026615 纳入 primary，必须从 raw/mzIdentML/peak-list 文件重建 protein-level quantification，并补齐 laboratory-study-donor/sample-batch-observation 链路；不能因其存在 PRIDE accession 而提前计分。
