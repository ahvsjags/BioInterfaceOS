# R4-T199：强 Q1 投稿门槛闭环目标

日期：2026-08-14。该目标把“拿不到内部真实实验数据”改写为可复核的公开论文数据、原始输入起步和外部证据闭环，不把技术重复、汇总表或作者自证当作独立 biological n。

## 已关闭的本地执行项

1. PMC7376165 CC-BY-4.0 141-subject cohort：T180/T181 已完成源审计、真实模型、paired ablation、cluster bootstrap 和 OOD；T198 补齐阈值/缺失敏感性及 selection-aware negative control。
2. Edinburgh、Dalian、UCD 三个可再分发 source maps：T192/T193/T194/T195 已完成共同 target、nested selection、study-held-out、cluster uncertainty 和 core-facility sensitivity；T197 补齐 development-only target membership。
3. Manchester 另一研究团队的全文/作者公开矩阵：T185/T186 已完成 61 个 patient clusters、289 个 longitudinal batches、4,169 个 external observations 的真实 author-run OOD，并使用每次置换重新选择 alpha。
4. 当前版本已包含代码、协议、receipt、manifest、GitHub tag/release 和 KAUST clean-checkout 验证路径。

## 仍必须由真实外部主体关闭的门禁

- 非作者、预先看不到答案的 protected lockbox evaluator receipt；
- 无作者参与、从原始输入开始的完整科学复现 receipt；
- 至少两个可核验外部用户/团队的独立安装、运行或 issue/PR/采用记录；
- Zenodo/等 DOI 归档与 immutable release 关联；
- 上述证据进入新一轮多智能体 editor review，并把 `scientific_submission_ready` 从 false 改为 true。

在这些外部事实真正发生前，项目的正确结论仍是 Major Revision，而不是“稳投强 Q1”。

