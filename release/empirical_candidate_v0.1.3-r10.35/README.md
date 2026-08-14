# BioInterfaceOS v0.1.3-r10.35

This immutable handoff overlay adds the current clean-room reproduction helper
for the scientific candidate `v0.1.3-r10.32`.

The helper is downloaded outside a clean r10.32 checkout and invoked from that
checkout. It verifies the exact tag and r10.32 manifest, independently
reacquires the public paper-data route, records environment and output hashes,
and preserves failures and negative runs. It does not create a non-author
receipt or promote `scientific_submission_ready`.

```text
scientific_candidate = v0.1.3-r10.32
handoff_overlay       = v0.1.3-r10.35
scientific_submission_ready = false
```

Public release: https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.35
