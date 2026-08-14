# R4-T234：固定 r10.28 的第三方执行 handoff addendum

日期：2026-08-14。该文件是面向非作者 evaluator、无作者复现团队和外部用户的执行入口。它不是 lockbox receipt、科学复现 receipt、采用 receipt 或 DOI receipt。

## 固定版本绑定

所有外部科学结论必须从 immutable tag 开始，不得从移动分支或作者工作区开始：

```text
repository=https://github.com/ahvsjags/BioInterfaceOS.git
tag=v0.1.3-r10.28
tag_target=5f72487023f80dd37d6b550b97638fb0246eb3fa
source_commit=b676433
release_manifest=release/empirical_candidate_v0.1.3-r10.28/release_manifest.json
release_manifest_sha256=4e35d6cbe8343e13419a28aca97b526e0e91c17ab297d1f6c33df6866bb7b6f4
external_protocol=docs/data/R4_T218_EXTERNAL_EVIDENCE_HANDOFF_PROTOCOL.json
external_protocol_sha256=3e51d49bb11fad58412e60980c158860e45647670f9a4a3a9de532bc92cc13a1
```

固定 checkout：

```bash
git clone --branch v0.1.3-r10.28 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
test "$(git rev-parse 'v0.1.3-r10.28^{}')" = "5f72487023f80dd37d6b550b97638fb0246eb3fa"
sha256sum release/empirical_candidate_v0.1.3-r10.28/release_manifest.json
uv sync --locked --all-groups
uv run pytest tests/review_round_3 tests/review_round_4 -q
```

## 无作者科学复现

推荐使用公开、可重获的 CC-BY-3.0 PMC6592156 silver-nanoparticle human-plasma supplementary route：

```bash
bash scripts/r4_external_reproduction.sh reports/external_reproduction/<participant_id>
```

该脚本会拒绝 dirty checkout，并逐项核对 `v0.1.3-r10.28` 的 tag target
`5f72487023f80dd37d6b550b97638fb0246eb3fa` 和 release manifest SHA-256
`4e35d6cbe8343e13419a28aca97b526e0e91c17ab297d1f6c33df6866bb7b6f4`；通过这些检查仍只表示复现输入固定，不能替代无作者团队的真实 receipt。

脚本会拒绝移动分支，独立重获输入，运行 source audit 与 external OOD，记录环境/依赖/输入/输出 hash，并保留失败和负结果。历史作者运行的计数只能作为比较信息，不能作为复现结果预填值。

复现 receipt 至少要包含：参与者身份与机构、非作者/无利益冲突声明、tag/commit、protocol 与 manifest hash、输入 accession 与下载 hash、环境 digest、完整命令、stdout/stderr hash、输出 hash、偏差与失败记录、签名声明和不可变归档定位。

## 非作者 lockbox evaluator

Evaluator 必须自行持有 protected held-out input 或 unseen real dataset；作者不得接触 row-level input、intermediate output 或调参反馈。Evaluator 只提交 aggregate receipt，至少包含：primary estimand、cluster-aware interval、effective n、paired composition ablation、within-batch permutation negative control 和 failure ledger。

下载量、GitHub star、issue view、作者/ Codex/KAUST 重跑和 GitHub Actions 都不能满足此门禁。

## 外部用户采用

需要两个不同的非作者用户或机构，在 clean environment 中安装固定 release 并完成不同的真实任务。每份 receipt 必须记录任务输入来源、命令、环境/依赖 digest、输出 hash、失败、限制和是否同意公开摘要。

## DOI/archive

归档服务必须返回固定 release 对应的 DOI、immutable record locator、上传后 manifest/tarball hash read-back。预先生成的 DOI metadata、GitHub release 或本地 tarball 不能替代 archive receipt。

## 当前公开证据边界

当前分支 `r3-real-data-execution-20260813` 的 T230–T233 仅记录作者侧论文/PRIDE 重筛、统计执行、来源边界和 negative results。T233 已证明 PXD026615 的 human-corona 文件组只有 5 个冻结共同 target；这些作者侧结果不会被升级为独立 validation。当前 `scientific_submission_ready` 仍为 `false`。

旧 GitHub Issue #2 只是历史协调请求，且正文绑定旧 r10.16 路线；它不是任何外部工作发生的证据。本 addendum 是当前 r10.28 执行协议的独立入口，不修改旧 issue。
