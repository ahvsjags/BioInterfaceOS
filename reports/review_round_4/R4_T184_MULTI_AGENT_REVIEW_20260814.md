# T184 Multi-Agent Review — PMC3252235 full-text source

日期：2026-08-14。三位独立角色代理分别从来源兼容性、统计设计和编辑审稿角度复核了 PNNL/PMC3252235 的实际补充表与 T184 机器 receipt。

## 共识事实

- 真实来源：PMC3252235，Pacific Northwest National Laboratory，人血浆纳米颗粒蛋白冠研究。
- 补充表 `S. Table 6`：24 个条件列，论文报告 88 个定量蛋白。
- 24 列是 3 种表面 × 2 种粒径 × 4 个时间点的条件/处理记录，不是 24 个独立 donor-level biological replicates。
- 当前冻结 R3 target universe 为 99 个 accession；逐列只有 `P04004` 和 `P06396` 两个直接重合，24 列均只有 2 个可用重合 target。
- 预注册最低覆盖为每个 measurement batch 至少 10 个正值 shared targets；PNNL 为 0 个合格列。
- `oa.xml` 的官方响应为 `idIsNotOpenAccess`；补充 XLS 的可再分发许可仍是 `NOASSERTION`，所以不进入公开 release。
- `18O` universal reference 是跨条件的肽段池，不是一个新的 biological replicate；mouse protocol-development replicates 也不进入 human 24-condition ledger。

## 代理结论

| 评审角色 | 判断 |
|---|---|
| 来源/兼容性 | 只能作为来源筛选候选；目标重合和许可均不足，不能进入主 OOD 或现有 technical OOD。 |
| 统计设计 | 可记录为 24 个 condition/process records；保守生物学单位为 1 或未报告，不能把 24 当作有效生物学 n，也不能普通独立样本 bootstrap。 |
| 编辑/强 Q1 | 只提高来源获取与拒纳审计的可追溯性；不关闭 independent lockbox、no-author reproduction、adoption、DOI 或 `scientific_submission_ready`。当前强 Q1 综合仍为 30/100，Major Revision。 |

## 允许与禁止的表述

允许：

> PMC3252235 is a human-plasma nanoparticle protein-corona source candidate with 88 quantified protein rows across 24 experimental conditions. Only two exact accessions overlap the frozen R3 target ledger; donor-level independence and a redistributable license are unresolved. The source was therefore excluded from both main and technical OOD and retained for source screening only.

禁止：

- “24 个独立生物学样本”；
- “88 个 R3-compatible target”；
- “PNNL external OOD performance”；
- “PNNL 验证了模型”；
- 把论文作者的 ANOVA 或作者分析当作 BioInterfaceOS 的独立复现；
- 为纳入 PNNL 而降低 10-target 门槛或事后扩展冻结 R3 target。

## 评分影响

| 模块 | T184 后保守分 | 变化 |
|---|---:|---|
| 数据兼容性/样本基础 | 84–85 | 不升；新来源未通过冻结兼容门槛。 |
| 统计设计 | 84–86 | 不升；没有新的预注册分析。 |
| 统计执行/有效 n | 68–72 | 不升；未运行模型，且 24 条件不能替代 biological n。 |
| 模型/消融/OOD | 52–56 | 不升；没有新的 prediction、CI、ablation 或 negative control。 |
| Protected lockbox | 4 | 不变。 |
| 无作者科学复现 | 0 | 不变。 |
| 外部采用 | 0 | 不变。 |
| DOI/release provenance | 25–30 | 不变；T184 不在 v0.1.3-r9.1 且没有 DOI receipt。 |
| 强 Q1 综合 | 30 | 不变；`scientific_submission_ready=false`。 |

机器证据：[T184 source screen](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/docs/data/R4_T184_PMC3252235_SOURCE_SCREEN.json)、[T184 status](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/docs/review_round_4/R4_T184_PMC3252235_SOURCE_STATUS.md)、[T184 receipt](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/reports/review_round_4/pmc3252235_source_screen/v1.0.0/r4_pmc3252235_source_screen_receipt.json)。
