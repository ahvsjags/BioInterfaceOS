# Public release inventory and boundary

The authoritative machine-readable inventory is [`PUBLIC_ASSET_REGISTRY.json`](PUBLIC_ASSET_REGISTRY.json). The strict audit expands its glob rules to every Git-tracked path, hashes each asset, rejects unregistered or multiply matched paths, and writes an append-only receipt under the round-two public-release audit report directory.

| Asset group | Distribution decision | Rights / source decision | Evidence boundary |
| --- | --- | --- | --- |
| Repository-authored source, tests, containers, configurations and documentation | `PUBLIC` | `Apache-2.0`; see [LICENSE](../../LICENSE) and [NOTICE](../../NOTICE) | Software and protocol only |
| `registry/` source metadata | `CONTROLLED` | `NOASSERTION` until row-level provenance and source license checks pass | Source metadata only |
| `data/` and fixture payloads | `EXCLUDED` | `NOASSERTION`; no redistribution assumption | Fixture only |
| `reports/` and historical `release/` artifacts | `EXCLUDED` | Historical record retained for audit, not relicensed | Quarantined historical output |

`release/public/bioif-public-v1.0.0` remains available only as a historical audit object. It is **not** a current public data release, a scientific replication, or empirical validation. The current public scope is **software replay only**.

Run:

```bash
python -m biointerfaceos release audit-public --strict
```

before creating any new public bundle. A passing asset audit does not satisfy the real-data, independent-evaluation, or scientific-reproduction gates in `docs/review_round_2/ACCEPTANCE_GATES.yaml`.
