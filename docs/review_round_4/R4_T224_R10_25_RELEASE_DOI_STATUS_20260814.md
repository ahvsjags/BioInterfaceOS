# R4-T224：r10.25 immutable release 与 DOI 状态

日期：2026-08-14  
状态：`CANDIDATE_NOT_DOI_ARCHIVED`

## 已完成的版本绑定

- GitHub tag：`v0.1.3-r10.25`
- release commit：`837be0631d4117ee3a1455de6743b411264a769a`
- source/provenance commit：`0b4e8e1eb0efe4b0dd690c3b77611309a34e7f6e`
- manifest：`release/empirical_candidate_v0.1.3-r10.25/release_manifest.json`
- manifest SHA-256：`37b0befc4dfe5a2b57f83bebf4b7e08cd9f7d87399499b3c8dc52d7a510cdd50`
- manifest accounting：2,638 个 source-commit tracked files；当前 release manifest 自身按约定排除 self-hash
- public tarball：`BioInterfaceOS-v0.1.3-r10.25.tar.gz`
- tarball：93,840,182 bytes
- tarball SHA-256：`4322cf39fa078b06c407d9dc81af12f438dea870cd7b1cc10730736f4b38b40e`
- GitHub release：[v0.1.3-r10.25](https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.25)

GitHub API 回读确认 tarball asset 状态为 `uploaded`，大小与 SHA-256 一致；KAUST clean checkout `/ibex/user/xup0a/BioInterfaceOS-r3-real-data-execution-20260814-clean` 已快进到 `837be06`，T222 strict verify 通过，新增测试为 `2 passed`。

## DOI 与外部证据状态

本次 release 只完成不可变版本、manifest、tarball、sidecar 和 handoff 绑定，没有产生 DOI/archive receipt。当前必须保持：

```text
independent_validation=false
protected_lockbox_evaluator_receipt=false
external_scientific_reproduction=false
external_user_adoption=false
doi_archived=false
scientific_submission_ready=false
```

GitHub release、作者控制的 KAUST replay、Codex 运行、下载计数和 Issue #2 招募请求都不能替代 DOI 服务返回的 record/version DOI，也不能替代非作者 evaluator、无作者复现或外部用户 receipt。

下一步 T225 仅接受外部产生的、可验证的身份/COI、输入或 protected-data attestation、环境 digest、命令、输出 hash、失败/负结果记录和签名 receipt；在这些证据到达前不修改任何 hard-gate 字段。
