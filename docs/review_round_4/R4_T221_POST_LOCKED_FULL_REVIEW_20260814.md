# R4 T221 锁定环境全套执行后的多智能体编辑复审

日期：2026-08-14  
评审提交：`ff32694ed3935feca7a120d4125b30034c295e89`  
执行环境：KAUST `.venv`，CPython 3.11.15，R3/R4 review tests：55 passed，4 skipped（4 项均为 clean checkout 中明确排除的 analysis-only 资产）。

本轮按统计主编、计算生物学编辑、开放科学审稿人、数据审计员和 devil's advocate 五个角色复审。分数只依据当前可核验 artifact；作者运行结果、GitHub 招募和本轮 agent 评审不计作第三方验证。

## 1. 当前经验事实

| 证据层 | 已核验结果 | 正确边界 |
|---|---|---|
| 三实验室共同 target admission（T178） | 3 个 laboratory anchors、99 个共同 UniProt target、2,724 个共同 rank observations、47 个 measurement batches、20,469 个源单元格 | 开发集 source compatibility；不能把 pooled/technical source 当作独立 biological cohort |
| 严格 primary study-held-out route（T195/T217） | Dalian、UCD、Edinburgh 三个 anchor；9 个预冻结 target；809 observations；85 batches；3 个 outer folds；nested alpha、batch bootstrap、paired ablation、permutation negative control | exploratory portability sensitivity；donor-level independence 未完全解析 |
| 论文附带 biological cohort OOD（T180/T181） | 141 个 biological subject units、666 个合格 measurement batches、17,026 个 observations、34 个 shared target；full sequence subject-equal Spearman 0.06845，95% CI [0.05253, 0.08293]；paired increment 0.02928，95% CI [0.02413, 0.03451]；negative-control p=0.24125 | 作者运行 exploratory OOD；来自 Seer/Broad 单一 laboratory lineage，不是独立 evaluator 或跨实验室复制 |
| 论文附带 technical cross-core OOD（T194） | 12 个 core facilities、99 个 target、707 observations；core-cluster bootstrap、nested selection、paired ablation 和 permutation 已执行 | 同一 pooled aliquot 的技术域；不是 12 个 biological cohorts |
| source-by-model / missingness heterogeneity audit（T214） | 8 个 effect rows、5 个 primary effect units、2 positive、1 negative；8 个 qualification-threshold sensitivity rows；明确禁止跨非独立路线 pooling | 描述性异质性和缺失性敏感性已闭合；未声称 MNAR 已被识别或已完成校正 |
| 其他公开论文 OOD（T177/T203/T209/R3 silver） | 已有真实公开补充数据的模型、负对照、OOD 和不确定性输出，并按 license boundary 分为可再分发/analysis-only | 均为作者运行；不能替代 lockbox、无作者复现或 adoption |

## 2. 五角色评分

| 角色 | 分数 | 编辑判断 |
|---|---:|---|
| 统计主编 | 81 | estimand、study-held-out、nested selection、cluster uncertainty、T214 heterogeneity 和 missingness audit 已成体系；正式 MNAR 校正仍未声称 |
| 计算生物学编辑 | 84 | 已有真实模型、配对消融、负对照、多个 OOD 路线和有效样本报告；结果应定位为 portability benchmark，不是机制发现 |
| 开放科学审稿人 | 70 | 55 个测试通过、r10.23 immutable release、manifest、checksum 和公开复现路线齐全；第三方 receipt 仍为空 |
| 数据审计员 | 84 | 三实验室/99 target 的行级 provenance 已核验，141-subject cohort 已完成 cell-level audit，T214 route boundaries 已验证；biological lineage 边界仍需保守叙述 |
| Devil's advocate | 59 | 关键结果仍由作者运行；technical batch、pooled aliquot、donor identity 缺失和 source selection 可能影响泛化解释 |
| **保守综合** | **75** | **内部方法/软件证据接近投稿级，但强 Q1 硬门禁仍未关闭** |

