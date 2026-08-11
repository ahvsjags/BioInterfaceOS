"""Minimal module entry point for the T003 version smoke test."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from biointerfaceos import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """Print package metadata without implementing the T004 command surface."""
    parser = argparse.ArgumentParser(prog="python -m biointerfaceos")
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
