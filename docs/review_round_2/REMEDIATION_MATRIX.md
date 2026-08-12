# BioInterfaceOS 第二轮审稿整改矩阵

基线：2026-08-12 五位独立评审的综合报告。此矩阵将 findings 映射为任务和可检验证据；`OPEN` 不等于可以忽略，表示没有满足验收门禁。

| ID | 审稿 finding | 严重性 | Owner tasks | 通过证据 | 不通过时的公开定位 | 初始状态 | 当前证据状态 |
|---|---|---|---|---|---|---|
| R2-01 | 关键 quantitative outputs 由 fixtures 驱动 | Critical | T116,T120,T122,T123,T129 | 非-fixture row-level provenance、raw predictions、external held-out evidence | software/schema/protocol only | OPEN | OPEN_EMPIRICAL_TARGET_UNAVAILABLE |
| R2-02 | Paper C 的 status 预置，非独立科学 replication | Critical | T116,T121,T124,T127 | 独立 evaluator、frozen code、真实 protected observations、签名 receipt | preregistration/protocol | OPEN | FALLBACK_PROTOCOL_ONLY_VERIFIED |
| R2-03 | 有效独立单位和不确定性不足；selection leakage | Critical | T121,T122,T123,T124,T129 | frozen estimand/split、study-clustered analysis、nested selection、effective n | exploratory analysis only | OPEN | OPEN_STATISTICAL_VALIDATION_UNAVAILABLE |
| R2-04 | software replay 与 scientific replication 混用 | Major | T116,T118,T124,T128 | 分开定义、report labels、外部 scientific reproduction receipt | deterministic software replay only | OPEN | OPEN_HISTORICAL_SEMANTIC_MIGRATION_REQUIRED |
| R2-05 | 外部 literature、comparators、变量/单位/assay 定义缺失 | Major | T120,T125,T126,T127 | bibliography、nearest-neighbor table、operational glossary | technical report only | OPEN | PASS_LITERATURE_AND_DOMAIN_PACKET |
| R2-06 | 公开包许可证、README、source-data、specs、receipts、container 不完整 | Major | T117,T118,T128 | asset-license registry、resolved paths、SBOM、rebuild receipt | partial release with explicit limits | OPEN | PASS_PUBLIC_RELEASE_AUDIT |
| R2-07 | 图件发生 clipping，且绘制错误字段 | Major | T119,T126,T127 | explicit field maps、bounds/semantic/visual tests、human signoff | withdraw affected panels | OPEN | FALLBACK_PROTOCOL_FIGURE_QA_VERIFIED |
| R2-08 | A/B 贡献重叠；C 体裁与证据等级错配 | Major | T125,T126,T127 | merged A+B manuscript；C protocol/results decision tied to T124 | single software/protocol portfolio | OPEN | FALLBACK_MERGED_PROTOCOL_PORTFOLIO_VERIFIED |
| R2-09 | 项目仍标记 IN_PROGRESS，final audit/test count口径不统一 | Major | T118,T128 | release-level JUnit receipt、consistent audit wording、external re-review | IN_PROGRESS with public blocker ledger | OPEN | OPEN_EXTERNAL_ACCEPTANCE_REQUIRED |

## Evidence-class policy

| Evidence class | 允许支持的结论 | 禁止支持的结论 |
|---|---|---|
| Fixture/CI test | parser、schema、contract、failure gate、deterministic behavior | material performance、generalization、replication、law、clinical/biological effect |
| Software replay | declared environment 下的 deterministic rebuild | independent scientific replication 或 empirical validity |
| Development real data | exploratory model/association、protocol feasibility | externally confirmed empirical claim，除非通过预定 validation gate |
| Independent locked evaluation | frozen claim 的 evaluator-backed status | 未在 preregistration 内定义的 post-hoc claim |
| External scientific reproduction | 可重建的 empirical conclusion，限于其验证范围 | 普适性或因果性超出研究设计的主张 |

## 验收使用方式

每个 owner task 完成时必须在对应 deliverable 中链接到本矩阵 ID、输入 hash、执行命令、结果、失败记录和 reviewer-readable explanation。T128 只有在所有仍属于目标稿件的 R2 IDs 都有可审计 `PASS` 证据后，才允许将稿件状态改为 submission-ready；若其中任何项只能走 fallback，对应稿件必须按本矩阵的公开定位降级。
