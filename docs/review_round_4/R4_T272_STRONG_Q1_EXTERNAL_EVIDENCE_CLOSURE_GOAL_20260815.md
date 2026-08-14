# R4-T272：strong-Q1 外部证据闭环改进目标

## 目标声明

在不伪造真实数据、独立身份、外部用户或 DOI 的前提下，把 BioInterfaceOS 从“作者侧 paper-derived execution + handoff package”推进到可审计的 strong-Q1 投稿候选：

1. 统计主 estimand、target freeze、inner selection、negative control、paired ablation、missingness 和 CI 在同一 biological-unit 层级闭合；
2. 取得至少一个非作者 protected-data lockbox receipt；
3. 取得至少一个无作者参与、从原始公开输入起步的 scientific reproduction receipt；
4. 取得至少两个来自不同外部用户/机构的真实安装与采用 receipt；
5. 完成 r10.52 archive 的 authenticated DOI upload 和 manifest/archive read-back；
6. 重新通过五角色编辑终审，并让所有公开 claims 与证据边界一致。

## 当前基线与目标

| 模块 | 当前严格分数 | 目标 | 关闭条件 |
|---|---:|---:|---|
| 数据兼容性与样本基础 | 78 | ≥90 | ≥3 独立 biological cohorts；donor/unit 可解析；共同 target 行级 provenance；许可与再分发闭合 |
| 统计分析设计 | 84 | ≥90 | primary biological-unit estimand；fold-local target freeze；unit-grouped inner selection；selection-aware null |
| 统计执行与有效样本 | 75 | ≥90 | 主结果、CI、null、ablation 同层级；UCD replicate 计权预注册并重算；coverage/missingness sensitivity；end-to-end regression |
| 模型、消融与 OOD | 55 | ≥90 | Spearman、MAE、RMSE paired inference；practical margin；负 OOD 结果完整报告；不能宣称 universal superiority |
| 独立评估 / lockbox | 0 | ≥90 | ≥1 非作者、protected input、一次性 evaluator receipt + identity/COI/签名/immutable locator |
| 外部科学复现 | 0 | ≥90 | ≥1 无作者参与团队，从原始公开输入开始，fresh environment、命令、hash、偏差和失败记录完整 |
| 外部用户可用性与采用 | 0 | ≥90 | ≥2 不同外部用户/机构、不同真实任务、清洁环境、可核验输出和 consented summary |
| DOI / 公开 release | 10 | ≥90 | DOI、immutable URL、archive receipt、manifest/archive exact read-back；CITATION 与 tag 一致 |

## 工作包与不可替代证据

### T272-A：统计 estimand repair

- 将 biological-unit grouped split 用于 inner selection，或明确降级 biological-unit claim；
- 对 T250 UCD technical replicates 预先定义 collapse/weighting；
- 同时重算 primary metric、cluster CI、permutation null、paired Spearman/MAE/RMSE；
- 输出 canonical v2 protocol、effective-n/coverage flow、negative-run ledger 与 end-to-end regression receipt。

验收：统计编辑能从 protocol 直接追溯到每个主结果，不需要用 secondary artifact 修补 primary estimand。

### T272-B：非作者 lockbox

- evaluator 控制 protected input 和一次性执行；
- 作者不能预先获得 row-level input、intermediate predictions 或答案；
- receipt 至少包含身份、COI、固定 release、环境、命令、stdout/stderr hash、输出 hash、偏差、负结果和 immutable locator。

验收：`verified_lockbox_receipt_count >= 1`，且 identity/independence audit 通过。

### T272-C：无作者科学复现

- 固定 `v0.1.3-r10.52`，使用 `scripts/r4_external_reproduction_r10_52.sh`；
- 由无作者参与团队从公开原始输入开始，在新环境运行 T250；
- 独立保存环境指纹、依赖 lock hash、输入/输出 hash、失败和偏差记录。

验收：`verified_no_author_reproduction_count >= 1`。作者控制的 KAUST clean-room 只能作为候选演练，不能计入该数量。

### T272-D：外部用户采用

- 至少两个不同机构或独立项目；
- 任务必须是真实 downstream use，不是 page view、star、模板或 fixture-only；
- 记录安装、版本、环境、输入 provenance、stdout/stderr、输出 hash、限制和 consent。

验收：`verified_distinct_adoption_receipt_count >= 2`。

### T272-E：DOI authenticated read-back

- 上传 r10.52 archive、sidecar、hash-bound manifest 和 deposit metadata；
- 记录 archive service DOI、immutable record URL、版本 DOI、上传时间；
- 从服务端回读 manifest/archive bytes，并与 `R10_52_DOI_DEPOSIT_METADATA.json` 完全比对；
- 只有回读成功才允许把 `doi_archived` 改为 `true`。

验收：`doi_archive_verified == true`，且不能仅凭 GitHub tag 或 KAUST 路径关闭 DOI 门禁。

## 强制 claim boundary

在 T272 全部关闭前，正文只能声称：BioInterfaceOS 提供 provenance-grounded、可审计的分析框架，并在 paper-derived/source-mapped 数据上完成作者侧 source-conditional portability 与异质性审计。

禁止声称：四个独立 biological cohorts 已验证、sequence features 带来普遍增益、机制或临床 utility 已验证、已有独立 lockbox、已有无作者复现、已有社区采用或已经 strong-Q1 ready。

## 最终 gate predicate

```text
scientific_submission_ready =
  verified_lockbox_receipt_count >= 1
  AND verified_no_author_reproduction_count >= 1
  AND verified_distinct_adoption_receipt_count >= 2
  AND doi_archive_verified == true
  AND statistics_estimand_consistent == true
  AND final_multi_agent_editorial_review == PASS
```

任何一项缺失时，状态保持 `scientific_submission_ready=false`，投稿决策为 `Major Revision / 暂缓投稿`。

