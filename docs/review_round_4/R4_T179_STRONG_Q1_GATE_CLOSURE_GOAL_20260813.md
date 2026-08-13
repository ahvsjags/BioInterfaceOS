# R4 T179 强 Q1 Gate-Closure 改进目标

**建立日期：** 2026-08-13
**状态：** `IN_PROGRESS`
**总目标：** 在不伪造实验、第三方身份、用户采用、独立结果或 DOI 的前提下，把 BioInterfaceOS 推进到可以稳投强 Q1 方法/计算生物学期刊的证据状态。只有所有硬门槛都有可审计 receipt，才允许 `scientific_submission_ready=true`。

## 当前基线与 90+ 出口

| 模块 | 当前保守分 | 90+ 出口条件 | 必须产生的证据 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 78 | 至少 3 个实验室、至少 2 个独立生物学 lineage；每个 source 有 donor/biological-unit、材料、批次和行级定位；共同 target 在分析前冻结 | 外部来源 registry、源文件 SHA-256、source-cell map、common-target ledger、独立单位核验 receipt |
| 统计分析设计 | 84 | estimand、primary endpoint、nested selection、cluster 层级、missingness、multiplicity、失败/负结果规则在解封前固定 | protocol SHA-256、analysis-freeze manifest、变更日志和预注册时间戳 |
| 统计执行与有效样本 | 62 | 用真实数据执行完整 primary endpoint；报告 biological unit/lab/batch/target 有效 n、排除项和完整 CI；不能以 pooled technical batch 代替 biological n | raw prediction archive、effective-n table、cluster-aware CI、missingness sensitivity 和失败清单 |
| 模型、消融与 OOD | 57 | full、composition-only、simple/constant baseline、paired ablation、负对照、study-held-out/OOD 和 uncertainty 全部由冻结配置运行；主要指标和最小效应阈值达到预设标准 | 模型配置 hash、预测表、消融差值及 CI、negative-control receipt、OOD/uncertainty report |
| 独立 protected lockbox | 4 | 非作者 evaluator 持有作者不可见的输入；一次性运行；作者只收到 aggregate receipt；失败和负结果完整记录 | evaluator 身份/COI、protected-input attestation、代码/容器/lockfile/input/output hash、签名 receipt |
| 无作者端到端科学复现 | 0 | 非作者团队从固定 tag clean checkout，重新取得原始输入并无作者调参完成全流程；复现偏差和失败均公开 | checkout/environment/commands/logs/output hash、deviation ledger、不可变归档 locator |
| 外部用户采用 | 25（接入准备度；实际采用仍为 0） | 至少 2 个不同机构的非作者用户完成不同任务，并提交含环境、版本、输出 hash、失败与局限的 adoption receipt | 两份独立 user/adoption receipt、issue/PR 或项目记录；下载量/star 不计入 |
| 公开 release 与 DOI | GitHub 可追溯；DOI pending | 固定 release、内容 manifest、Zenodo/等价档案服务不可变 DOI 和版本 hash 完成核验 | DOI/archive receipt、release manifest、CITATION.cff、版本一致性审计 |

严格综合当前仍为 `30/100`，`scientific_submission_ready=false`。T178 已关闭“三个 CC-BY 来源是否形成共同 development target”的资产审计，但没有关闭 biological independence、lockbox、无作者复现、外部采用或 DOI。

## T179 分阶段工作包

### T179-A：生物学独立性与真实 target

1. 继续从全文、补充材料和官方公共仓库筛选可重新获取的真实 human-biointerface/protein-corona 数据。
2. 只接收明确 license/permission、accession、原始或作者结果文件、样本/批次设计、材料协变量和 target mapping 的来源。
3. 不把 pooled aliquot、技术 core、重复测量或论文中的汇总均值当作 donor-level biological n。
4. 在候选源审计完成后冻结 biological unit、common target、batch 纳入、zero/blank/NA 和缺失机制；未达标的候选保持 `HOLD/REJECTED`。

### T179-B：真实模型与统计执行

