from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from biointerfaceos.schema import (
    ConfigError,
    SchemaDefinitionError,
    ValidationError,
    discover_schemas,
    load_config,
    validate,
    validate_all,
)

ROOT = Path(__file__).parents[1]


def write_yaml(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value), encoding="utf-8")


def test_discovery_and_all_valid_fixtures() -> None:
    assert len(discover_schemas(ROOT)) == 9
    assert len(validate_all(ROOT)) == 9


def test_invalid_nested_field_path(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "required": ["rows"],
        "properties": {"rows": {"type": "array", "items": {"type": "integer"}}},
        "additionalProperties": False,
    }
    with pytest.raises(ValidationError, match=r"\$\.rows\[1\]"):
        validate({"rows": [1, "bad"]}, schema)


def test_unknown_field(tmp_path: Path) -> None:
    fixture = tmp_path / "material.yaml"
    write_yaml(
        fixture,
        {
            "schema": "material",
            "schema_version": 1,
            "data": {"material_id": "m", "material_class": "metal", "size_nm": 1, "extra": 2},
        },
    )
    local = ROOT / "tests" / "fixtures" / "schema" / "_temporary.yaml"
    local.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        with pytest.raises(ValidationError, match=r"\$\.data\.extra: unknown field"):
            load_config(ROOT, local, "material", 1)
    finally:
        local.unlink()


@pytest.mark.parametrize("value, message", [("wood", "enum"), (3, "expected string")])
def test_enum_and_type(value: object, message: str) -> None:
    schema = discover_schemas(ROOT)["material"].document
    with pytest.raises(ValidationError, match=message):
        validate({"material_id": "m", "material_class": value, "size_nm": 1}, schema)


def test_bad_version(tmp_path: Path) -> None:
    path = ROOT / "tests" / "fixtures" / "schema" / "_temporary.yaml"
    write_yaml(path, {"schema": "material", "schema_version": 2, "data": {}})
    try:
        with pytest.raises(ConfigError, match="schema_version"):
            load_config(ROOT, path, "material", 1)
    finally:
        path.unlink()


def test_path_containment(tmp_path: Path) -> None:
    path = tmp_path / "outside.yaml"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError, match="escapes repository root"):
        load_config(ROOT, path, "material", 1)


def test_invalid_schema(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    for source in (ROOT / "schemas").glob("*.v1.json"):
        (root / "schemas" / source.name).write_bytes(source.read_bytes())
    broken = root / "schemas" / "claim.v1.json"
    document = json.loads(broken.read_text(encoding="utf-8"))
    document["unsupported"] = True
    broken.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SchemaDefinitionError, match="unsupported keyword"):
        discover_schemas(root)


def test_boolean_is_not_integer() -> None:
    with pytest.raises(ValidationError, match="expected integer"):
        validate(True, {"type": "integer"})
