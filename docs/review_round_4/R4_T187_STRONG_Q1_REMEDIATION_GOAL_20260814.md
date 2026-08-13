# R4_T187 Strong-Q1 Remediation Goal

## Objective

将 BioInterfaceOS 从“作者运行、analysis-only external OOD 的探索性 benchmark”推进到具有可核验外部科学证据的强 Q1 投稿候选。所有证据必须真实产生于固定版本和固定协议；不能用作者运行、Codex/KAUST 内部运行、公开链接或结构化空 receipt 代替外部证据。

## Exit criteria

| Gate | Required evidence | Pass condition |
|---|---|---|
| Licensed independent data | 至少一个新增明确许可、不同生物实验室的共同冻结 target 来源，并覆盖 biological units | source bytes、许可、target map、unit map、missingness 和 hash 全部可审计 |
| Statistical execution | 修正版 Manchester 及后续来源均执行 frozen estimand、patient/biological-unit cluster uncertainty、paired ablation、negative control | report/receipt 与代码 hash 一致，失败规则和 effective n 可复核 |
| Model contribution | full、composition-only、constant、负对照及 OOD 结果均按预注册合同报告 | 不得删除 full 失败结果；若 full 不优于 baseline，主张必须降级或重写 |
| Independent lockbox | 非作者 evaluator 一次性访问受保护数据 | evaluator identity/COI、commit、environment、input hash、logs、aggregate output hash 和签名 receipt 完整 |
| No-author scientific reproduction | 无作者参与团队从 clean checkout 和原始输入起步 | 独立环境重建、端到端科学结果对齐、差异解释和 receipt 完整 |
| External adoption | 至少两份真实外部用户/机构记录 | 版本、环境、实际任务、输出、失败、issue/PR 或引用可核验 |
| DOI/release | corrected artifacts in immutable release | release tag、asset manifest、DOI deposit receipt、data pointer and license boundary agree |
| Editorial gate | 三个独立评审角色复核最终 bundle | all module scores >=90 and `scientific_submission_ready=true`; otherwise remain Major Revision |

## Work packages

1. **Empirical source expansion**：继续优先全文论文、PMC/PRIDE/ProteomeXchange 等可核验来源；默认只接受明确许可或可公开再分发的 processed data。Manchester 当前仅作为 analysis-only exploratory OOD，不提高为独立验证。
2. **Model claim repair**：以 composition-only 胜过 full 的 Manchester 结果为强制负向证据；在任何新数据解封前冻结模型、消融、负对照、missingness、multiple-comparison 和 stopping rules。
3. **External evidence collection**：通过预先定义的 handoff bundle 寻找非作者 evaluator、无作者复现团队和真实外部用户；仅接收带身份/COI/版本/hash/日志/签名的 receipt。
4. **Publication and archival**：完成最终 release manifest、许可证审计、数据指针、DOI deposit 和 manuscript claim ledger，再进行最后一轮多智能体编辑审查。

## Non-negotiable boundaries

- `author-run exploratory OOD` 不得写成 `independent validation`。
- 61 patients、289 longitudinal batches 和 4,169 target observations 不得写成 4,169 个独立 biological replicates。
- GitHub release 不得写成 DOI；无作者参与的 agent review 不得写成 external reproduction。
- 如果新的数据继续显示 full 不优于 composition-only，正确动作是重写贡献边界，不是删除负结果或事后换 endpoint。
