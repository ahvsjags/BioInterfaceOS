# BioInterfaceOS v0.1.3-r10.29

This is an immutable paper-data evidence overlay for the BioInterfaceOS
empirical candidate release. It is anchored to the public `v0.1.3-r10.28`
manifest and adds the byte-verified PMC11328176 multicore source, the audited
PMC9047655 candidate screen, the T246 execution script, model outputs and the
T246/T247 editorial evidence.

The overlay is not a DOI archive and does not claim independent validation,
no-author reproduction, external adoption or submission readiness. The
PMC11328176 route is a technical core-facility sensitivity analysis on one
common prepared material; it is not six independent biological cohorts.

To verify the overlay from a clean checkout:

```bash
git clone --branch v0.1.3-r10.29 --depth 1 https://github.com/ahvsjags/BioInterfaceOS.git
cd BioInterfaceOS
sha256sum release/empirical_candidate_v0.1.3-r10.29/release_manifest.json
python scripts/validate_execution_pack.py
```

The manifest's `base_release` must also be verified against the immutable
r10.28 manifest before external work begins.
