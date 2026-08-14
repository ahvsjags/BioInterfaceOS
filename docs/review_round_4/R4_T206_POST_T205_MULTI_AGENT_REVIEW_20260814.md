# R4 T206：T205 后多智能体门禁复审

日期：2026-08-14。评审基线为 T205 完成后的当前工作树（提交 8f9f894）；随后新增的 r10.16 release assembly 只改变版本绑定和公开文档，不改变 T195/T197/T198/T200/T203 的数值结果。三位 agent 分别承担统计、计算生物学编辑、复现/出版完整性角色。

## 分数共识

| 模块 | 复审分数 | 判断 |
|---|---:|---|
| 数据兼容性、共同 target 与追溯 | 83–85 | 三实验室 route 真实覆盖 9 个严格共同 target、85 batches；T203 另有 97 targets/45 biological units，但只是一篇新论文、作者运行且 CC-BY-NC-ND |
| 统计设计与泄漏控制 | 88 | 冻结 target、nested selection、study-held-out、cluster uncertainty、missingness 与 multiplicity 设计较强 |
| 统计执行与有效样本 | 82 | T195/T197/T198/T200/T203 receipts 均可 verify；不能将 row count 当成独立 biological n |
| 模型、消融与 OOD | 80 | 真实模型、配对消融、cluster bootstrap、置换负对照和 paper OOD 已执行；仍非独立验证 |
| Biological novelty | 38 | 当前是 portability/OOD 方法证据，不是机制、因果或正交实验发现 |
| 跨实验室泛化 | 35 | 3-lab common-target 仍受 pooled/technical unit 与 donor-ID 语义限制 |
| Protected lockbox | 10 | 无非作者 evaluator receipt |
| No-author scientific reproduction | 5 | 无无作者端到端 receipt |
| 外部用户采用 | 0 | Issue 只有作者方招募评论，无外部回复或采用 receipt |
| DOI 归档 | 20 | v0.1.3-r10.15 package hash 已核验，但尚无 archive locator/DOI；且它不绑定当前 8f9f894 |
| 公开发布完整性 | 78 | GitHub release、公开仓库、外部 handoff 已有；当前版本绑定正在通过 r10.16 修复 |
| Claim discipline | 88–92 | 当前明确不把作者运行 paper OOD、KAUST、GitHub 或 Codex 当成外部验证 |

技术模块综合约 84/100；严格强 Q1 出版成熟度约 58/100。结论保持：`NOT_READY / MAJOR_REVISION`，不能设置 `scientific_submission_ready=true`。

## T205 的作用与未解决项

T205 证明了旧的 v0.1.3-r10.15 DOI deposit archive（92,384,282 bytes；SHA-256 `1ec081789fea4f3406fbb8b7000fd2e1618d07606bbbccf8c09355d451ad5ef3`）内部一致，但复审发现它绑定旧 tag/commit，不是当前工作树。该问题进入 T207：建立 r10.16 tag、重新生成 archive/manifest 和 DOI deposit metadata，再以新版本作为最终归档候选。

Issue #2 的公开招募只属于外部协调请求，不是 lockbox、no-author reproduction 或 adoption receipt。当前所有独立性硬门禁继续为 false。
