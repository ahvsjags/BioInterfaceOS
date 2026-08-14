"""Rebuildable DuckDB catalog backed by authoritative Parquet registries."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from biointerfaceos.assets import INDEX_PATH
from biointerfaceos.manifest import MANIFEST_PATH
from biointerfaceos.policy import REJECTION_PATH

CATALOG_PATH = Path("registry/catalog.duckdb")
SCHEMA_VERSION = 1
INPUTS: Mapping[str, Path] = {
    "source_manifest": MANIFEST_PATH,
    "asset_index": INDEX_PATH,
    "rejected_sources": REJECTION_PATH,
}


class CatalogError(RuntimeError):
    """Raised when the derived catalog cannot be safely built or checked."""


@dataclass(frozen=True)
class CatalogSummary:
    """Catalog counts and schema version."""

    schema_version: int
    source_rows: int
    asset_rows: int
    rejection_rows: int
    join_rows: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, candidate: Path) -> Path:
    repository = root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    if resolved != repository and repository not in resolved.parents:
        raise CatalogError(f"path escapes repository: {candidate}")
    if "locked_test" in resolved.parts:
        raise CatalogError("locked-test paths are forbidden")
    return resolved


class Catalog:
    """A versioned, Parquet-backed DuckDB query layer."""

    def __init__(self, root: Path, database_path: Path | str = CATALOG_PATH) -> None:
        self.root = root.resolve(strict=True)
        candidate = Path(database_path)
        self.database_path = _contained(
            self.root,
            candidate if candidate.is_absolute() else self.root / candidate,
        )
        if self.database_path == self.root:
            raise CatalogError("catalog database cannot be repository root")
        self.inputs = {
            name: _contained(
                self.root,
                path if path.is_absolute() else self.root / path,
            )
            for name, path in INPUTS.items()
        }

    def _require_inputs(self) -> None:
        for name, path in self.inputs.items():
            if not path.is_file():
                raise CatalogError(f"authoritative Parquet input is missing: {name} at {path}")

    def _sql_path(self, path: Path) -> str:
        return path.as_posix().replace("'", "''")

    def _open(self) -> Any:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = duckdb.connect(str(self.database_path))
        connection.execute("PRAGMA threads=1")
        return connection

    def build(self) -> CatalogSummary:
        """Create or replace derived views from current Parquet inputs."""
        self._require_inputs()
        connection = self._open()
        try:
            connection.execute("BEGIN TRANSACTION")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS catalog_meta (key VARCHAR PRIMARY KEY, value VARCHAR NOT NULL)"
            )
            connection.execute("DELETE FROM catalog_meta")
            metadata = [("schema_version", str(SCHEMA_VERSION))]
            metadata.extend((name + "_sha256", _sha256(path)) for name, path in self.inputs.items())
            connection.executemany("INSERT INTO catalog_meta VALUES (?, ?)", metadata)
            for name, path in self.inputs.items():
                connection.execute(
                    f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{self._sql_path(path)}')"
                )
            connection.execute(
                "CREATE OR REPLACE VIEW asset_provenance AS "
                "SELECT m.asset_id, m.source_id, m.url, m.sha256, "
                "a.relative_path, a.size_bytes "
                "FROM source_manifest AS m "
                "JOIN asset_index AS a "
                "ON m.asset_id = a.asset_id AND m.sha256 = a.sha256"
            )
            connection.execute("COMMIT")
        except Exception as exc:
            connection.execute("ROLLBACK")
            raise CatalogError(f"catalog build failed: {exc}") from exc
        finally:
            connection.close()
        return self.check()

    def _metadata(self, connection: Any) -> dict[str, str]:
        try:
            rows = connection.execute("SELECT key, value FROM catalog_meta").fetchall()
        except Exception as exc:
            raise CatalogError(f"catalog metadata is missing: {exc}") from exc
        return {str(key): str(value) for key, value in rows}

    def check(self) -> CatalogSummary:
        """Verify schema metadata, view inputs, hashes, and core join."""
        self._require_inputs()
        if not self.database_path.is_file():
            raise CatalogError(f"catalog database is missing: {self.database_path}")
        connection = self._open()
        try:
            metadata = self._metadata(connection)
            if metadata.get("schema_version") != str(SCHEMA_VERSION):
                raise CatalogError("catalog schema version is unsupported")
            for name, path in self.inputs.items():
                expected = metadata.get(name + "_sha256")
                if expected != _sha256(path):
                    raise CatalogError(f"catalog input changed since build: {name}")
                connection.execute(f"SELECT * FROM {name} LIMIT 0")
            source_rows = int(connection.execute("SELECT count(*) FROM source_manifest").fetchone()[0])
            asset_rows = int(connection.execute("SELECT count(*) FROM asset_index").fetchone()[0])
            rejection_rows = int(connection.execute("SELECT count(*) FROM rejected_sources").fetchone()[0])
            join_rows = int(connection.execute("SELECT count(*) FROM asset_provenance").fetchone()[0])
        except CatalogError:
            raise
        except Exception as exc:
            raise CatalogError(f"catalog check failed: {exc}") from exc
        finally:
            connection.close()
        return CatalogSummary(SCHEMA_VERSION, source_rows, asset_rows, rejection_rows, join_rows)

    def query(self, sql: str) -> list[tuple[Any, ...]]:
        """Run one caller-supplied read query against the derived catalog."""
        if not sql.lstrip().lower().startswith(("select", "with", "describe", "show")):
            raise CatalogError("catalog query must be read-only")
        connection = self._open()
        try:
            return [tuple(row) for row in connection.execute(sql).fetchall()]
        except Exception as exc:
            raise CatalogError(f"catalog query failed: {exc}") from exc
        finally:
            connection.close()
