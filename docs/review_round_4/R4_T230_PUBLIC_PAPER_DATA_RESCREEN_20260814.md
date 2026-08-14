# R4-T230：公开论文数据补充筛查与独立性判定

日期：2026-08-14。目的：在缺少内部实验数据的条件下，使用可公开重获的全文、补充表和 ProteomeXchange/PRIDE 资产，寻找能进入 BioInterfaceOS 冻结 target 体系的真实数据；同时对“新实验室”“独立样本”和“有效生物学 n”作语义审计。

## 结论先行

本轮没有发现可以诚实关闭“3 个独立实验室生物学共同 target”门槛的新来源，但已经把可用的公开论文数据路径分层：

1. `PXD054751`（Sapienza University of Rome）是独立于当前 Edinburgh/Dalian/UCD 开发锚点的 CC0 公开来源，且全文、PRIDE 记录和作者结果表可追溯；但其结果表只有 3 个冻结 target 的交集，任何一个 source condition 都达不到预设的至少 10 个共同 target，因此不能进入当前 primary endpoint 或模型执行。
2. `PXD077545` 是新的公开 PSNP protein-corona 数据集，论文报告 12 + 39 个 human-plasma samples，并提供 Source Data 与 PRIDE accession；但其提交/研究谱系仍属于 Michigan State University，不能作为新的独立 laboratory validation。它最多用于同谱系 biological-unit sensitivity analysis。
3. `PXD026615`（University of Salamanca/CSIC）保留为后续原始文件重处理候选；当前尚未形成满足本项目 source-cell、定量尺度、batch 和 target mapping 契约的行级数据，故不静默纳入。

因此，公开论文数据已经解决了“完全没有真实数据”的作者侧证据问题：可以进行可审计的 cohort/source audit、模型、配对消融、negative control、OOD 和 missingness 分析；但不能凭论文表格自动产生非作者 lockbox receipt、无作者科学复现、外部用户采用或 DOI 归档。`scientific_submission_ready` 继续保持 `false`。

## A. PXD054751：Sapienza University of Rome

### 可核验来源

- 论文全文：[Nature Communications/PMC11496629](https://pmc.ncbi.nlm.nih.gov/articles/PMC11496629/)。
- 公共原始数据记录：[PRIDE PXD054751](https://www.ebi.ac.uk/pride/archive/projects/PXD054751)。
- 许可：CC0-1.0；来源实验室：Sapienza University of Rome, Department of Chemistry。
- 局部下载资产：`data/raw/r4_candidate_pxd054751_rome/Results.xlsx`。
- 文件大小：482,408 bytes。
- SHA-256：`1b7ae06c0933e95e21c993e09ccb4edd7c1088757d34dfdfbbf5f80ad2242df6`。

### 结构与覆盖审计

| 审计项 | 结果 |
|---|---:|
| 结果表 protein rows | 198 |
| source-labelled conditions | 5 |
| 每个 condition 的作者强度列 | 3（A1–A3） |
| 总 intensity columns | 15 |
| 与冻结 R3 99-target ledger 的 unique overlap | 3 |
| 每个 condition 的 shared positive targets | 3, 3, 3, 3, 2 |
| 达到最低 10-target batch 要求的 condition | 0 |
| 可确认的 donor-level biological replicate map | 无 |
| 当前 admission | `NOT_ADMITTED` |

这 5 个 A1–A3 列不能在没有原始设计证据时被重新命名为 donor-level biological replicates。不同 formulation 的 intensity 也不是当前 rank endpoint 的共同量纲。故本来源可作为“独立候选已筛查且未满足 admission contract”的负结果，不能被用来增加有效样本量或制造外部验证结论。

## B. PXD077545：新的公开数据，但不是新的独立 laboratory

论文：[Integrated top-down and bottom-up proteomics enables precise characterization of proteoforms within the protein corona](https://www.nature.com/articles/s41467-026-74306-3)；数据记录：[ProteomeXchange PXD077545](https://proteomecentral.proteomexchange.org/dataset/PXD077545)。全文描述 12 个第一批与 39 个第二批 human-plasma samples，并提供 Source Data 与 PRIDE accession；每个样本含技术重复。

该来源具有真实的 biological-unit 价值，但 PRIDE 元数据所显示的提交/研究谱系仍为 Michigan State University，与当前 Michigan State 相关路线属于同一 lineage。故本项目的 claim boundary 为：

- 可以用于同谱系的 sample-unit accounting、敏感性分析或方法可迁移性展示；
- 不能称作“第三/第四个独立实验室”；
- 不能用于关闭 independent validation、external lockbox 或无作者 reproduction gate；
- 在没有重新建立 target/batch/source-cell 兼容映射前，不进入冻结 primary endpoint。

## C. PXD026615：保留候选，不提前计分

PXD026615 由 University of Salamanca/CSIC 公开，包含 human/rabbit/bovine plasma 相关 protein-corona 实验和全文数据描述。它值得继续做原始文件级重处理，但当前尚未完成：统一 target accession、样本/批次层级、实验室—研究—donor/patient—sample—batch—observation 链接、共同量纲和最低覆盖率核验。因此当前状态为 `CANDIDATE_PENDING_REPROCESSING`，不计入模型、有效 n 或独立验证评分。

本轮进一步读取 PRIDE 文件清单：共 100 个公开文件，包括 20 个 `.raw`、20 个 `.msf`、20 个 `.mzid.gz`、18 个 `.mgf` 以及 22 个 protocol/checksum 文件；清单中没有可直接复用的 protein-level tabular quantification matrix 或明确的样本设计表。也就是说，若要把它推进到 admission，必须先固定数据库/搜索参数并从原始或 peak/result 文件重建定量，再逐文件建立样本与 batch map；不能把“有 PRIDE accession”直接当作可执行 cohort。

## D. 对强 Q1 改进目标的更新

本轮把“通过全文论文数据寻找真实数据”落实为可复核的 admission 结果，而不是以来源数量代替证据质量。当前目标应保持以下硬门槛：

| 门槛 | 当前状态 | 允许的下一步 |
|---|---|---|
| 作者侧真实数据执行 | 已满足 | 继续使用已审计的 PMC/PRIDE cohort，并把 paper-data sensitivity 分层报告 |
| 3 个独立实验室 biological common target | 未满足 | 完成 PXD026615 原始文件重处理，或取得有 donor/sample/batch 链接的新独立来源 |
| 非作者 protected lockbox | 未满足 | 外部 evaluator 保存 protected input 并返回 aggregate signed receipt |
| 无作者原始输入科学复现 | 未满足 | 外部团队从固定 release 和公开 accession 起步，提交不可变 receipt |
| 外部用户采用 | 未满足 | 至少两份不同环境、不同任务的独立安装/使用 artifact |
| DOI/archive | metadata ready，未归档 | 认证归档后 read-back DOI 与 immutable hash |

本轮不提高现有强 Q1 综合分，也不将 `scientific_submission_ready` 改为 `true`。具体总审计见 [`R4_T229_CURRENT_STRONG_Q1_COMPLETION_AUDIT_20260814.md`](R4_T229_CURRENT_STRONG_Q1_COMPLETION_AUDIT_20260814.md)。

## E. 可审计判定

```text
paper_data_rescreened=true
public_fulltext_or_repository_traceability=true
new_independent_laboratory_admitted=false
author_side_real_data_execution_supported=true
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```
