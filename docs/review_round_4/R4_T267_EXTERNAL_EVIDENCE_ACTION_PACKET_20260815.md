# R4-T267：外部证据行动包（v0.1.3-r10.50）

本文件定义当前 release 后仍未关闭的四个真实外部门禁。它是可执行 handoff，不是外部 receipt；作者本人、KAUST、本地重跑、CI、GitHub issue 和模板均不能计入以下证据。

## 需要的真实主体

| 门禁 | 最低证据 | 不计入 |
|---|---|---|
| 非作者 lockbox | 非作者 evaluator 在固定 tag 上运行 protected evaluator，并返回带身份、COI、命令、输出 hash、失败账本和签名的 receipt | 作者运行、KAUST运行、CI |
| 无作者科学复现 | 与作者无从属关系的团队从 accession/论文入口独立获取数据，运行 `v0.1.3-r10.50`，返回 accession-to-result crosswalk、输出 hash 和结论 | 作者预先生成的结果、只读论文 |
| 外部采用 | 两个不同外部用户在 fresh environment 安装并运行两个不同任务，返回安装日志、版本、命令、输出 hash、失败/修复记录和公开 issue/PR 或签名回执 | 作者本地安装、同一团队两次运行 |
| DOI read-back | 认证 archive 上传后返回 DOI、immutable record URL、manifest/archive bytes 与 SHA-256 read-back | Git tag、GitHub branch、KAUST 路径 |

## 固定绑定

- Git tag：`v0.1.3-r10.50`
- source commit：`07db8ceef9b785bc3fba0f79f346f9f633645a63`
- manifest：`release/empirical_candidate_v0.1.3-r10.50/release_manifest.json`
- T265 execution receipt：`reports/review_round_4/t265_biological_common_target/v1.0.0/t265_biological_common_target_receipt.json`
- T265 cross-environment receipt：`docs/review_round_4/R4_T265_CROSS_ENVIRONMENT_REPRODUCIBILITY_RECEIPT_20260815.json`

## Receipt 最低字段

```text
participant_id
affiliation_and_role
conflict_of_interest_statement
git_tag_and_commit
environment_fingerprint
commands_executed
input_accessions_or_public_entrypoints
output_paths_and_sha256
failure_ledger
conclusion
signed_attestation_or_immutable_public_locator
execution_timestamp_utc
```

## 当前门禁状态

```text
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

T265 已解决作者侧真实论文数据执行、共同 biological target、留一实验室、nested selection、负对照、消融、cluster uncertainty 和跨环境复现；它不能替代上表四类真实外部证据。
