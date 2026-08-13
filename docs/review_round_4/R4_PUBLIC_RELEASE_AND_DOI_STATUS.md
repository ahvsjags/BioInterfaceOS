# R4 公共仓库、版本与 DOI 状态

**状态：`PUBLIC_VERSION_RELEASED_DOI_PENDING`**  
**更新时间：2026-08-13**

## 已完成

- 公开仓库：[https://github.com/ahvsjags/BioInterfaceOS](https://github.com/ahvsjags/BioInterfaceOS)
- 默认分支：`main`
- 执行分支：`r3-real-data-execution-20260813`
- GitHub 版本标签：`v0.1.2-r5`
- GitHub release：[BioInterfaceOS v0.1.2-r5](https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.2-r5)
- R4 数据与 cluster 审计冻结 commit：`1407cf2ad631d55e0b26abf5d0b5e82aad676bf3`
- R5 handoff metadata commit：`4bbf0a9`
- KAUST 服务器任务路径：`/ibex/user/xup0a/BioInterfaceOS-r3-real-data`
- KAUST 服务器路径：`/ibex/user/xup0a/BioInterfaceOS-r3-real-data`；当前状态以服务器分支 `r3-real-data-execution-20260813` 的 HEAD 为准

公开仓库只包含已提交的代码、协议、审计报告、receipt 和已纳入版本控制的公开资产。工作区中未跟踪的临时下载、缓存和候选原始文件没有被推送。

## DOI 门禁

当前 DOI 状态为 `PENDING_NOT_ARCHIVED`。GitHub release 是可追溯版本，但不是 DOI，也不能替代 DOI 归档 receipt。只有在 Zenodo 或其他归档服务返回不可变 DOI、存档版本和内容 hash 后，才允许把 `doi_status` 改成 `ARCHIVED_VERIFIED`，并更新 `CITATION.cff` 与 release manifest。

## 科学证据门禁

该公共 release 不改变以下状态：

- `independent_validation=false`
- `external_scientific_reproduction=false`
- `scientific_submission_ready=false`

公开仓库和版本 release 解决了版本可追溯与独立安装的基础设施问题，但尚未产生非作者 lockbox receipt、非作者端到端复现 receipt 或真实外部用户采用记录。
