# R4 T251 多角色编辑评审：论文数据替代路线后

结论：`MAJOR_REVISION`；`scientific_submission_ready=false`。

本轮评审把 T249/T250 的真实论文/补充表执行纳入证据链。它解决了上一轮最关键的内部缺口：没有可复核的跨来源共同 target、没有真实模型执行、没有外层来源留出结果。它没有改变非作者 lockbox、无作者复现、外部采用和 DOI read-back 的事实状态。

## 综合分数

| 模块 | 本轮 | 目标 | 评语 |
|---|---:|---:|---|
| 数据兼容性与样本基础 | 92 | 90 | 4 个 source/lab anchors、7 个严格共同 accession、783 条共同观察；但若干来源仍 pooled、donor-unresolved 或 technical-only |
| 统计分析设计 | 94 | 90 | estimand、source-local rank、nested selection、cluster uncertainty、missingness 和 leakage boundary 完整 |
| 统计执行与有效样本 | 94 | 90 | 4-fold held-out execution、115 measurement batches、真实模型拟合、2,000 bootstrap 和 256 permutation/折；effective biological n 仍不能从公开 map 推断 |
| 模型、消融、negative control 与 OOD | 92 | 90 | full/composition/constant 三模型、paired ablation、negative control、论文 OOD 已有 receipt；外部 OOD 仍非无作者验证 |
| 独立评估 / lockbox | 12 | 90 | 无真实非作者 evaluator receipt |
| 外部科学复现 | 8 | 90 | 无无作者参与的 PMC6592156 或主路线复现 receipt |
| 外部用户采用 | 46 | 90 | GitHub/issue/handoff 已准备，但无两个非作者安装或用户报告 |
| DOI 不可变归档 | 25 | 90 | release metadata、archive hash 和 deposit packet 已准备，但无 DOI authenticated read-back |

8 个模块的简单均值为 **57.9/100**；前四个“内部科学核心模块”均值为 **93.0/100**，后四个“外部可接受性模块”均值为 **22.8/100**。因此不能把内部 90+ 误报成强 Q1 已接收级别。

## 多角色意见

| 角色 | 分数 | 主要判断 |
|---|---:|---|
| EIC | 63 | 有真实论文数据和可复核模型结果，但外部证据门槛未过，建议大修后再审 |
| Statistical methodologist | 94 | 设计和执行闭环强；需要把 6-batch Dalian fold 和 biological effective n 限制置于主文显著位置 |
| Proteomics / nanobio interface | 89 | 四来源共同 target 具有价值；仍不能将技术条件、pooled plasma、donor-unresolved map 写成独立生物学队列 |
| Reproducibility / software resource | 82 | CLI、hash、ledger、receipt、clean-check 已成形；真实外部安装和第三方结果尚缺 |
| Devil’s advocate | 49 | 如果主张“泛化/生物学验证”，会因非作者 lockbox 与 donor independence 不足而拒稿 |
| Synthesis editor | 66 | 可以形成一篇诚实的 exploratory benchmark/resource 论文；不能以“实验数据不可得”为理由填造外部结果 |

## 新增真实证据

T249 使用 PMC6592156/PXD007648 论文补充表作为第四来源：30 个 pH/temperature batches、899 个蛋白、13,485 个 source-map cells，和当前三来源严格交集后保留 7 个 common accession。T249 receipt 为 4 anchors / 7 targets / 783 common observations / 115 measurement batches。

T250 在 target freeze 之后执行四个 leave-one-laboratory-anchor-out folds。Full sequence ridge 的 outer mean Spearman 为 0.926、0.687、0.685、0.766，分别对应 Dalian、UCD、Edinburgh 和 University of Southern Denmark/Russian Academy of Sciences；2,000 个 batch-cluster bootstrap 与 256 次 within-batch permutation 均已写入 receipt。Dalian 只有 6 个 batches，不能据此声称稳定的 biological generalization。

## 强 Q1 门禁

以下门禁仍为 false，不能由论文补充数据替代：

- 非作者 lockbox evaluator receipt；
- 无作者参与的科学复现实证；
- 两个非作者外部用户安装/采用 receipt；
- DOI 服务 authenticated read-back；
- 最终 scientific submission gate。

因此当前最准确的投稿定位是：**有真实公开论文数据支撑的、可审计 exploratory cross-source rank-portability/resource 论文，大修后可投；尚不具备强 Q1 稳投证据。**

复核文件：

- [T249 四来源共同 target 状态](R4_T249_FOUR_LAB_COMMON_TARGET_PAPER_DATA_STATUS_20260814.md)
- [T250 四来源模型执行状态](R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_STATUS_20260814.md)
- [T251 JSON 评审记录](R4_T251_MULTI_AGENT_EDITORIAL_REVIEW_20260814.json)
