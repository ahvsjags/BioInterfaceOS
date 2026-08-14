# R4 T207：当前 r10.16 release 与 DOI deposit 状态

日期：2026-08-14。

## immutable release

- tag：`v0.1.3-r10.16`
- dereferenced commit：`82c5b218e98a65ec899ed8aac8def48896bfd288`
- GitHub release：<https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.16>
- release manifest：`release/empirical_candidate_v0.1.3-r10.16/release_manifest.json`
- manifest SHA-256：`2029f9566d57170ab10d098871e7397a89ab6dd26ff860cb961e878ea62d6635`

## current DOI deposit package

目录：`D:/Downloads/BioInterfaceOS/doi_deposit_v0.1.3-r10.16/`

- archive：`BioInterfaceOS-v0.1.3-r10.16.tar.gz`
- bytes：92,534,896
- archive SHA-256：`bbd5827d6a66dc047f68f5d2ed2ce43722555fde5db60b50e349f72fc22f40d9`
- sidecar、zenodo metadata 和 deposition manifest 均已更新为 r10.16/82c5b21，并通过本地 hash 对账。

## gate status

T207 已关闭“当前提交与 DOI 候选版本不一致”的本地准备问题。当前状态是 `DOI_DEPOSIT_PACKAGE_READY_NOT_ARCHIVED`：尚无 Zenodo/等价服务的 record locator、version DOI、归档 hash 或正式 archive receipt，因此 `doi_archived=false` 仍必须保持。

同样，`independent_validation=false`、`external_scientific_reproduction=false`、`external_user_adoption=false` 和 `scientific_submission_ready=false` 不因新 tag、GitHub release、KAUST verify 或 Codex 运行而改变。Issue #2 仍是招募请求，尚无非作者回复。
