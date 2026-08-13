# R4 T184 — PNNL full-text source acquisition and boundary

状态：`SCREENED_NOT_ADMITTED`。

这轮把“通过论文全文拿不到真实数据”的问题做成了可核验的来源审计。PMC3252235 的论文和官方补充表已经实际下载到 KAUST R3 工作树对应的原始候选目录；补充表 `S. Table 6` 包含 24 个纳米颗粒/时间实验条件和论文报告的 88 个定量人血浆蛋白。

审计结果不能把它加入冻结的 R3 主 OOD：补充表中的 24 个测量列在当前 99 个冻结 target 中每列只有 2 个直接重合蛋白（P04004、P06396），没有一列达到预注册的每批次至少 10 个正值 target。因此，修改 target universe 或降低阈值来接纳这个来源会构成查看数据后的事后改协议。

该补充表还没有明确的可再分发许可。PMC 全文可公开阅读不等于 XLS 资产自动获得 CC-BY/CC0；所以原始 XLS 留在分析服务器的候选目录，不进入公开 release，也不产生公开数据集声明。它同时不提供 donor-level independent biological units；论文明确把时间点样本描述为 process replicates，不能替代 141 个 biological units。

机器可核验记录：

- 注册与决定：[R4_T184_PMC3252235_SOURCE_SCREEN.json](/D:/Downloads/BioInterfaceOS/kaust_t118_worktree/docs/data/R4_T184_PMC3252235_SOURCE_SCREEN.json)
- 原始候选文件：`data/raw/r4_candidate_pmc3252235_NIHMS344183/NIHMS344183-supplement-Supp_Tables_pow.xls`
- 字节数：`6,702,592`
- SHA-256：`d9e4563eba493c7bb57f0ae9783af4c8ded9889bb64d1706899d6d65caf87284`

结论是“真实全文数据已获取，但该来源不能诚实地升级为主 OOD/独立验证”。当前可公开使用的实证路线仍是 CC-BY/CC0 的已审计来源、141-subject biological-cohort OOD，以及外部 evaluator/reproduction/adoption 的真实 receipt；后者不能由论文表格替代。
