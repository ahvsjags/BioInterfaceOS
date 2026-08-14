# R4-T233：PXD026615 mzIdentML 全文件重处理与纳入判定

日期：2026-08-14。目的：对 PXD026615（University of Salamanca-CSIC）进行不依赖作者内部文件的公开结果级重处理，判断它能否补足当前 primary common-target endpoint 的独立实验室缺口。

## 结论先行

PXD026615 确实是独立实验室、开放论文、公开 PRIDE 结果资产，且论文研究了 human plasma、rabbit plasma 和 fetal bovine serum 中的 IONP/IONP-Pt protein corona。但全文件审计显示：

- 属于 corona 路线的 human 文件组 `0363_1_1`、`0363_2_1`、`0363_3_1` 与冻结 R3 99-target ledger 的正向交集分别为 5、3、5，联合交集只有 5；
- `0363_4_1`–`0363_6_1` 主要显示 bovine/contaminant protein annotation，`0363_7_1`–`0363_9_1` 主要显示 rabbit annotation，不构成 human primary endpoint；
- 其余 `0379_*` 与 `180430_0355_*` 虽有较高 human target overlap，但论文将相应路线用于 Caco-2/Jurkat 细胞内/AHA 新合成蛋白研究，而不是 plasma protein corona，不能把它们混入 corona target matrix；
- mzIdentML 提供的是 identification/PSM evidence，不是当前 primary 所需的跨研究共同尺度 quantitative intensity matrix。

因此 PXD026615 当前判定为 `NOT_ADMITTED_LOW_CORONA_COVERAGE_AND_ENDPOINT_MIXTURE`。它关闭了“尚未核查 PXD026615”的审计缺口，但没有关闭“3 个独立实验室 primary common-target”门禁。

## 可核验来源与资产

- 论文全文：[Journal of Nanobiotechnology, 10.1186/s12951-022-01546-y](https://link.springer.com/article/10.1186/s12951-022-01546-y)。论文明确描述 human plasma、rabbit plasma、FBS 的 corona 比较，并将 Caco-2/Jurkat 的 AHA 标记作为 intracellular proteomics 路线。
- 数据记录：[PRIDE PXD026615](https://www.ebi.ac.uk/pride/archive/projects/PXD026615)。
- PRIDE API 文件清单：[PXD026615 files API](https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD026615/files)。
- 本地审计目录：`data/raw/r4_candidate_pxd026615_salamanca/`。
- 20 个 `.mzid.gz` 全部以 PRIDE API checksum 复核通过；API 报告的解压后总字节数为 250,649,665，当前本地 gzip 字节数为 29,635,301。
- 论文补充 DOCX 的静态下载端点返回 3,038-byte anti-bot HTML challenge，而非合法 Office 文件；该失败资产保留但未用于样本/数值推断。

## 重处理方法

1. 从每个 mzIdentML 的 `DBSequence` 建立 `id -> accession` 映射。
2. 从 `PeptideEvidence` 建立 `id -> DBSequence accession` 映射。
3. 仅使用 rank-1 `SpectrumIdentificationItem`，按 `PeptideEvidenceRef -> PeptideEvidence -> DBSequence` 累计 PSM evidence。
4. 以 `common_rank_target_member=true` 的冻结 R3 ledger canonical accession 作为 target 集合，共 99 个 target。
5. 对每个结果文件分别计算 positive accession 数和冻结 target 正向交集；不把同一论文的不同 protein-domain 路线合并为 biological replicate。

该结果是公开结果文件的 presence/PSM-level bounded audit，不是作者原始 abundance 的重建，也不将 PSM count 伪装成跨研究统一 intensity。

## 文件级结果

| 文件组 | 结果文件 | positive accession 数（逐文件） | 冻结 target 交集（逐文件） | endpoint 判定 |
| --- | --- | ---: | ---: | --- |
| `0363_1–3` | 3 个 human-annotated corona 文件 | 466, 289, 528 | 5, 3, 5；union 5 | human corona candidate，但低于 10-target admission |
| `0363_4–6` | 3 个 bovine/contaminant-dominant 文件 | 495, 535, 516 | 2, 2, 2 | 非 human primary |
| `0363_7–9` | 3 个 rabbit-annotated 文件 | 648, 421, 568 | 2, 2, 2 | 非 human primary |
| `0379_1–6` | 6 个 human cellular/AHA-related 文件 | 5,570, 1,952, 5,878, 9,659, 10,146, 8,258 | 68, 43, 73, 87, 91, 86 | domain mismatch，不得并入 corona |
| `180430_0355_1–6` | 6 个 human cellular/AHA-related 文件（PRIDE 中有一缺失 mzid entry） | 2,236, 2,749, 823, 629, 200（实际下载的 5 个） | 81, 89, 2, 2, 2 | domain mismatch，不得并入 corona |

`0363_1–3` 的 human corona 交集只有 5 个，且文件名/结果文件本身没有提供可独立证明的 donor-level biological map。论文也把 corona 与 intracellular AHA 研究放在同一 ProteomeXchange 项目中；因此仅凭“20 个 mzIdentML”不能把文件数当成 biological n。

## 纳入判定

| 门槛 | 结果 |
| --- | --- |
| 新独立实验室 | 是，Salamanca-CSIC |
| 公开可重获结果文件 | 是，20/20 checksum matched |
| human corona source-cell ≥10 frozen targets | 否，最大 5，union 5 |
| 可比 quantitative intensity matrix | 否，当前重建为 identification/PSM evidence |
| donor/sample/batch map | 未由公开文件充分证明 |
| 是否加入 primary effective n | 否 |
| 当前状态 | `NOT_ADMITTED_LOW_CORONA_COVERAGE_AND_ENDPOINT_MIXTURE` |

这次重处理不能提高 primary common-target 分数，但提高了来源审计的完整性：PXD026615 现在从“待处理候选”变成了有文件级证据支持的“不纳入”结论。不得使用 `0379_*` 或 `180430_*` 的高 target overlap 来制造 corona 共同 target，因为论文明确将这部分用于细胞内 AHA/新合成蛋白路线。[论文方法与 AHA 路线](https://link.springer.com/article/10.1186/s12951-022-01546-y)

## 门禁更新

```text
pxd026615_full_mzid_reprocessed=true
pxd026615_all_public_mzid_checksums_verified=true
pxd026615_human_corona_primary_admitted=false
new_independent_laboratory_primary_admitted=false
additional_primary_effective_n_created=false
scientific_submission_ready=false
```
