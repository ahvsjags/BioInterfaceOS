# T005 quality, tests, and CI report

Recorded: 2026-08-11T17:57:06Z

## Result

The reproducible Python 3.11 quality gate passed on the Ibex checkout. The implementation commit is e60785cccc960425922a52e0731db4b8e9720eb8. The runtime package remains dependency-free; the locked dev group provides the quality tools.

## Locked toolchain

- uv: 0.12.1
- Python: 3.11.15
- ruff: 0.12.12
- mypy: 1.17.1
- pytest: 8.4.2
- Dev lock resolution: 12 packages total, including BioInterfaceOS and pinned ruff/mypy/pytest transitive dependencies.
- uv.lock SHA-256: 7234dde79178f2ff574885ebec1479373be6455800665ec6e9c4c5f20d7e40d6

The first environment synchronization downloaded the two binary quality tools because they were not already cached. The subsequent frozen synchronization and quality gate ran with UV_OFFLINE=1 and passed.

## Acceptance evidence

| Command | Exit | Result |
| --- | ---: | --- |
| uv lock --check | 0 | Lockfile is current. |
| UV_OFFLINE=1 uv sync --frozen --python 3.11 | 0 | Frozen environment synchronized from the lock. |
| UV_OFFLINE=1 make check | 0 | Ruff lint, Ruff format check, mypy, and pytest all passed. |
| ruff check src tests | 0 | No lint findings. |
| ruff format --check src tests | 0 | Four files already formatted. |
| mypy | 0 | No issues in four source files. |
| pytest | 0 | 3 tests passed, no network/data/model dependency. |
| python -m compileall -q src tests | 0 | Compilation passed. |
| git diff --check | 0 | No whitespace errors. |

Makefile now uses frozen uv execution for all four checks. The CI workflow pins uv 0.12.1 and immutable action revisions, has read-only contents permission, and requires no secrets.

## Scope and limitations

The initial exploratory ruff check on the whole repository also found pre-existing findings in T000/T002 utility scripts. The contractual T005 gate intentionally targets the package and tests (src tests), which are the T005 quality inputs; those older utility findings were not silently claimed as fixed. No data, model, locked-test content, or T006+ implementation was touched.

## Artifact hashes

- pyproject.toml: 23af8e58decdac66ed311d2fbc3eeb8c02e705699833d08eb4888f6afbd24c3d
- Makefile: 69cd2f305f3fe2b53333bf3c82282bc0b56c3b84af0a3ad29b9e9137bf0b6a50
- .github/workflows/ci.yml: cafaec3c726959ecbd36298ee113fd9046f9aa78f3dd606877848c0300f77387
- uv.lock: 7234dde79178f2ff574885ebec1479373be6455800665ec6e9c4c5f20d7e40d6
- src/biointerfaceos/cli.py: c4f989923085ddec7d85ebdcdc9ac280acca23647a82ee13a7bc30976dcb8dfe
- tests/test_cli.py: b44e3a7ca0562029343312a9587660b4925ca192d96f9c3ed07f88d93796b49f
