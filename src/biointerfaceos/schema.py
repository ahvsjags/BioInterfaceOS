"""Versioned schema discovery and strict repository configuration validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

SCHEMA_NAMES = (
    "material",
    "bioenvironment",
    "protocol",
    "evidence",
    "corona",
    "response",
    "source",
    "agent",
    "claim",
)
SUPPORTED_TYPES = {"object", "array", "string", "number", "integer", "boolean", "null"}
SUPPORTED_KEYS = {
    "$schema",
    "$id",
    "title",
    "description",
    "schema_version",
    "type",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "enum",
    "minimum",
    "maximum",
    "minItems",
}


@dataclass(frozen=True)
class SchemaDocument:
    """A discovered versioned schema and its parsed document."""

    name: str
    version: int
    path: Path
    document: dict[str, Any]


@dataclass(frozen=True)
class LoadedConfig:
    """A validated configuration envelope."""

    schema: str
    schema_version: int
    data: Any
    path: Path


class SchemaError(ValueError):
    """Base error for schema discovery, definition, and configuration loading."""


class SchemaDefinitionError(SchemaError):
    """A schema document is malformed or uses an unsupported construct."""


class ValidationError(SchemaError):
    """An instance does not conform to its selected schema."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}")


class ConfigError(SchemaError):
    """A configuration cannot be safely loaded or has a bad envelope."""


def _contained(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    candidate = path if path.is_absolute() else resolved_root / path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ConfigError(f"path escapes repository root: {path}")
    return resolved


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaDefinitionError(f"{path}: cannot load JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SchemaDefinitionError(f"{path}: schema root must be an object")
    return value


def _check_schema(node: Any, path: str = "$") -> None:
    if not isinstance(node, dict):
        raise SchemaDefinitionError(f"{path}: schema node must be an object")
    unknown = sorted(set(node) - SUPPORTED_KEYS)
    if unknown:
        raise SchemaDefinitionError(f"{path}: unsupported keyword {unknown[0]!r}")
    schema_type = node.get("type")
    if schema_type not in SUPPORTED_TYPES:
        raise SchemaDefinitionError(f"{path}.type: expected a supported type")
    if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"]):
        raise SchemaDefinitionError(f"{path}.enum: expected a non-empty array")
    for key in ("minimum", "maximum"):
        value = node.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int | float)):
            raise SchemaDefinitionError(f"{path}.{key}: expected a number")
    if "minItems" in node and (
        isinstance(node["minItems"], bool)
        or not isinstance(node["minItems"], int)
        or node["minItems"] < 0
    ):
        raise SchemaDefinitionError(f"{path}.minItems: expected a non-negative integer")
    if schema_type == "object":
        properties = node.get("properties", {})
        required = node.get("required", [])
        if not isinstance(properties, dict):
            raise SchemaDefinitionError(f"{path}.properties: expected an object")
        if not isinstance(required, list) or any(not isinstance(v, str) for v in required):
            raise SchemaDefinitionError(f"{path}.required: expected an array of strings")
        missing = sorted(set(required) - set(properties))
        if missing:
            raise SchemaDefinitionError(f"{path}.required: unknown property {missing[0]!r}")
        if node.get("additionalProperties", True) is not False:
            raise SchemaDefinitionError(f"{path}.additionalProperties: must be false")
        for name, child in properties.items():
            _check_schema(child, f"{path}.properties.{name}")
    if schema_type == "array":
        if "items" not in node:
            raise SchemaDefinitionError(f"{path}.items: required for arrays")
        _check_schema(node["items"], f"{path}.items")


def discover_schemas(root: Path) -> dict[str, SchemaDocument]:
    """Discover and sanity-check exactly the nine version-one contracts."""
    schema_dir = _contained(root, Path("schemas"))
    found: dict[str, SchemaDocument] = {}
    for path in sorted(schema_dir.glob("*.v1.json")):
        name = path.name.removesuffix(".v1.json")
        document = _load_json(path)
        _check_schema(document)
        version = document.get("schema_version")
        if isinstance(version, bool) or version != 1:
            raise SchemaDefinitionError(f"{path}: schema_version must be integer 1")
        if name in found:
            raise SchemaDefinitionError(f"duplicate schema: {name}")
        found[name] = SchemaDocument(name, 1, path.resolve(), document)
    missing = sorted(set(SCHEMA_NAMES) - set(found))
    extra = sorted(set(found) - set(SCHEMA_NAMES))
    if missing or extra or len(found) != len(SCHEMA_NAMES):
        raise SchemaDefinitionError(f"schema set mismatch; missing={missing}, extra={extra}")
    return found


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return value is None


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> None:
    """Validate an instance recursively, raising the first deterministic error."""
    expected = schema["type"]
    if not _matches_type(instance, expected):
        raise ValidationError(path, f"expected {expected}, got {type(instance).__name__}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ValidationError(path, f"value {instance!r} is not in enum {schema['enum']!r}")
    if expected in {"integer", "number"}:
        if "minimum" in schema and instance < schema["minimum"]:
            raise ValidationError(path, f"must be >= {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ValidationError(path, f"must be <= {schema['maximum']}")
    if expected == "object":
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in instance:
                raise ValidationError(f"{path}.{required}", "required field is missing")
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(instance) - set(properties))
            if unknown:
                raise ValidationError(f"{path}.{unknown[0]}", "unknown field")
        for name in sorted(set(instance) & set(properties)):
            validate(instance[name], properties[name], f"{path}.{name}")
    if expected == "array":
        if len(instance) < schema.get("minItems", 0):
            raise ValidationError(path, f"must contain at least {schema['minItems']} items")
        for index, value in enumerate(instance):
            validate(value, schema["items"], f"{path}[{index}]")


def load_config(
    root: Path, path: Path, expected_schema: str, expected_version: int
) -> LoadedConfig:
    """Safely load and validate one strict YAML configuration envelope."""
    config_path = _contained(root, path)
    try:
        envelope = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"{config_path}: cannot load YAML: {exc}") from exc
    if not isinstance(envelope, dict):
        raise ConfigError("$: configuration envelope must be an object")
    expected_keys = {"schema", "schema_version", "data"}
    if set(envelope) != expected_keys:
        raise ConfigError(f"$: envelope keys must be exactly {sorted(expected_keys)!r}")
    if envelope["schema"] != expected_schema:
        raise ConfigError(f"$.schema: expected {expected_schema!r}")
    version = envelope["schema_version"]
    if isinstance(version, bool) or version != expected_version:
        raise ConfigError(f"$.schema_version: expected integer {expected_version}")
    schemas = discover_schemas(root)
    if expected_schema not in schemas:
        raise ConfigError(f"$.schema: unknown schema {expected_schema!r}")
    document = schemas[expected_schema]
    if document.version != expected_version:
        raise ConfigError(f"$.schema_version: schema version {expected_version} is unavailable")
    validate(envelope["data"], document.document, "$.data")
    return LoadedConfig(expected_schema, expected_version, envelope["data"], config_path)


def validate_all(root: Path) -> list[LoadedConfig]:
    """Validate all contracts and their repository fixtures."""
    schemas = discover_schemas(root)
    loaded = []
    for name in SCHEMA_NAMES:
        fixture = Path("tests/fixtures/schema") / f"{name}.v1.yaml"
        loaded.append(load_config(root, fixture, name, schemas[name].version))
    return loaded
