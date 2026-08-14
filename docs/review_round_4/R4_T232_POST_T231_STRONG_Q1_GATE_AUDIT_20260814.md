# R4-T232：T231 后强 Q1 门禁复核

日期：2026-08-14。审计对象：固定 release `v0.1.3-r10.28`、作者侧 KAUST 执行、T230/T231 公开论文数据重筛、当前 external-evidence handoff 协议，以及本地 review-round 3/4 回归结果。

## 判定

T231 增加了真实公开数据的文件级重建和负结果证据，但没有把任何不兼容来源强行纳入 primary endpoint。当前项目已不再是 protocol/software-only：作者侧已有真实 proteomics、study-held-out/nested/cluster-aware 统计、模型、配对消融、negative control、OOD 和不确定性结果；然而强 Q1 的四个外部硬门禁仍未被真实第三方 artifact 关闭。

`scientific_submission_ready=false` 保持不变。

## 当前模块评分

| 模块 | 当前分数 | T232 判定 | 仍需的证据 |
| --- | ---: | --- | --- |
| 数据兼容性与来源可审计性 | 94 | 已达到 | 对跨实验室 biological independence 继续保守表述；T231 候选不得补入 primary |
| 统计分析设计 | 90+ | 已达到 | 外部 receipt 绑定后做最终编辑复核 |
| 统计执行与有效样本 | 90+ | 已达到（作者/KAUST） | 不得把作者 replay 升级为独立验证 |
| 模型、消融、负对照、OOD、不确定性 | 90+ | 已达到（作者/KAUST） | 最终稿中继续区分 author-run 与 external |
| 非作者 protected lockbox | 10 | 未达到 | 1 个非作者 evaluator、protected held-out input、aggregate signed receipt |
| 无作者科学复现 | 15 | 工程路径已备、科学证据未达 | 1 个无作者团队重新获取公开输入并提交不可变 receipt |
| 外部用户采用 | 0 | 未达到 | 2 个不同非作者用户/机构、不同真实任务、环境和输出 hash |
| 版本 DOI/archive | 25 | 只完成准备 | 真实归档服务返回 DOI、immutable record 和 hash read-back |
| 强 Q1 strict composite | 70 | 未通过 | 四个外部门禁真实验证后重新编辑复审 |

## T231 对数据门禁的具体影响

- `PXD032162` 已从公开 repository 文件重建出 723,192 行 QuantSpectra、16 个 raw-file 标识和 300 个蛋白 accession，但冻结 target 交集为 8，80 个 mix/channel group 中没有一个达到至少 10-target batch 门槛。因此它固定为 `SENSITIVITY_ONLY_NOT_ADMITTED`。
- `PXD020584` 的全文样本语义得到确认：healthy subjects 20、RA patients 17；differential-centrifugation 分析为 HS 12、RA 10。但它是 EV protein-corona endpoint，54 个 XLSX 的 451-protein union / 39-target union 不是同尺度共同 observation matrix，因此固定为 `DOMAIN_OOD_ONLY_PENDING`。
- PXD028310、PXD050779、PXD053359 的低覆盖、pooled 或 proteoform-only 边界已记录；它们没有增加 effective n 或 independent-lab common-target 数。

这些负结果是有效的审计证据，但不能被反向计入“已获得三独立实验室 biological common target”。

## 当前回归与完整性证据

| 检查 | 结果 |
| --- | --- |
| `tests/review_round_4` | 53 passed |
| `tests/review_round_3 tests/review_round_4` | 62 passed |
| T231 JSON 解析 | 通过 |
| T231 commit diff check | 通过 |
| 当前提交 | `79d804e12d3ab6c59c1b25ea0cab79949b3f4a5f` |
| GitHub 分支 | `r3-real-data-execution-20260813` |
| KAUST 任务分支 | `r4-paper-data-fallback-20260814` |

本地测试证明的是固定代码和作者可访问数据路径的工程可复现性，不是第三方科学复现或独立 validation。

## 下一轮唯一有效闭环

1. 按 `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json` 将固定 release 交给真实非作者 lockbox evaluator，并接收 protected-input aggregate receipt。
2. 由另一真实非作者团队独立重新获取公开 accession/full-text 输入，执行固定命令并提交带环境、命令、输出 hash、偏差和归档定位的 reproduction receipt。
3. 取得两个不同非作者用户/机构的真实安装与任务 adoption receipt。
4. 将固定 release 归档至真实 DOI 服务，回读 DOI、immutable record 和上传后 hash。
5. 只有 1–4 全部 verified 后，才运行最终多智能体编辑复审并更新 `scientific_submission_ready`。

在上述 artifact 出现前，继续扩大作者侧论文数据筛查不会诚实地把 lockbox、复现、采用或 DOI 分数提高到 90；当前目标保持 active。

## 门禁状态

```text
author_side_real_data_execution=true
paper_fulltext_pride_rescreened=true
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```
