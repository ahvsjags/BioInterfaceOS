# Public handoff update — v0.1.3-r10.35

The current external-reproduction helper is available in the immutable
handoff overlay:

- Release: https://github.com/ahvsjags/BioInterfaceOS/releases/tag/v0.1.3-r10.35
- Scientific candidate: `v0.1.3-r10.32`
- Helper: `scripts/r4_external_reproduction_r10_32.sh`
- Current handoff: `docs/external/INDEPENDENT_REPRODUCTION_AND_USER_HANDOFF_R10_34.md`
- Coordination issue: https://github.com/ahvsjags/BioInterfaceOS/issues/2

The helper is intentionally downloaded outside a clean r10.32 checkout. It
records its own hash, requires the exact r10.32 tag and manifest, reacquires
the public paper-data route, preserves failed/negative runs and emits hashes
for a T218 receipt. This is an executable route, not evidence that an external
team has run it.
