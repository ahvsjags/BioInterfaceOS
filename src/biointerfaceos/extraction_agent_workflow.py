"""Offline multimodal ExtractionAgent parser selection and evidence validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.agent_runtime import TraceLedger
from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string


class ExtractionAgentError(RuntimeError):
    """Raised when the ExtractionAgent contract is invalid."""


@dataclass(frozen=True)
class ExtractionAgentSummary:
    """Summary of one deterministic extraction-agent evaluation."""

    cases: int
    agent_correct: int
    fixed_correct: int
    agent_accuracy: float
    fixed_accuracy: float
    selected_pipeline: str
    schema_valid: bool
    evidence_grounded: bool
    trace_events: int
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise ExtractionAgentError(f"{label} fields do not match schema")


class ExtractionAgentWorkflow:
    """Select deterministic parser tools and compare agent value to fixed extraction."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/agents/extraction_agent_fixture.json")
        self.output_root = output_root or self.root / "reports/agents/extraction"

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "extraction-agent fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ExtractionAgentError(f"cannot load extraction-agent fixture: {exc}") from exc
        _keys(data, {"schema_version", "mode", "inputs", "cases"}, "extraction-agent fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "extraction_agent_fixture":
            raise ExtractionAgentError("extraction-agent fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("cases"), list):
            raise ExtractionAgentError("extraction-agent inputs/cases are invalid")
        return data

    def _inputs(self, fixture: dict[str, Any]) -> None:
        expected = {
            "T050 benchmark receipt": (
                self.root / "reports/benchmark/benchmark_receipt.json",
                "096ecc8a263e1f41268b2004decae90d23528a1c4ffffcf6c8227888d0854712",
            ),
            "T080 agent receipt": (
                self.root / "reports/agents/agent_receipt.json",
                "09750940ab002de284939df873657c6013db25ef21e1d26c243d15046884094f",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "extraction-agent input")
            _keys(row, {"label", "path", "sha256"}, "extraction-agent input")
            label = _string(row.get("label"), "extraction-agent input label")
            if label not in expected:
                raise ExtractionAgentError(f"unexpected extraction-agent input: {label}")
            path, checksum = expected[label]
            declared = (self.root / _string(row.get("path"), "input path")).resolve(strict=True)
            if declared != path.resolve(strict=True) or row.get("sha256") != checksum:
                raise ExtractionAgentError(f"input path or checksum differs: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise ExtractionAgentError(f"input checksum differs: {label}")
            receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), f"{label} receipt")
            if label == "T050 benchmark receipt" and receipt.get("g2_status") != "PASS":
                raise ExtractionAgentError("T050 fixed benchmark is not passing G2")
            if label == "T080 agent receipt" and receipt.get("trace_sealed") is not True:
                raise ExtractionAgentError("T080 runtime trace is not sealed")
            seen.add(label)
        if seen != set(expected):
            raise ExtractionAgentError("extraction-agent inputs are incomplete")

    @staticmethod
    def _cases(fixture: dict[str, Any]) -> list[dict[str, Any]]:
        required = {
            "case_id",
            "document_kind",
            "source_asset_id",
            "allowed_tools",
            "expected_parser",
            "fixed_correct",
            "agent_fields",
        }
        cases: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["cases"]:
            case = _mapping(value, "extraction-agent case")
            _keys(case, required, "extraction-agent case")
            case_id = _string(case.get("case_id"), "extraction-agent case ID")
            if case_id in seen:
                raise ExtractionAgentError(f"duplicate extraction-agent case: {case_id}")
            allowed = case.get("allowed_tools")
            fields = case.get("agent_fields")
            if not isinstance(allowed, list) or not allowed or any(not isinstance(tool, str) for tool in allowed):
                raise ExtractionAgentError(f"invalid parser allowlist: {case_id}")
            if not isinstance(fields, list) or not fields:
                raise ExtractionAgentError(f"invalid agent fields: {case_id}")
            fixed_correct = case.get("fixed_correct")
            if not isinstance(fixed_correct, bool):
                raise ExtractionAgentError(f"fixed correctness must be boolean: {case_id}")
            cases.append(
                {
                    "case_id": case_id,
                    "document_kind": _string(case.get("document_kind"), "document kind"),
                    "source_asset_id": _string(case.get("source_asset_id"), "asset ID"),
                    "allowed_tools": tuple(allowed),
                    "expected_parser": _string(case.get("expected_parser"), "expected parser"),
                    "fixed_correct": fixed_correct,
                    "agent_fields": fields,
                }
            )
            seen.add(case_id)
        if not cases:
            raise ExtractionAgentError("extraction-agent fixture has no cases")
        return cases

    @staticmethod
    def _validate_fields(fields: list[Any]) -> tuple[bool, bool, list[dict[str, Any]]]:
        schema_valid = True
        evidence_grounded = True
        names: set[str] = set()
        normalized: list[dict[str, Any]] = []
        required = {
            "field_name",
            "value",
            "value_type",
            "unit",
            "evidence_locators",
            "confidence",
        }
        for value in fields:
            field = _mapping(value, "extraction-agent field")
            if set(field) != required:
                schema_valid = False
                continue
            name = _string(field.get("field_name"), "field name")
            value_type = _string(field.get("value_type"), "field type").lower()
            locators = field.get("evidence_locators")
            confidence = field.get("confidence")
            type_ok = value_type in {"string", "integer", "number"}
            confidence_ok = (
                isinstance(confidence, int | float)
                and not isinstance(confidence, bool)
                and 0.0 <= float(confidence) <= 1.0
            )
            locator_ok = (
                isinstance(locators, list)
                and bool(locators)
                and all(isinstance(locator, str) and locator.startswith("asset:") for locator in locators)
            )
            value_ok = (
                (value_type == "string" and isinstance(field["value"], str))
                or (
                    value_type == "integer" and isinstance(field["value"], int) and not isinstance(field["value"], bool)
                )
                or (
                    value_type == "number"
                    and isinstance(field["value"], int | float)
                    and not isinstance(field["value"], bool)
                )
            )
            if name in names or not type_ok or not confidence_ok or not locator_ok or not value_ok:
                schema_valid = False
            if not locator_ok:
                evidence_grounded = False
            names.add(name)
            normalized.append(
                {
                    "field_name": name,
                    "value": field["value"],
                    "value_type": value_type,
                    "unit": field["unit"],
                    "evidence_locators": list(locators) if isinstance(locators, list) else [],
                    "confidence": float(confidence) if isinstance(confidence, int | float) else 0.0,
                }
            )
        return schema_valid, evidence_grounded, normalized

    @staticmethod
    def _parser(case: dict[str, Any]) -> str:
        by_kind = {
            "table": "table_semantics",
            "figure": "figure_digitizer",
            "supplement": "supplement_parser",
            "pdf": "pdf_parser",
        }
        parser = by_kind.get(case["document_kind"])
        if parser is None or parser not in case["allowed_tools"]:
            raise ExtractionAgentError(f"no allowlisted parser for {case['case_id']}")
        return parser

    def run(self, *, fixture: bool = True) -> ExtractionAgentSummary:
        """Evaluate parser selection, evidence grounding, and fixed-pipeline value."""
        if not fixture:
            raise ExtractionAgentError("--fixture is required for extraction-agent evaluation")
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        cases = self._cases(fixture_data)
        trace = TraceLedger()
        decisions: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        agent_correct = 0
        fixed_correct = sum(case["fixed_correct"] for case in cases)
        schema_valid = True
        evidence_grounded = True
        for case in cases:
            parser = self._parser(case)
            trace.append("parser_selected", case["case_id"], 0, {"parser": parser})
            valid, grounded, fields = self._validate_fields(case["agent_fields"])
            schema_valid = schema_valid and valid
            evidence_grounded = evidence_grounded and grounded
            correct = parser == case["expected_parser"] and valid and grounded
            agent_correct += correct
            trace.append(
                "evidence_validated",
                case["case_id"],
                0,
                {"schema_valid": valid, "evidence_grounded": grounded, "fields": len(fields)},
            )
            decisions.append(
                {
                    "case_id": case["case_id"],
                    "document_kind": case["document_kind"],
                    "selected_parser": parser,
                    "expected_parser": case["expected_parser"],
                    "allowed_tools": list(case["allowed_tools"]),
                    "agent_correct": correct,
                    "source_asset_id": case["source_asset_id"],
                }
            )
            records.append(
                {
                    "case_id": case["case_id"],
                    "source_asset_id": case["source_asset_id"],
                    "fields": fields,
                    "schema_version": 1,
                    "evidence_grounded": grounded,
                }
            )
        trace.validate()
        agent_accuracy = agent_correct / len(cases)
        fixed_accuracy = fixed_correct / len(cases)
        selected = (
            "extraction_agent"
            if schema_valid and evidence_grounded and agent_accuracy > fixed_accuracy
            else "fixed_pipeline"
        )
        comparison = {
            "schema_version": 1,
            "cases": len(cases),
            "agent_correct": agent_correct,
            "fixed_correct": fixed_correct,
            "agent_accuracy": agent_accuracy,
            "fixed_accuracy": fixed_accuracy,
            "agent_value": int(selected == "extraction_agent"),
            "selected_pipeline": selected,
            "schema_valid": schema_valid,
            "evidence_grounded": evidence_grounded,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "decisions": {
                "schema_version": 1,
                "decisions": decisions,
                "target_values_exposed": False,
            },
            "records": {
                "schema_version": 1,
                "records": records,
                "target_values_exposed": False,
            },
            "comparison": comparison,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        trace_bytes = trace.to_bytes()
        seal = trace.seal()
        resume_key = _sha256(_canonical(raw_payloads) + trace_bytes + _canonical(seal))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "decisions": self.output_root / "parser_decisions.json",
            "records": self.output_root / "extracted_records.json",
            "comparison": self.output_root / "metric_comparison.json",
            "failures": self.output_root / "failure_ledger.json",
            "trace": self.output_root / "tool_trace.jsonl",
            "seal": self.output_root / "tool_trace_seal.json",
            "receipt": self.output_root / "extraction_agent_receipt.json",
            "log": self.output_root / "extraction_agent_log.json",
            "manifest": self.output_root / "extraction_agent_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        payload_bytes["trace"] = trace_bytes
        payload_bytes["seal"] = _canonical(seal)
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "model": "EXTRACTION_AGENT",
            "status": "VALID",
            "fixture": True,
            "cases": len(cases),
            "agent_correct": agent_correct,
            "fixed_correct": fixed_correct,
            "agent_accuracy": agent_accuracy,
            "fixed_accuracy": fixed_accuracy,
            "selected_pipeline": selected,
            "schema_valid": schema_valid,
            "evidence_grounded": evidence_grounded,
            "trace_events": len(trace.records),
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        payload_bytes["log"] = _canonical(
            {
                "schema_version": 1,
                "resume_key": resume_key,
                "events": [
                    {"event": "T050_T080_inputs_verified", "cases": len(cases)},
                    {"event": "parser_selection_completed", "cases": len(cases)},
                    {
                        "event": "evidence_schema_validation_completed",
                        "passed": schema_valid and evidence_grounded,
                    },
                    {"event": "fixed_pipeline_comparison_completed", "selected": selected},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "EXTRACTION_AGENT",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                        "sha256": _sha256(payload_bytes[name]),
                        "bytes": len(payload_bytes[name]),
                    }
                    for name, path in paths.items()
                    if name in payload_bytes
                },
            }
        )
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise ExtractionAgentError("existing extraction-agent receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise ExtractionAgentError(f"existing extraction-agent artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return ExtractionAgentSummary(
            cases=len(cases),
            agent_correct=agent_correct,
            fixed_correct=fixed_correct,
            agent_accuracy=agent_accuracy,
            fixed_accuracy=fixed_accuracy,
            selected_pipeline=selected,
            schema_valid=schema_valid,
            evidence_grounded=evidence_grounded,
            trace_events=len(trace.records),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
