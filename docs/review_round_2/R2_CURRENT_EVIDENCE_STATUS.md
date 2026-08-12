# BioInterfaceOS 第二轮审稿：当前证据状态台账

本台账将初始整改矩阵中的九项意见绑定到当前 receipt。`PASS` 只表示表中限定的过程或公开发布门禁通过；不表示形成可投稿的实证结论。`FALLBACK` 表示已验证降级定位；`OPEN` 表示原始科学问题仍缺少可接受证据。

| ID | 当前可审计状态 | 当前定位 | 仍需满足的条件 |
|---|---|---|---|
| R2-01 | OPEN_EMPIRICAL_TARGET_UNAVAILABLE | 当前 T129 汇总覆盖 6 个候选来源、5 个实验室和 24 个已核验源资产。PXD030327 的 636 个来源 run 与 819 个矩阵列已映射，但 NP 标签仍为类别、数值字段仅为 P/NP 暴露且仅单实验室。T132 审计 PXD017052 的完整 12 个 CC-BY 出版方资产，并将 9 个结果/原始单位显式闭合到 SPION 与重复号；该路线仍为单实验室、尚未获 CC-BY cohort amendment，且无跨研究共同终点。未冻结共同 target，禁止模型使用 | 真实、非 fixture 的跨研究共同终点、数值材料/粒径协变量与行级溯源；冻结模型输出和外部 held-out 评估 |
| R2-02 | FALLBACK_PROTOCOL_ONLY_VERIFIED | Paper C 仅为预注册/协议稿，不是独立 replication | 独立 evaluator、冻结代码、受保护真实观测与签名 receipt |
| R2-03 | OPEN_STATISTICAL_VALIDATION_UNAVAILABLE | 不报告模型、消融、OOD 或有效样本量结论 | 冻结 estimand/split、study-clustered 分析、nested selection、effective n |
| R2-04 | FALLBACK_SOFTWARE_REPLAY_BOUNDARY_VERIFIED | 历史 fixture 稿件的违规表述以源哈希隔离，排除于当前 R2 稿件与公开发布范围；不作为 scientific replication | 获得外部 scientific reproduction receipt |
| R2-05 | PASS_LITERATURE_AND_DOMAIN_PACKET | 外部文献、comparators 与术语定义包可用于后续稿件 | 将其与真实数据和独立验证门禁共同满足，不能单独支持实证结论 |
| R2-06 | PASS_PUBLIC_RELEASE_AUDIT | 公开包完整性已审计；历史 fixture bundle 未公开 | 与真实数据、运行环境和外部复现 receipt 一并通过提交门禁 |
| R2-07 | FALLBACK_PROTOCOL_FIGURE_QA_VERIFIED | 三张 field-mapped 协议图通过 geometry/semantic QA，未绘制实证值 | 真实数据图的字段映射、统计与人工签署 |
| R2-08 | FALLBACK_MERGED_PROTOCOL_PORTFOLIO_VERIFIED | A+B 合并，C 保持 protocol-only；历史 fixture 稿件不复用 | T123 真实 target 与 T124 独立评估后再决定 results 稿件 |
| R2-09 | OPEN_EXTERNAL_ACCEPTANCE_REQUIRED | 项目仍为 IN_PROGRESS；T128 的下一版将绑定 T132 更正后的当前 T129 证据与两条 protocol 稿件路径，现有九个阻塞项 | 外部复现、编辑复审、逐项 finding 映射与签名证明 |

## 使用规则

1. 任何状态变化必须先生成新的版本化 receipt，再更新本台账和 `REMEDIATION_MATRIX.md`。
2. 任何 `OPEN` 项不得在摘要、图注、新闻稿或稿件中改写为已验证的实证结论。
3. `FALLBACK` 与 `PASS` 项只能支持本行的当前定位；它们不将 `scientific_submission_ready` 改为 `true`。
4. 只有全部仍适用于目标稿件的 R2 finding 均有符合其验收门禁的证据，且 T128 获得外部复现和编辑复审签名后，才可重新评估 submission-ready。
