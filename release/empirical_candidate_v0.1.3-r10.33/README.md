# BioInterfaceOS v0.1.3-r10.33

This immutable handoff overlay adds the current external-receipt preflight and
coordination metadata on top of the scientific candidate `v0.1.3-r10.32`.
The scientific candidate remains fixed at r10.32; r10.33 does not add or
promote scientific results.

The overlay binds the preflight to the r10.32 tag, manifest and KAUST archive,
updates the external handoff records, and records the current DOI preparation
metadata. It still contains no non-author lockbox receipt, no-author
reproduction receipt, external adoption receipt or DOI read-back.

```text
scientific_candidate = v0.1.3-r10.32
handoff_overlay       = v0.1.3-r10.33
scientific_submission_ready = false
```

The overlay is not evidence of external participation. Templates, public issue
comments, author-run executions and Codex/agent executions remain excluded from
all external gates.

Public release: https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.33
