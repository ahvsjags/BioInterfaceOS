# R2 public software-replay release

Run `python -m biointerfaceos reproduce release --strict` from a clean checkout
to create an immutable R2 replay record at
`reports/review_round_2/reproducibility/r2_software_replay/v1.6.0/`.

The record contains a default-deny public-source manifest, SHA-256 file hashes,
a CycloneDX-style SBOM derived from `pyproject.toml` and `uv.lock`, a deterministic
source archive, a clean temporary-worktree replay receipt, and a JUnit-style
result. The clean replay executes the public CLI from the copied public source
and rebuilds all three R2 protocol figures.

The package includes only registry-approved `PUBLIC` assets. It fails closed if
a data payload, source registry, historical report, historical release, or
unregistered asset enters the scope. Historical fixture bundles and manuscript
outputs remain quarantined.

This is **software replay only**. It is **not scientific replication**, **not
empirical validation**, and cannot by itself support submission-ready scientific
claims. Real-data provenance, pre-specified statistics, benchmarks, model runs,
and independent evaluation remain mandatory later gates.
