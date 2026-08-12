# Container replay recipes

`r2-software-replay.Dockerfile` packages the R2 public-source replay only. It
rebuilds the three field-mapped protocol diagrams from their tracked specs and
checks their hashes, semantic boundaries and geometry. It does not include
`data/`, `registry/`, `reports/`, `release/`, any manuscript payload, or any
claim of scientific reproduction.

The image deliberately requires a caller-supplied, lockfile-matching
`wheelhouse/`; the source archive does not redistribute third-party wheels.
Build and run it without network access:

```bash
docker build --network=none -f containers/r2-software-replay.Dockerfile -t bioif-r2-replay .
docker run --rm --network=none -v "$PWD/reports:/workspace/BioInterfaceOS/reports" bioif-r2-replay
```

For a local replay using the locked environment, run:

```bash
python -m biointerfaceos reproduce release --strict
```

The resulting receipt states `software_replay=true`,
`scientific_reproduction=false`, and `scientific_submission_ready=false`.
