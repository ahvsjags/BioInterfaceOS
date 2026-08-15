# R4-T287 author-controlled clean-room path check — 2026-08-15

## Result

The fixed public tag `v0.1.3-r10.57` was cloned into a fresh KAUST directory and executed from the release helper:

- repository: `https://github.com/ahvsjags/BioInterfaceOS.git`
- tag: `v0.1.3-r10.57`
- checked-out commit: `3557fac2019e57fd8968cdcf55b106750eafa750`
- environment: Python `3.9.18`, uv `0.12.1` on Linux x86_64
- T250 strict verification: valid (`observations=783`, `targets=7`, `laboratories=4`, `measurement_batches=115`, `models=3`)
- T250 execution test: `1 passed in 10.31s`
- dependency lock check: passed

The execution bundle is at:

`/ibex/user/xup0a/BioInterfaceOS-r10.57-cleanroom-check-20260815/external_run`

Its output hashes are recorded in `output_hashes.txt`; the helper-script SHA-256 is `b0bde9373bafadcfae5a5b3555b2eac466c30f69ff548c36180f119718a67dd4`.

## Evidence boundary

This is an author-controlled KAUST path check. It verifies that a fresh checkout can install and execute the public route, but it is **not** a no-author scientific reproduction, lockbox receipt or external adoption receipt. The external gate counters and `scientific_submission_ready` remain false.
