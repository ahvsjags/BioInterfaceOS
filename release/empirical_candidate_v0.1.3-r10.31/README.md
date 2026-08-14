# BioInterfaceOS v0.1.3-r10.31

This immutable correction overlay supersedes r10.30 for cross-platform paper-data
audit reproducibility. It normalizes the PMC6592156 derived source map to LF
bytes and rebinds the source audit, T249 common-target registry, and T250
execution receipts without changing the scientific observations or model fits.

The overlay remains exploratory. It does not claim four independent biological
cohorts, non-author lockbox validation, no-author reproduction, external
adoption or DOI archival. The paper-data route uses source-local ranks and
retains the technical-batch and donor-resolution boundaries.

To verify from a clean checkout:

```bash
git clone --branch v0.1.3-r10.31 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
sha256sum release/empirical_candidate_v0.1.3-r10.31/release_manifest.json
python scripts/validate_execution_pack.py
python -m biointerfaceos data verify-r4-t249-four-lab-common-target --strict
python -m biointerfaceos data verify-r4-t250-four-lab-common-target --strict
```

The manifest's `base_release` must be verified against immutable r10.30 before
external work begins. DOI status remains `PENDING_NOT_ARCHIVED` until an
authenticated archive service returns a persistent DOI read-back.
