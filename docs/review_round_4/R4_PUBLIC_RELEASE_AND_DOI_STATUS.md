# R4 公共仓库、版本与 DOI 状态

**状态：`PUBLIC_VERSION_RELEASED_DOI_PENDING`**  
**更新时间：2026-08-15**

## 已完成

- 公开仓库：[https://github.com/ahvsjags/BioInterfaceOS](https://github.com/ahvsjags/BioInterfaceOS)
- 默认分支：`main`
- 执行分支：`r3-real-data-execution-20260813`
- 当前固定科学标签：`v0.1.3-r10.57`
- 固定标签目标：`3557fac2019e57fd8968cdcf55b106750eafa750`
- 当前协调分支：`r3-real-data-execution-20260813`（最新 handoff overlay commit `f129208`）
- KAUST 服务器任务路径：`/ibex/user/xup0a/BioInterfaceOS-r4-paper-data-fallback-20260814`
- KAUST r10.57 archive：`release_assets_r10.57/BioInterfaceOS-v0.1.3-r10.57.tar.gz`

公开仓库只包含已提交的代码、协议、审计报告、receipt 和已纳入版本控制的公开资产。工作区中未跟踪的临时下载、缓存和候选原始文件没有被推送。

## DOI 门禁

当前 DOI 状态为 `PENDING_NOT_ARCHIVED`。固定 Git tag 和 KAUST archive 已准备完成，但尚无认证 DOI。GitHub tag 或服务器 archive 都不是 DOI，也不能替代 DOI 归档 receipt。只有在 Zenodo 或其他归档服务返回不可变 DOI、存档版本和内容 hash 后，才允许把 `doi_status` 改成 `ARCHIVED_VERIFIED`，并把 DOI read-back 绑定到 `CITATION.cff` 与 release manifest。

## 科学证据门禁

该公共 release 不改变以下状态：

- `independent_validation=false`
- `protected_lockbox_evaluator_receipt=false`
- `external_scientific_reproduction=false`
- `external_user_adoption=false`
- `doi_archived=false`
- `scientific_submission_ready=false`

公开仓库、固定 tag、版本 manifest、KAUST archive 和独立安装路径已准备完成，但尚未产生非作者 lockbox receipt、非作者端到端复现 receipt、真实外部用户采用记录或认证 DOI read-back。
