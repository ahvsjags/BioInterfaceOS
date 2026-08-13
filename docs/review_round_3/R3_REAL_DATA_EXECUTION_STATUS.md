# R3 真实全文补充数据执行状态

**状态：`EXPLORATORY_REAL_DATA_EXECUTED_NOT_SUBMISSION_READY`**
**更新：2026-08-13**

## 这次真实做成了什么

我们没有以模拟数据替代实证。R3 将原始论文全文及其机器可读补充文件审计、映射为可追溯的实验单元，并在预先冻结的协议下实际运行了模型和外部 OOD 评估。

| 证据层 | 真实数据范围 | 已执行结果 | 不能推出的结论 |
|---|---:|---|---|
| R3 开发与留实验室评估 | 3 个独立实验室锚点，99 个共同 UniProt 蛋白，2,724 个蛋白×测量批次观测，47 个测量批次 | 嵌套选择、逐实验室外留、cluster bootstrap、置换负对照与配对消融均已运行 | 不能把三个来源的原始强度拼接为同一浓度尺度，也不能称为临床/材料效用 |
| 预声明外留：Oklahoma 金纳米颗粒 | 168 个观测，2 个批次 | 完整序列模型 mean batch Spearman 0.023（95% CI −0.030–0.077） | 不能选择性删除这一失败 OOD 来源 |
| 新增外部实验室：银纳米颗粒人血浆 | 50 个与冻结特征表直接相交的 UniProt 蛋白，953 个观测，30 个批次 | 完整模型 mean batch Spearman 0.497（95% CI 0.466–0.529）；相对 composition-only +0.053（95% CI 0.036–0.070）；within-batch permutation p=0.0039 | 这是作者运行的公共数据外部 OOD，不是独立 evaluator，也不是无作者科学复现 |

## 已冻结、可复核的主要对象

- R3 共同排序目标的原始账本：`data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv`，SHA-256 `de378c12ac1a92803145879adcc1e171a299b76cda46100ed03b9243b38741b8`。
- R3 序列特征表：`data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv`，SHA-256 `c8b6c2946d99a07374371928014148118ced4667ecfa3f58d025ce88057b62a5`。
- R3 主分析协议与外留 split：`docs/data/R3_T151_ANALYSIS_PROTOCOL.json` 以及 `reports/review_round_3/analysis_protocol/v1.0.0/`。
- 已执行的三实验室结果：`reports/review_round_3/common_rank_model_evaluation/v1.0.0/model_evaluation_report.json`。
- 银纳米颗粒全文源审计：`reports/review_round_3/silver_plasma_source_audit/v1.0.0/silver_plasma_source_audit_receipt.json`。
- 银来源 OOD 协议与结果：`docs/data/R3_T155_SILVER_EXTERNAL_OOD_PROTOCOL.json` 和 `reports/review_round_3/silver_external_ood/v1.0.0/silver_external_ood_report.json`。

银来源的全文补充表是 2019 年公开的人血浆/60 nm 银纳米颗粒研究：两个工作表共 899 个蛋白行、30 个条件×重复测量批次、13,485 个源单元，其中 9,357 个为可排序的正作者报告值。其具体源文件、字节大小和 SHA-256 已由 `R3_T154_SILVER_PLASMA_SOURCE_REGISTRY.json` 绑定。

## 反证与不纳入来源

`R3_T153_FURTHER_FULLTEXT_SCREEN.json` 记录所有新增全文章节筛查，而不是只保留支持性来源：

- `PMC4596693` 是 CC-BY 人血浆 SPION 数据，但与冻结特征表只有 18 个直接共同 UniProt 蛋白；硅涂层三列各仅 5–6 个可用蛋白，另三列虽有 12–15 个但只有三个批次。因此不满足事先定义的 12 批次外部 OOD 门槛。
- `PMC7484794` 的定量蛋白工作表含 `APOA1_BOVIN`、`ALBU_BOVIN` 等牛源记录，不能伪装成人血浆验证。

## 结果应如何解读

三实验室开发集的真实外留不是一致胜利：Michigan State 的 full model 为 0.247（95% CI 0.214–0.279），Seer/Broad 为 0.341（0.294–0.401），但在 Oklahoma 的 Gold 来源上失败。新银来源提供较强的、完全不参与训练或超参数选择的作者运行外部 OOD 支持。共同结论只能是：**蛋白序列特征对某些来源内的作者报告排序具有可复现的预测信号，但其跨材料、实验室与读出模式的泛化仍不均一。**

## 更新后的编辑成熟度评分（0–100）

| 模块 | 当前分数 | 评分理由 | 到 90 分的硬门槛 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 72 | 4 个实验室锚点、可追溯源单元和 50 个外部相交蛋白；仍不存在横跨全部来源的单一共同 target | ≥3 个新增实验室的预先协调 target，且每个实验室有充分独立 biological units |
| 统计分析设计 | 88 | estimand、嵌套选择、cluster bootstrap、负对照和缺失规则已冻结 | 公共时间戳预注册；独立统计审计确认实现与协议一致 |
| 统计执行与有效样本 | 84 | 2,724 个开发观测及 953 个外部 OOD 观测已真实运行 | 多研究共同目标的正式 effective n、敏感性和重复执行均通过 |
| 模型、消融与 OOD 证据 | 79 | 正、负 OOD 与配对消融均被保留；存在明确异质性和一个失败外留来源 | ≥3 个预留外部实验室、跨批次/材料一致的效果以及独立重跑 |
| 独立评估/lockbox | 12 | 协议和输入已准备，尚无第三方 receipt | 非作者 evaluator 在未知保护数据上一轮评估，签名并完成审计 |
| 外部科学复现 | 8 | 可重跑作者分析；没有无作者团队从原始输入复现实证结论 | 独立团队重新获取数据、重建并签署 deviation ledger 与结果 receipt |
| 用户可用性与外部采用 | 46 | 有可审计工作流，尚无公开 release、外部安装和 issue/PR 证据 | 版本 DOI、公开发布、独立安装与真实使用证据 |
| 强 Q1 综合成熟度 | 48 | 已从“无真实模型结果”升级为“可复核探索性真实数据证据” | 上述数据、lockbox、独立复现、公开采用四类硬门槛全部通过 |

这些数字是编辑性成熟度评分，不是效应量，也不是可投稿判定；当前 `scientific_submission_ready` 必须保持 `false`。
