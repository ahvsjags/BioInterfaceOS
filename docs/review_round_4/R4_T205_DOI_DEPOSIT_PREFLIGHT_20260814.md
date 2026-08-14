# R4 T205：不可变 release DOI deposit preflight

日期：2026-08-14。

## 当前不可变版本

- GitHub release：`v0.1.3-r10.15`
- tag dereferenced commit：`dd74814a762bbbd323c5432daaa8b9cc3e435ff5`
- GitHub release URL：<https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.15>
- release 状态：published、非 draft、非 prerelease；当前没有额外 release asset，GitHub source archive 以 tag 为准。

## 本地 deposit package

package 目录：`D:/Downloads/BioInterfaceOS/doi_deposit_v0.1.3-r10.15/`

- archive：`BioInterfaceOS-v0.1.3-r10.15.tar.gz`
- archive bytes：92,384,282
- archive SHA-256：`1ec081789fea4f3406fbb8b7000fd2e1618d07606bbbccf8c09355d451ad5ef3`
- source release manifest SHA-256：`b2cfb34e4fbe2bf64df829e2a64a885f92453a5d79b3dbc080d7f0aaa204706b`
- metadata：`zenodo.json`
- deposit manifest：`deposition_manifest.json`

hash 已由 archive `.sha256` 文件和 deposition manifest 双重记录。`zenodo.json` 明确使用 software deposit、Apache-2.0、tag URL 和探索性证据边界。

## 门禁状态

`DOI_DEPOSIT_PACKAGE_READY_NOT_ARCHIVED`。目前没有 Zenodo/等价服务返回的 record locator、version DOI、归档文件 hash 或不可变 archive receipt，因此 `doi_archived=false` 仍然是正确状态。GitHub tag/release 不能替代 DOI。

完成该门禁只需要在授权 Zenodo 账户中上传 archive 与 metadata，随后把以下返回值写回新的 receipt 并重新核对：record URL、version DOI、archived bytes、archive SHA-256、tag/commit 和 manifest SHA-256。不得在 receipt 返回前填写 DOI 或把 deposit package 写成已归档。