## 3. 模块评分

| 模块 | 当前分数 | 结论与剩余缺口 |
|---|---:|---|
| 数据兼容性、许可与行级 provenance | **92** | 已达到“至少 3 个实验室共同真实 target”的开发集证据标准；仍需把 laboratory anchor 与 biological cohort 清楚分离 |
| 统计分析设计 | **90** | T217/T200/T195/T181/T214 已固定 primary role、study-held-out、nested、cluster、missingness、multiplicity 和描述性 source-by-model heterogeneity；正式 MNAR bounds/IPW 仍未声称 |
| 统计执行与有效样本 | **91** | T195、T181、T194 均有真实模型执行和 cluster uncertainty；donor-level effective n 仍不能对所有 primary route 宣称 |
| 模型、配对消融、负对照、OOD 与不确定性 | **91** | 真实 full/composition/constant baselines、paired ablation、permutation negative controls、多个 OOD 和 95% intervals 均存在；sequence 增量不稳定，不能写 universal superiority |
| 来源异质性与 claim discipline | **93** | T214 已保留正向、负向和 near-zero 路线，禁止不当 pooled inference，并区分 computational interval 与 biological uncertainty；仍需全文持续执行同一 claim audit |
| 工程审计与 locked-environment replay | **94** | KAUST CPython 3.11.15 下 55 passed/4 skipped；已绑定 source maps、reports、receipt 和 checksums |
| immutable public version binding | **92** | r10.23 tag、GitHub release、tarball、manifest、SHA-256 和 handoff 均齐全；归档 DOI 尚未返回 |
| 非作者 protected lockbox evaluator | **10** | 无真实非作者 evaluator receipt |
| 无作者 accession-to-result 科学复现 | **15** | PMC6592156 路线已公开招募；没有非作者独立下载、运行、环境 digest、输出 hash 和 signed receipt |
| 外部用户采用 | **0** | Issue #2 目前没有第三方回复、安装记录或真实任务 receipt |
| DOI / archive | **25** | DOI 投递包已准备，但没有可解析 DOI、archive locator 或归档服务 receipt |
| **强 Q1 综合成熟度** | **69** | 外部硬门禁具有不可替代性，不能由内部 90+ 模块抵消 |

## 4. 编辑决定

**Major Revision / Not Ready。** 当前可以按 computational methods、auditable benchmark、reproducibility/software 论文继续准备；不能按 biological mechanism、clinical utility 或独立生物学发现论文宣称。

```text
independent_validation = false
protected_lockbox_evaluator_receipt = false
external_scientific_reproduction = false
external_user_adoption = false
doi_archived = false
scientific_submission_ready = false
```

## 5. 使所有模块真正达到 90+ 的终止条件

1. 非作者 evaluator 在预先冻结协议下完成 protected lockbox aggregate receipt，并提供身份/COI、输入 hash、代码 commit、环境 digest、完整 stdout/stderr、输出 hash、失败记录和签名时间戳。
2. 非作者团队从 PMC6592156 supplementary endpoint 独立取得原始输入，按 r10.23 handoff 完成 accession-to-result 复现，报告偏差和阴性结果。
3. 两个非作者用户/机构在 clean environments 中完成不同真实任务，提交安装、日志、版本、输出 hash、限制和 COI 记录。
4. 将 donor/patient/sample 层级补到 primary route；不能补齐时，正式把 primary 结论降级为 source-conditional technical/portability audit。
5. 若正文要提出 source-by-model 的正式推断，需另行预注册 interaction estimand；当前 T214 仅支持描述性异质性。另可补充 MNAR/pattern-mixture/IPW 或可识别 bounds，但不得把现有 threshold sensitivity 写成 MNAR 识别。
6. 获得真实 DOI/archive receipt 后，以同一版本重新运行五角色复审；只有所有外部 predicates 和全部模块均达到 90+，才允许修改 `scientific_submission_ready=true`。
