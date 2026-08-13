# R4_T186 Multi-Agent Editorial Review — Corrected Manchester OOD

日期：2026-08-14  
评审角色：统计方法、数据来源/独立性、主编/投稿编辑

## 1. 本轮新增的真实证据

Manchester/Manchester BRC 的作者公开 nano-omics 矩阵被作为 analysis-only external source 审计并在 KAUST 重跑。它不是受保护 lockbox，也不是无作者复现。

| 项目 | 已核验值 |
|---|---:|
| source cells | 193,971 |
| positive source cells | 177,636 |
| biological units | 61 patients |
| measurement batches | 289 longitudinal patient-timepoint batches |
| qualified batches | 289 |
| frozen target coverage | 25 unique canonical accessions |
| external target observations | 4,169 |
| model count | 3 |

证据入口：

- [T185 source registry](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/docs/data/R4_T185_MANCHESTER_NANOOMIC_SOURCE_REGISTRY.json)
- [T186 OOD protocol](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/docs/data/R4_T186_MANCHESTER_NANOOMIC_BIOLOGICAL_OOD_PROTOCOL.json)
- [corrected OOD report](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/reports/review_round_4/manchester_nanoomic_ood/v1.0.0/r4_manchester_nanoomic_ood_report.json)
- [source audit receipt](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/reports/review_round_4/manchester_nanoomic_source/v1.0.0/r4_manchester_nanoomic_source_receipt.json)

## 2. 修正后的统计结果

- `SEQUENCE_RIDGE_FULL`: subject-equal mean Spearman `0.29415`, 95% patient-cluster CI `[0.26269, 0.32520]`。
- `SEQUENCE_RIDGE_COMPOSITION_ONLY`: `0.35271`, 95% patient-cluster CI `[0.31637, 0.39020]`。
- full minus composition-only：patient-equal mean `-0.05855`，95% patient-cluster CI `[-0.07781, -0.04022]`，61 patients / 289 paired batches。
- corrected within-development-batch target permutation：每次 permutation 重新执行 nested alpha selection；正确统计量为 61 个患者的 subject-equal mean Spearman；256 resamples 的 upper-tail `p=0.03113`，null 95% interval `[-0.52666, 0.29570]`。

该结果支持“Manchester source 上存在可测的 external OOD signal”，但不支持“full physicochemical feature set 优于 composition-only”，也不支持临床验证、独立 evaluator 验证或广泛泛化。

## 3. 三智能体复核与综合评分

三个角色的关键结论一致：Manchester 是新的 laboratory anchor，可称为 `author-run exploratory OOD on a distinct Manchester laboratory source`；不能称 `independent validation`、`externally replicated` 或 `external scientific reproduction`。

| 模块 | 评审范围 | 综合分 | 编辑解释 |
|---|---:|---:|---|
| 数据兼容性与样本基础 | 78–85 | **84/100** | 25 个冻结 target、4,169 个外部 target observations 和逐 cell provenance 已有；但仅覆盖 25/99，纵向列不是独立样本，作者矩阵仓库无显式 LICENSE。 |
| 统计分析设计 | 86–90 | **88/100** | estimand、development-only nested selection、患者聚类不确定性、配对消融和 selection-aware permutation 已冻结；仍需预先规定 qualification-induced missingness、多重比较和最终失败规则。 |
| 统计执行与有效样本 | 76–84 | **80/100** | 已在 KAUST 真实执行，61 个患者是有效推断单位；但作者运行结果不能替代第三方科学复现。 |
| 模型、消融与 OOD 证据 | 45–58 | **47/100** | 新增真实 OOD；但 full 明显低于 composition-only，因而核心 sequence-driven 增量主张没有得到支持。 |
| 独立评估 / protected lockbox | 4 | **4/100** | 没有非作者 evaluator、受保护输入、签名 aggregate receipt。 |
| 外部科学复现 | 0 | **0/100** | 没有无作者参与的 clean-checkout、环境重建和端到端科学结果 receipt。 |
| 外部用户采用 | 0 | **0/100** | 没有真实外部机构使用、失败记录、输出或可核验引用。 |
| DOI / release provenance | 20 | **20/100** | 软件已有 GitHub release，但 corrected T186 结果尚未进入不可变版本，且没有 DOI deposit receipt。 |
| 强 Q1 综合成熟度 | 28–30 | **29/100** | 该项受 lockbox、无作者复现、采用和 DOI 硬门槛限制，不是简单平均。 |

## 4. 编辑决定

**当前决定：Major Revision；不建议以 sequence-driven、独立验证或临床泛化论文投强 Q1。**

可接受的稿件定位是：具有严格审计协议和真实 exploratory external OOD 的可复现计算方法/benchmark，并如实报告 full 模型在 Manchester 上被 composition-only ablation 击败这一结果。

当前必须禁止的表述：

- `independently validated`；
- `externally replicated`；
- `sequence-driven improvement`；
- `broad generalization`；
- `community adopted`。

## 5. 下一轮强 Q1 改进目标

完整目标写入 [R4_T187 strong-Q1 remediation goal](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/docs/review_round_4/R4_T187_STRONG_Q1_REMEDIATION_GOAL_20260814.md)。在以下证据全部真实、独立、可核验之前，`scientific_submission_ready` 必须保持 `false`：

1. 非作者 evaluator 完成 protected lockbox，一次性输出固定版本、受保护输入、日志 hash、aggregate metrics 和签名 receipt。
2. 无作者参与团队从 clean checkout 完成环境安装、原始输入起步、数据映射、模型执行和结果比对，并提交 reproduction receipt。
3. 至少两份真实外部用户/机构 adoption receipt，记录版本、环境、任务、输出、失败和 issue/PR 或引用。
4. 将 corrected T186 结果与最终代码/协议/数据指针放入新的不可变 release，并取得 DOI deposit receipt；不把无 LICENSE 的作者矩阵复制进 release。
5. 对模型贡献重新预注册：要么承认 composition-only 是 Manchester 上的主结果并重写 scientific claim，要么在新数据解封前冻结新的模型/消融/OOD 合同，不能事后挑选有利模型。
6. 至少补齐一个具有明确可再分发许可、不同生物实验室、共同冻结 target 且有 biological-unit-level evidence 的独立来源；现有 Manchester 只计一个新 laboratory anchor。

## 6. 结论

本轮解决了“没有真实外部 OOD 执行”和两个统计实现问题，但没有解决独立评估、无作者复现、外部采用、DOI 及 full-model 增量证据。因此本轮不是强 Q1 通过，而是将工作从“无真实外部结果”提升到“有真实、校正后的 exploratory external OOD，仍 Major Revision”。
