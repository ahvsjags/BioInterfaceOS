# T004 CLI doctor report

Date: 2026-08-11

## Result

The dependency-light CLI foundation passed its mandatory acceptance checks under CPython 3.11.15. The installed `biointerfaceos doctor --strict` command reported zero mandatory failures. It reported the absent optional tools as `WARN` and every future command family as `NOT_IMPLEMENTED`; none was claimed as functional.

## Command evidence

| Command | Exit | Observed result |
| --- | ---: | --- |
| `uv lock --check` | 0 | Lock resolved consistently with one editable package. |
| `make env` | 0 | Frozen sync installed `biointerfaceos==0.1.0`; uv emitted only its cross-filesystem hardlink fallback warning. |
| `.venv/bin/biointerfaceos doctor --strict` | 0 | Python, repository, seven files, 17 top-level skeleton directories, and package import passed; mandatory failures: 0. |
| `.venv/bin/biointerfaceos --version` | 0 | Printed `0.1.0`. |
| `.venv/bin/python -m biointerfaceos --version` | 0 | Printed `0.1.0`. |
| `.venv/bin/python -m unittest -v tests.test_cli` | 0 | 3 tests passed. |
| `.venv/bin/python -m compileall -q src/biointerfaceos tests/test_cli.py` | 0 | Compilation completed without output. |
| `git diff --check` | 0 | No whitespace errors. |

`uv lock` was run before `uv lock --check`. The console entry point changes installation metadata but adds no resolved dependency, so `uv.lock` remained byte-for-byte unchanged with SHA-256 `1a0983851f8aa9c7b5995edd430faa4b157174ca187291ef08f0e5f83c680b4a`.

## Honest quality-tool status

The intentionally minimal T003/T004 environment does not install pytest, ruff, or mypy. Each probe (`.venv/bin/python -m pytest --version`, `.venv/bin/python -m ruff --version`, and `.venv/bin/python -m mypy --version`) exited 1 with `No module named ...`. These checks are absent, not passes; their installation and configuration belongs to T005.

## Scope

No optional large package was installed, no data or model was downloaded, no locked-test content was inspected, and no T005-or-later capability was implemented.

## Artifact hashes

- `pyproject.toml`: `49d8da41b9d44a0bd7c65d072d0fd2056a02cd42ea57824a1788e63d08df41bd`
- `src/biointerfaceos/cli.py`: `72a2c3e062761706f9cc049918ecbc679c15467c3da16cb14c0dfd712daf0ef6`
- `tests/test_cli.py`: `b44e3a7ca0562029343312a9587660b4925ca192d96f9c3ed07f88d93796b49f`
