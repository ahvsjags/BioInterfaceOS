# R4-T239：固定 release 与外部复现脚本一致性审计

日期：2026-08-14  
状态：`HANDOFF_CORRECTED_TAG_SCRIPT_BOUNDARY_EXPLICIT`

## 发现

R4-T234 的 handoff 绑定不可变 tag `v0.1.3-r10.28`，其 tag target 为：

```text
5f72487023f80dd37d6b550b97638fb0246eb3fa
```

后续 commit `6c4ac72` 在移动分支中给 `scripts/r4_external_reproduction.sh` 增加了：

- clean checkout 拒绝；
- tag target 校验；
- release manifest hash 校验。

但这些行不在 `v0.1.3-r10.28` 的脚本内容中。若第三方从 r10.28 checkout，直接运行 tag 内脚本，不能声称使用了 6c4ac72 的脚本防护。

## 修正

R4-T234 现在要求第三方在运行 r10.28 脚本前手动执行：

```bash
test -z "$(git status --porcelain)"
test "$(git rev-parse 'v0.1.3-r10.28^{}')" = "5f72487023f80dd37d6b550b97638fb0246eb3fa"
test "$(sha256sum release/empirical_candidate_v0.1.3-r10.28/release_manifest.json | awk '{print $1}')" = "1c939f964b97463dab4c5b0899df1f5deab92a7d8a7257d2a306f14f1f881491"
```

脚本加固 commit 仍保留在移动分支，供下一次 immutable release 采用；当前不把它回填成 r10.28 的证据。

## 结论

版本边界已纠正。R4-T239 不产生任何外部科学 receipt，也不改变 T238 的分数或 `scientific_submission_ready=false`；它只保证外部团队不会把 post-tag 工作树误当成固定 release。
