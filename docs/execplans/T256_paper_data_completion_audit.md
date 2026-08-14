# T256：论文全文数据替代与投稿证据闭环

状态：`COMPLETED_INTERNAL_EXTERNAL_GATES_UNVERIFIED`  
日期：2026-08-14

## 目标

在无法新增湿实验样本的前提下，使用已发表论文全文、补充材料和公共 ProteomeXchange/PRIDE accession，构建可追溯、可重算、按证据等级分层的真实实验数据路线，并逐条审计其对强 Q1 投稿门槛的贡献。

## 已完成的内部工作

- 固定 T238 四来源 source-held-out 主路线，不把论文报告的样本数直接当作模型有效样本；
- 保留 T249 四来源/七个严格共同 target 的 source-cell provenance；
- 将 T203、T209、T246、T177 和候选 PRIDE 来源分为 OOD、technical sensitivity 或排除层；
- 对 T238 执行 nested selection、paired ablation、selection-reexecuted permutation null；
- 通过 T255 增加 measurement-batch cluster bootstrap 95% CI；
- 形成逐条要求审计和机器可读状态文件；
- 固定公开复核入口为 `v0.1.3-r10.43`；commit 以 release tag read-back 为准。

## 外部未完成门槛

以下项目不能由作者继续下载论文或自己重跑来替代：

1. 非作者 protected lockbox evaluator receipt；
2. 无作者参与的 accession-to-result scientific reproduction receipt；
3. 两个非作者用户/机构的独立安装与实际使用记录；
4. DOI/immutable archive deposit 和 manifest read-back hash；
5. 上述证据到齐后的五角色编辑复评。

## 验收条件

本执行目标只有在以下条件同时满足时才允许关闭为 submission-ready：

- 所有主分析和 OOD artifact 的 hash 与固定 release 一致；
- 所有第三方 receipt 记录 identity、COI、环境、命令、输出 hash、失败运行和签名 attestation；
- 最终编辑复评中数据兼容性、统计设计、统计执行、模型/OOD、lockbox、复现、采用和归档模块均不低于 90；
- `scientific_submission_ready=true` 由可审计 receipt 共同支持，而不是由作者端状态文件单方面设置。

## 当前判定

论文数据路线已足以支持 methods/benchmark/reproducibility resource 定位；在外部 receipt 到达前，强 Q1 scientific submission gate 继续保持 `false`。

权威审计：`docs/review_round_4/R4_T256_REQUIREMENT_BY_REQUIREMENT_COMPLETION_AUDIT_20260814.md`。
