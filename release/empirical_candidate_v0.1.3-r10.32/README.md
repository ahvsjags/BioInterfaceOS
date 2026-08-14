# BioInterfaceOS v0.1.3-r10.32

This immutable correction overlay supersedes r10.31 for repository-state
consistency. It records the completed T226/T227/T228 paper-data execution work
while keeping T225 external lockbox, no-author reproduction, adoption and DOI
receipts explicitly in progress.

The overlay remains exploratory. It does not claim four independent biological
cohorts, non-author lockbox validation, no-author reproduction, external
adoption or DOI archival. The paper-data route uses source-local ranks and
retains the technical-batch and donor-resolution boundaries.

To verify from a clean checkout:

```bash
git clone --branch v0.1.3-r10.32 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
sha256sum release/empirical_candidate_v0.1.3-r10.32/release_manifest.json
python scripts/validate_execution_pack.py
python -m biointerfaceos data verify-r4-t249-four-lab-common-target --strict
python -m biointerfaceos data verify-r4-t250-four-lab-common-target --strict
```

The manifest's `base_release` must be verified against immutable r10.31 before
external work begins. DOI status remains `PENDING_NOT_ARCHIVED` until an
authenticated archive service returns a persistent DOI read-back.
