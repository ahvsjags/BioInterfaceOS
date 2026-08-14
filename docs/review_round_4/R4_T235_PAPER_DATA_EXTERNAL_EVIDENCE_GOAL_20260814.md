# R4-T235：论文数据替代路线与外部证据闭环目标

日期：2026-08-14  
目标对象：固定 release `v0.1.3-r10.28`、三来源公开论文/仓储数据、外部 handoff 协议 `R4-T218` 与当前强 Q1 门禁。

## 目标

在无法自行获得新的湿实验数据时，使用可公开获取、可核验的论文全文/补充表/ProteomeXchange 数据完成 BioInterfaceOS 的计算生物学验证；同时把作者侧公开数据重分析与真正的第三方证据严格分层，最终只在真实外部 artifact 完整后把项目推进到 `scientific_submission_ready=true`。

论文数据可以提供真实观测、跨来源共同 target、study-held-out 统计、模型/消融/OOD 和不确定性证据；它不能凭作者侧运行自动产生非作者 lockbox、无作者复现、外部采用或 DOI 归档证据。

## 已完成且允许进入论文的作者侧证据

### 三来源共同 target 主路线

固定输入为：

- Edinburgh DataShare DS7545，University of Edinburgh-led study，CC-BY-4.0；
- PRIDE PXD060795，Dalian University of Technology，CC0；
- PRIDE PXD064962，University College Dublin / Conway Institute，CC0。

三来源严格交集冻结为 9 个 canonical accession：

`P04004`, `P04264`, `P05556`, `P06396`, `P07996`, `P26038`, `P60174`, `Q04695`, `Q9HDC9`。

T192/T193/T195 已记录 809 行可追溯共同观测、85 个 measurement batches、3 个 leave-one-laboratory-anchor-out folds，并执行 nested batch selection、cluster bootstrap、full/composition-only/constant 模型、配对消融和 within-batch rank-permutation negative control。

允许的论文措辞是：

> 在三个独立来源实验室的公开蛋白组数据上，BioInterfaceOS 对冻结共同 target 的跨来源 rank portability 呈现探索性信号；不将其表述为三组独立 donor-level biological cohorts、湿实验复制或独立验证。

以下边界必须原样保留：Dalian 是 pooled/unspecified plasma；Edinburgh 当前 source map 未编码 donor ID；UCD 的 replicate columns 是技术重复，不能扩大 effective biological n。

### 论文全文与开放仓储候选的负结果

T230/T231/T233 的筛查和 mzIdentML 重处理是有效的排除证据：候选来源若缺乏 source-matched numeric covariate、共同定量 endpoint、足够 target 覆盖或一致 biological unit 语义，必须保留为 sensitivity/OOD/negative-result evidence，不能强行加入 primary endpoint。

## 当前门禁基线

| 模块 | 当前判断 | 目标 |
| --- | --- | ---: |
| 数据兼容性与来源可审计性 | 公开三来源共同 target 已完成，生物学边界仍需保守表述 | >=90 |
| 统计设计 | estimand、nested selection、study-held-out、cluster uncertainty 已冻结 | >=90 |
| 统计执行与有效样本 | T193/T195 已由作者侧执行并留有 receipt | >=90 |
| 模型、消融、负对照、OOD、不确定性 | 已有作者侧真实公开数据执行 | >=90 |
| 非作者 protected lockbox | 尚无真实 evaluator receipt | >=90 |
| 无作者科学复现 | 脚本和固定 release 已准备，尚无外部团队 receipt | >=90 |
| 外部用户采用 | 尚无两个非作者真实任务 receipt | >=90 |
| DOI/archive | manifest 已准备，尚无真实归档返回值和 hash read-back | >=90 |
| 强 Q1 综合 | 保持 `scientific_submission_ready=false` | >=90 |

## 新一轮工作包

1. **固定论文数据主路线**：只使用 T192/T193/T195 作为公开数据 exploratory primary route；把所有新增全文候选登记为 sensitivity、OOD 或 negative result，禁止事后按性能挑 target。
2. **冻结外部输入与代码**：第三方只接受 `v0.1.3-r10.28`、release manifest、T218 protocol 和可再分发 source maps；作者不得读取 lockbox 的行级输入或中间结果。
3. **非作者 lockbox**：由无利益冲突 evaluator 一次性执行 frozen release，提交 environment digest、input attestation、aggregate estimand、effective n、paired ablation、negative control、failure ledger 和签名 receipt。
4. **无作者复现**：外部团队从 clean checkout 独立重新获取 PMC/PRIDE/论文补充数据，执行 `scripts/r4_external_reproduction.sh` 或等价固定命令，保留失败日志、偏差说明和输出 hash。
5. **外部采用**：至少两个不同非作者用户/机构在不同真实任务和干净环境中安装并运行，记录输入来源、输出 hash、失败与限制，并取得公开摘要同意。
6. **归档与 DOI**：把通过门禁的固定 release 和许可边界提交真实归档服务，回读 DOI、immutable record locator 与上传后 hash；准备包不算 DOI 证据。
7. **工程质量门禁**：修复当前 GitHub Actions 的 Ruff 失败后，再执行完整 `make check`；不得通过放宽质量门禁来制造绿色状态。
8. **最终编辑复审**：只有四项外部谓词全部 verified，才重新评分并允许将 `scientific_submission_ready` 置为 true。

## 禁止的替代

- 不把论文 measurement batch 当作 donor-level biological replicate；
- 不把作者/KAUST/Codex replay 当作 external evaluator 或 no-author reproduction；
- 不用空 receipt、模板、公开链接、GitHub branch 或 DOI 准备包代替真实第三方 artifact；
- 不在看到外部数据或外部结果后更换 primary endpoint、target 或 stopping rule；
- 不隐藏低覆盖、失败、负对照或跨来源异质性结果。

## 退出条件

当且仅当 T218 的 lockbox、no-author reproduction、两份 adoption receipt 和真实 DOI archive 全部完成，且最终多智能体编辑复审的每个模块均达到 90/100 以上，才允许将：

```text
scientific_submission_ready=true
```

在此之前项目状态保持 `active`，论文定位为“公开论文/仓储数据上的可审计计算验证与跨来源探索性 benchmark”，不宣称独立湿实验验证。

## 权威证据入口

- `docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json`
- `docs/data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_REGISTRY.json`
- `docs/review_round_4/R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_STATUS_20260814.md`
- `docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json`
- `docs/external/R4_T234_FIXED_RELEASE_EXTERNAL_HANDOFF_20260814.md`
- `release/empirical_candidate_v0.1.3-r10.28/release_manifest.json`
