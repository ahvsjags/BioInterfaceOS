# R4 T213：当前 release 指针一致性修订

日期：2026-08-14  
状态：`CANDIDATE_NOT_DOI_ARCHIVED`

T212 发布 r10.17 后，审计发现 `CITATION.cff` 和 README 的一个历史 manifest 入口仍指向 r10.16。该问题不改变任何数据、模型或 gate，但会使读者从当前代码得到不同的 release 入口。

本任务将 README、CITATION、release manifest、GitHub release、Issue #2 和 KAUST branch 统一到 `v0.1.3-r10.18`。r10.16 与 r10.17 均保持不可变，用作历史 release，不覆盖、不重写。

本次修订仍不改变：

```text
independent_validation = false
protected_lockbox_evaluator_receipt = false
external_scientific_reproduction = false
external_user_adoption = false
doi_archived = false
scientific_submission_ready = false
```

这是版本与引用入口修复，不是外部科学证据，也不是 DOI receipt。
