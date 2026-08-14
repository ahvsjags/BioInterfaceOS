# R4-T266：immutable release 与 DOI 门禁状态

日期：2026-08-15

## 已完成

- GitHub immutable tag：`v0.1.3-r10.50`
- tag 对应 source commit：`07db8ceef9b785bc3fba0f79f346f9f633645a63`
- hash-bound manifest：`release/empirical_candidate_v0.1.3-r10.50/release_manifest.json`
- manifest：593,268 bytes；SHA-256 `84ec1f65b6589b23d6ef4d10e8a468904b0ff55067dff092d61693f73c46c597`
- DOI deposit metadata：`docs/release/R10_50_DOI_DEPOSIT_METADATA.json`

## 尚未完成

当前没有经过认证的 archive upload、DOI、immutable record URL 或 read-back SHA-256 receipt。因此：

```text
doi_archived=false
scientific_submission_ready=false
```

该版本已经足以供外部 evaluator、复现团队和用户安装；但版本标签和 KAUST 归档不能被当作 DOI 证据。外部 lockbox、无作者复现和外部采用门禁同样保持关闭，直到真实非作者主体返回带身份、COI、命令、输出 hash 和失败账本的 receipt。