1. 复用冻结的 source-local rank estimand，不跨研究合并 raw abundance scale。
2. 在所有 admitted development/OOD source 上输出 full、composition-only、simple rank 和 constant baseline。
3. 以 batch、target、laboratory、biological unit 分层报告有效 n，并预先指定 cluster bootstrap、permutation、multiplicity 和停止/失败规则。
4. 如果 full model 不超过 baseline 或 CI 跨过无效区间，记录为负结果并修改论文定位；不得通过改 endpoint、删失败批次或事后调参制造 90 分。

### T179-C：外部 lockbox 与无作者复现

1. 向非作者 evaluator 提供 `R4_T166_EXTERNAL_EVALUATOR_AND_REPRODUCTION_PROTOCOL.json`、固定 release 和一次性受保护输入；作者不接触 row-level input/intermediate output。
2. 同时邀请第二个无作者控制团队做 clean-checkout scientific reproduction；接受失败和偏差记录。
3. 使用 `R4_T172_EXTERNAL_RECEIPT_BUNDLE_TEMPLATE.json` 做结构预检，但把结构预检与真实身份、独立性、科学结论分开；预检成功不等于 gate 通过。

### T179-D：外部采用、DOI 与最终复评

1. 在公开 issue/handoff 中收集至少两份真实外部使用记录；作者控制的 Codex agent、作者自测、自动下载、GitHub page view 和 star 不计入。
2. 由 Zenodo 或等价档案服务实际产生不可变 DOI，并核对存档版本、release manifest 和内容 SHA-256。
3. 由五个编辑角色（EIC、方法学、领域、可复现性/视角、Devil's Advocate）重新评分；每个模块和严格综合均必须至少 90。
4. 在最后一个外部 receipt 通过独立身份/范围/科学审计前，所有 `independent_validation`、`external_scientific_reproduction`、`community_adopted` 和 `scientific_submission_ready` 保持 `false`。

## 当前可执行命令

```bash
cd /ibex/user/xup0a/BioInterfaceOS-r3-real-data
uv sync --locked --all-groups
uv run pytest -q tests/review_round_3 tests/review_round_4
uv run biointerfaceos data verify-r4-three-lab-common-target --strict

## T180/T181 实施更新

T180/T181 已把“真实数据拿不到”转化为一条可复核的论文数据路线：复用 PMC7376165 的 CC-BY-4.0 Supplementary Data 5，冻结 141 个 individual plasma subjects、705 个 NP-corona batches、34 个冻结 target 子集，并在 141 个 biological-unit clusters 上执行真实模型、成对消融、不确定性和负对照。结果为 full sequence ridge 的 subject-equal mean Spearman `0.06845`（95% cluster CI `[0.05253, 0.08293]`），composition-only `0.03917`（`[0.02132, 0.05493]`），paired delta `0.02928`（`[0.02413, 0.03451]`），negative-control upper-tail `p=0.24125`。

该进展将“统计执行与有效样本”从仅有 technical/pool evidence 提高为有 141 个 biological-unit 的可运行 cohort evidence，也使模型/OOD 结果有更完整的有效 n 和 cluster-aware CI。但它仍来自 Seer/Broad 同一 laboratory anchor，结果仍为 author-run exploratory；负对照不显著、sequence 增量较小，不能升级为确认性机制结论。因此 T180/T181 不关闭 protected lockbox、非作者独立 evaluator、无作者科学复现、外部采用、版本 DOI 或 `scientific_submission_ready`。
uv run biointerfaceos data verify-r4-pmc13106918-source --assets-root data/raw/r4_candidate_pmc13106918 --strict
uv run biointerfaceos data verify-r4-pmc13106918-technical-ood --strict
```

这些命令目前可以证明公开代码、T178 三实验室开发资产和 T177 作者运行 technical OOD 的可复核性；它们不能伪造或替代 T179-C/D 的外部事实。若外部 receipt 在投稿前仍未到达，稿件必须降级为方法/软件/可审计 benchmark，不能声称强 Q1 生物学发现或独立验证。
