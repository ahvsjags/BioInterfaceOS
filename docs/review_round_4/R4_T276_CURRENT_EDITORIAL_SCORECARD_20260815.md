# R4-T276：当前编辑审稿状态卡（2026-08-15）

## 结论

论文全文与公开补充材料路线已经把项目从“没有可执行真实结果”推进到“有固定 common-target panel、作者侧 nested/cluster-aware 执行和跨环境字节一致性”。这不是独立实验室验证，也不是外部复现。按编辑审稿的硬门禁，当前仍是 Major Revision，不能声称 strong-Q1 ready。

## 模块评分

| 模块 | 当前分数 | 已有证据 | 仍缺的投稿级证据 |
|---|---:|---|---|
| 数据兼容性与样本基础 | 78 | T273 固定 5-target panel；Seer/Broad、Tianjin、Manchester 共 3 个 laboratory route；paper-derived ledger、coverage flow 和许可证边界 | 可再分发且行级可追溯的跨实验室共同 target 仍需权利闭合；需要第三方/原始数据持有人确认；不能把 paper-derived route 写成作者独立采样 |
| 统计分析设计 | 91 | biological-unit primary estimand、grouped inner selection、leave-one-lab-out、cluster-aware bootstrap、selection-aware permutation null、缺失/coverage 规则 | 需要把最终冻结的 protocol 与投稿版本、lockbox 输入和审稿后修订逐项绑定 |
| 统计执行与有效样本 | 91 | T273 本地/KAUST verify 通过；3853 observations、5 targets、3 laboratories、916 qualified measurement batches、246 biological units；T274 coverage sensitivity 已执行 | technical replicate 的 replicate-aware model refit 尚未执行；当前 T275 仅为 post-fit endpoint sensitivity |
| 模型、消融与 OOD 证据 | 72 | full/composition paired ablation、negative control、OOD/coverage 相关 author-side artifacts；T273 中 full-minus-composition rank gain 为 0 | 需要真实外部 evaluator、预注册的模型/消融/OOD 结论和独立输入起步的结果；当前不能宣称 sequence-specific incremental value |
| 非作者 lockbox | 0 | evaluator protocol、输入/输出契约和 handoff package 已准备 | 至少 1 个非作者 evaluator 的一次性 receipt，包含输入 hash、执行环境、输出 hash 和签名/时间戳 |
| 无作者参与的科学复现 | 0 | clean-room 脚本、固定 release、source reacquisition 说明已准备 | 至少 1 个无作者参与团队从原始输入开始的完整复现报告；作者只能核验 receipt，不能代执行 |
| 外部用户采用 | 0 | GitHub branch、安装/验证脚本和版本化文档 | 至少 2 个独立外部用户或团队的可验证安装/运行记录，以及 issue/PR 或公开使用记录 |
| DOI 与版本可引用性 | 10 | r10.52 archive metadata 与 manifest 已存在 | DOI deposit 成功、API/read-back 返回同一版本与 checksum；当前 `doi_archived=false` |

八项分数的简单平均约为 42.8/100；但投稿决策不是平均分机制，lockbox、无作者复现和外部采用为硬门禁，因此不能用统计模块的高分抵消三个 0 分模块。

## 论文全文数据路线的正确定位

T250/T265/T273 使用的是公开论文全文、补充表格和可追溯 source ledger 衍生的真实测量数据。它们可以支持方法可执行性、common-target 兼容性、有效样本定义、cluster-aware 统计和作者侧重放；在许可证允许范围内可以作为 analysis-only evidence。它们不能替代：

1. 未参与项目设计和执行的 evaluator 的 lockbox；
2. 无作者参与团队从原始输入开始的科学复现；
3. 原始实验室/数据持有人对样本语义、权利和共同 target 的独立确认；
4. 外部用户真实安装、运行和采用记录。

## 进入 strong-Q1 投递门的必要条件

全部条件必须同时满足，而不是继续提高作者侧统计分数：

1. 完成 replicate-aware refit，冻结 primary estimand、effective n、missingness 和 coverage policy，并把结果写入最终 manuscript/table/figure。
2. 获得至少 1 份非作者 lockbox receipt、至少 1 份无作者参与复现 receipt、至少 2 份独立外部采用记录。
3. 完成 DOI deposit 和 authenticated read-back，确认 DOI 版本、release manifest、source code 和 checksum 一致。
4. 重新运行 5-agent editorial re-review；只有当上述硬门禁全部通过，且数据、执行、模型/OOD、外部证据各模块均达到 90 分以上，才把 `scientific_submission_ready` 改为 `true`。

当前门禁仍为 `scientific_submission_ready=false`。
