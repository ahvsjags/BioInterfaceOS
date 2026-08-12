# T112 Build reproducibility containers and clean-room package

## Result

T112 was completed on the KAUST Ibex server at implementation commit `f9d97b1`.
The project now has a deterministic clean-room workflow, an offline container
entrypoint, a license-aware public-file allowlist, and three independent
reproduction receipts. The package excludes lockbox payloads, raw/CAS data,
credentials, secrets, and model payloads.

## Reproducible command

```bash
make reproduce-clean
```

Observed first run:

```text
CLEAN_ROOM_VALID repro_id=bioif-clean-room-v1.0.0 package_sha256=dc795d0e62e420e77cb9e219f50b3f418f3bdd9950c17ae5ebe17757b6512eb3 result_hash=6bc746911560fcef206ea2f54783fb05f62ff26673a86fd7056b7da82095bb7d runs=3 tests_passed=32 network_accessed=false protected_values_read=false
```

A second invocation was rejected before overwrite:

```text
CLEAN_ROOM_INVALID: clean-room package already executed; overwrite refused
```

## Clean-room boundary

The public archive is built from an explicit allowlist containing committed
source, schemas, fixtures, tests, release metadata, lockbox metadata-only
receipts, final publication figures/tables, and license manifests. It explicitly
excludes `data/locked_test`, `data/raw`, `data/cas`, credentials, secrets, and
model payloads. Bronze license metadata was checked: allowed/derived assets are
redistributable and restricted assets remain pointer-only.

The container definition uses `uv sync --frozen --offline --no-dev`; the runtime
entrypoint runs the benchmark/catalog/manifest/lockbox subset with `--offline`.
Three independent runs each passed 32 tests and agreed on the package and
result hashes.

## Acceptance evidence

| Gate | Result |
|---|---|
| Focused clean-room tests | 5 passed |
| Full test suite | 380 passed |
| Static checks | ruff, format check, mypy, compileall, and `git diff --check` passed |
| Environment | `uv lock --check` and frozen `uv sync` passed |
| Repository checks | schema, assets, catalog, lockbox, release, and state passed |
| Offline benchmark | 32 tests passed on each of 3 independent runs |
| Reproduction agreement | package SHA and result hash identical across all receipts |
| License boundary | license manifest bound to bronze manifest; restricted pointer payload excluded |
| Network boundary | network false; offline uv/pytest commands; protected values read false |
| Immutability | second clean-room run rejected; verify checks archive and receipts |

## Artifacts

- Schema: `agents/reproducibility/clean_room.v1.json` (SHA-256 `8573f7ff939a828578611159daab23a92b0814097601a3690c9be3c2275bf4e6`)
- Fixture: `tests/fixtures/reproducibility/clean_room_fixture.json` (SHA-256 `56de913b0b85f1434ef005f51cf207617c8191a696c0dc0962b5b81dfe09637c`)
- Workflow: `src/biointerfaceos/clean_room_workflow.py` (SHA-256 `73529459f87f0f5f2f752f961d873da74c72562fa658615bd51baeef1a1d209b`)
- Container: `containers/clean-room.Dockerfile` (SHA-256 `11e53bddd2d081141e722d6c6726d3eccd0fc0530c1012a3b9f5d07c870e2b20`)
- Runtime entrypoint: `containers/clean-room-run.sh` (SHA-256 `135f79822c8521a54c562eb0fdd3b28a782967ba3cc3553d9b244a7ab963e8c6`)
- Tests: `tests/reproducibility/test_clean_room_workflow.py` (SHA-256 `8c5992c890b4232a665494eca584d8e133b7014bc4cfcac4bfcfb367688344d1`)
- Public package: `reports/reproducibility/clean-room-v1.0.0/public_package.tar.gz` (SHA-256 `dc795d0e62e420e77cb9e219f50b3f418f3bdd9950c17ae5ebe17757b6512eb3`)
- Package manifest: `reports/reproducibility/clean-room-v1.0.0/package_manifest.json` (SHA-256 `2014bfe65a2b2149714fb5df181347415c122daa722377146bc3d57f6189ef3c`)
- Reproduction report: `reports/reproducibility/clean-room-v1.0.0/reproduction_report.json` (SHA-256 `f855e9a3210aa6ff56bf9263fb52635a69f323f1715a390fa1ffbd8d322fa8e8`)
- Receipts: `runs/run_1/receipt.json` `4f09caa2e22b18fa5701f7eb4884d484fbf7f00216717869a39aef3788ec0c2b`; `runs/run_2/receipt.json` `5ab914164a870e797a6934bb48ad3c3dbaaebb58478f8fabe410da7a2b1820d6`; `runs/run_3/receipt.json` `f5708162e08f340af19bc04ef3ec576fb93ecbd393d4b94713d13cf99145be23`
- Implementation commit: `f9d97b1`

## Limitations and rebuild steps

- Raw or restricted-pointer data must be rebuilt from the original licensed
  source locator under the source policy and is intentionally not copied here.
- A caller supplying an offline uv wheelhouse can build the container; the
  Dockerfile never contacts a package index.
- The package reproduces the redistributable benchmark and metadata-only main
  results; it does not expose protected lockbox values.

The next task is T113: run the manuscript claim-to-evidence and language audit.
