# Decisions

## 2026-08-11 — T001 protected repository boundary

- Use LF-normalized text attributes and explicitly mark analytical databases, archives, documents, and raster images as binary.
- Ignore secrets, machine-local configuration, caches, virtual environments, raw/downloaded data, checkpoints, trained-model files, and transient experiment artifacts.
- Keep the execution contract, configuration examples/templates, curated registries, and reports eligible for tracking.
- The initial snapshot was left staged when both Git identity fields were unset; no identity was invented and no commit was claimed at that time.
- The blocker was resolved by the explicitly configured repository-local non-human identity `BioInterfaceOS-Codex <biointerfaceos-codex@localhost>`. Global Git configuration was not changed.

## 2026-08-11 — T003 minimal Python environment

- Keep the installable core free of runtime dependencies at T003 and lock it to the Python 3.11 minor series with uv; optional quality, data, modeling, and GPU packages enter only when their owning tasks require and validate them.
