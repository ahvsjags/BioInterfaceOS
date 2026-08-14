# R4-T264：PXD068107 全文衍生真实数据执行报告

日期：2026-08-14
状态：`EXECUTED_EXPLORATORY_TECHNICAL_OOD_EXTERNAL_GATES_OPEN`

## 结论

通过 PMC 全文、PRIDE accession 和 BioStudies source-data 的三段式证据链，BioInterfaceOS 已经在 PXD068107 上完成一次可复核的真实作者侧技术 OOD 执行。该结果补足了“只有 protocol、没有真实模型结果”的缺口，但不能被解释为 193 个独立患者，也不能替代非作者 lockbox、无作者复现或外部采用证据。

## 数据证据链

| 层级 | 证据 |
|---|---|
| 全文 | PMC12808129，研究对象为血液污染与纳米颗粒血浆蛋白组流程 |
| 仓储 | PRIDE PXD068107，Westlake University，CC0 |
| 可下载 source data | BioStudies `2b_heatmap.xlsx` 及相关图表 source files，逐文件 SHA-256 固定 |
| 主矩阵 | `2b_heatmap`，21 行技术/纳米颗粒条件 × 7,819 蛋白列 |
| 与冻结 R3 特征的交集 | 98 个 canonical proteins；每个条件至少 82 个正值共同蛋白 |
| 生物学单位边界 | 1 个 pooled/technical source；本轮不把论文报道的 193 人数转成蛋白×患者矩阵 |

行级 source-cell ledger：`data/raw/r4_candidate_pxd068107/derived/R4_PXD068107_technical_source_cell_map.csv`。
审计 receipt：`reports/review_round_4/pxd068107_source_audit/v1.0.0/pxd068107_source_audit_receipt.json`。

## 预注册执行结果

固定 R3 development population 为 2,724 observations；外部 PXD068107 为 1,976 observations、21 个 technical-condition clusters。使用 source-local positive rank，禁止跨研究 raw-scale 合并；模型为 constant、full sequence ridge 和 composition-only ridge。

| 模型 | mean Spearman | 95% CI | 备注 |
|---|---:|---:|---|
| Full sequence ridge | 0.17861 | [0.14194, 0.21418] | 真实论文 source-data technical OOD |
| Composition-only ridge | 0.19994 | [0.17010, 0.22984] | 高于 full model，提示 sequence feature 增益不稳健 |
| Constant training mean | undefined | — | 仅报告 MAE/RMSE |

配对消融：full − composition = `-0.02133`，95% CI `[-0.03864, -0.00449]`。
开发集内 cluster permutation：观察值 `0.17861`，上尾 `p=0.01167`。
完整 JSON receipt：`reports/review_round_4/pxd068107_technical_ood/v1.0.0/r4_pxd068107_technical_ood_report.json`。

## 编辑边界与分数更新

这项证据把“真实模型/OOD 尚未执行”提升为“已有一项可复核的论文衍生技术 OOD”，但不增加 biological effective n，也不关闭独立实验室共同生物 target、非作者 lockbox、无作者复现、外部采用或 DOI read-back 门禁。当前保守分数为：

| 模块 | 分数 | 仍需解决 |
|---|---:|---|
| 数据兼容性与样本基础 | 85 | 行级 donor-to-batch crosswalk；至少 3 个独立实验室共同 biological target |
| 统计分析设计 | 88 | 独立外部团队运行后复核预注册执行 |
| 统计执行与有效样本 | 86 | 独立 source/团队确认 effective n |
| 模型、消融与 OOD | 84 | 非作者数据锁定评估、更多独立生物学 OOD |
| 独立评估/lockbox | 0 | 非作者签名 receipt |
| 外部科学复现 | 0 | 无作者原始输入起步 receipt |
| 外部用户采用 | 0 | 两个真实外部用户/机构安装与任务 receipt |
| DOI immutable archive/read-back | 10 | DOI deposit 与 read-back receipt |

因此仍保持：`scientific_submission_ready=false`，综合决策为 `MAJOR_REVISION_EXTERNAL_GATES_UNVERIFIED`。论文衍生数据解决的是作者侧实证执行，不是第三方证据的替代品。
