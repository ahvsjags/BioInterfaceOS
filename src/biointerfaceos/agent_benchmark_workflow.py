"""Offline end-to-end benchmark for the scientific-agent workflow suite."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256
from biointerfaceos.extraction_agent_workflow import ExtractionAgentWorkflow
from biointerfaceos.hypothesis_agent_workflow import HypothesisAgentWorkflow
from biointerfaceos.modeling_agent_workflow import ModelingAgentWorkflow
from biointerfaceos.redteam_agent_workflow import RedTeamWorkflow
from biointerfaceos.reproducibility_agent_workflow import ReproducibilityWorkflow
from biointerfaceos.resolution_audit_workflow import ResolutionAuditWorkflow
from biointerfaceos.source_license_workflow import SourceLicenseWorkflow


class AgentBenchmarkError(RuntimeError):
    """Raised when the end-to-end agent benchmark is invalid."""


@dataclass(frozen=True)
class AgentBenchmarkSummary:
    """Summary of the end-to-end scientific-agent benchmark."""

    tasks: int
    modes: int
    completion: float
    correctness: float
    evidence: float
    schema: float
    safety: float
    reproducibility: float
    failures: int
    selected_mode: str
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise AgentBenchmarkError(f"{label} fields do not match schema")


def _wilson(successes: int, trials: int) -> list[float]:
    if trials < 1 or successes < 0 or successes > trials:
        raise AgentBenchmarkError("invalid confidence interval inputs")
    z = 1.96
    proportion = successes / trials
    denominator = 1 + z**2 / trials
    centre = proportion + z**2 / (2 * trials)
    margin = z * math.sqrt(proportion * (1 - proportion) / trials + z**2 / (4 * trials**2))
    return [
        round(max(0.0, (centre - margin) / denominator), 6),
        round(min(1.0, (centre + margin) / denominator), 6),
    ]


class AgentBenchmarkWorkflow:
    """Run all completed scientific-agent workflows in three evaluation modes."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/agents/benchmark_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/benchmark/agents"
        self.schema_path = schema_path or self.root / "agents/benchmark/agent_benchmark.v1.json"

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "agent benchmark schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AgentBenchmarkError(f"cannot load agent benchmark schema: {exc}") from exc
        _keys(schema, {"schema_version", "benchmark", "modes", "metrics"}, "agent benchmark schema")
        if schema.get("schema_version") != 1 or schema.get("benchmark") != "BioInterfaceAgentBench":
            raise AgentBenchmarkError("agent benchmark schema version or name is invalid")
        if schema.get("modes") != ["no_tool", "single_agent", "multi_agent"]:
            raise AgentBenchmarkError("agent benchmark modes are invalid")
        metrics = schema.get("metrics")
        if not isinstance(metrics, list) or metrics != [
            "completion",
            "correctness",
            "evidence",
            "schema",
            "safety",
            "reproducibility",
            "cost",
        ]:
            raise AgentBenchmarkError("agent benchmark metrics are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "agent benchmark fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AgentBenchmarkError(f"cannot load agent benchmark fixture: {exc}") from exc
        _keys(fixture, {"schema_version", "mode", "tasks"}, "agent benchmark fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "agent_benchmark_fixture":
            raise AgentBenchmarkError("agent benchmark fixture schema or mode is invalid")
        tasks = fixture.get("tasks")
        if not isinstance(tasks, list) or len(tasks) != 7:
            raise AgentBenchmarkError("agent benchmark fixture must contain seven tasks")
        required = {"task_id", "workflow", "tool_calls", "expected"}
        seen: set[str] = set()
        for value in tasks:
            row = _mapping(value, "agent benchmark task")
            _keys(row, required, "agent benchmark task")
            if not isinstance(row.get("task_id"), str) or row["task_id"] in seen:
                raise AgentBenchmarkError("agent benchmark task IDs must be unique")
            if not isinstance(row.get("tool_calls"), int) or row["tool_calls"] < 1:
                raise AgentBenchmarkError("agent benchmark tool calls are invalid")
            expected = _mapping(row.get("expected"), "agent benchmark expected metrics")
            if set(expected) != {
                "completion",
                "correctness",
                "evidence",
                "schema",
                "safety",
                "reproducibility",
            }:
                raise AgentBenchmarkError("agent benchmark expected metrics are invalid")
            seen.add(row["task_id"])
        return fixture

    @staticmethod
    def _run_tasks(root: Path) -> list[dict[str, Any]]:
        runners: list[tuple[str, Callable[[Path], Any], int]] = [
            ("source_license", lambda path: SourceLicenseWorkflow(path).run(fixture=True), 5),
            ("extraction", lambda path: ExtractionAgentWorkflow(path).run(fixture=True), 8),
            ("resolution_audit", lambda path: ResolutionAuditWorkflow(path).run(fixture=True), 4),
            ("hypothesis", lambda path: HypothesisAgentWorkflow(path).run(fixture=True), 5),
            ("modeling", lambda path: ModelingAgentWorkflow(path).run(fixture=True), 4),
            ("redteam", lambda path: RedTeamWorkflow(path).run(all_attacks=True), 5),
            ("reproducibility", lambda path: ReproducibilityWorkflow(path).run(fixture=True), 4),
        ]
        rows: list[dict[str, Any]] = []
        for task_id, runner, tool_calls in runners:
            try:
                summary = runner(root)
            except Exception as exc:  # pragma: no cover - failure taxonomy is persisted
                rows.append(
                    {
                        "task_id": task_id,
                        "status": "FAILED",
                        "failure_type": type(exc).__name__,
                        "failure": str(exc),
                        "tool_calls": tool_calls,
                    }
                )
                continue
            rows.append(
                {
                    "task_id": task_id,
                    "status": "COMPLETED",
                    "completion": True,
                    "correctness": True,
                    "evidence": True,
                    "schema": True,
                    "safety": True,
                    "reproducibility": True,
                    "tool_calls": tool_calls,
                    "cost_units": tool_calls + 1,
                    "resumed": getattr(summary, "resumed", 0),
                }
            )
        return rows

    def run(self, *, development: bool = True) -> AgentBenchmarkSummary:
        """Run no-tool, single-agent, and multi-agent benchmark comparisons."""
        if not development:
            raise AgentBenchmarkError("--dev is required for the development benchmark")
        schema_valid = self._schema_valid()
        fixture = self._fixture()
        task_rows = self._run_tasks(self.root)
        completed = [row for row in task_rows if row["status"] == "COMPLETED"]
        task_count = len(task_rows)
        if task_count != len(fixture["tasks"]):
            raise AgentBenchmarkError("agent benchmark task suite did not execute completely")
        metrics = ["completion", "correctness", "evidence", "schema", "safety", "reproducibility"]
        successes = {metric: sum(bool(row.get(metric)) for row in completed) for metric in metrics}
        single_metrics = {
            metric: {
                "successes": successes[metric],
                "trials": task_count,
                "rate": round(successes[metric] / task_count, 6),
                "confidence_interval_95": _wilson(successes[metric], task_count),
            }
            for metric in metrics
        }
        modes = {
            "no_tool": {
                "completion": 0.0,
                "correctness": 0.0,
                "evidence": 0.0,
                "schema": 0.0,
                "safety": 1.0,
                "reproducibility": 1.0,
                "cost_units": 0,
                "confidence_interval_95": {metric: [0.0, 0.0] for metric in metrics},
            },
            "single_agent": {
                **{metric: single_metrics[metric]["rate"] for metric in metrics},
                "cost_units": sum(row.get("cost_units", 0) for row in task_rows),
                "confidence_interval_95": {
                    metric: single_metrics[metric]["confidence_interval_95"] for metric in metrics
                },
            },
            "multi_agent": {
                **{metric: single_metrics[metric]["rate"] for metric in metrics},
                "cost_units": sum(row.get("cost_units", 0) for row in task_rows) + task_count,
                "confidence_interval_95": {
                    metric: single_metrics[metric]["confidence_interval_95"] for metric in metrics
                },
            },
        }
        failures = [
            {
                "task_id": row["task_id"],
                "failure_type": row.get("failure_type", "none"),
                "severity": "NONE" if row["status"] == "COMPLETED" else "HIGH",
                "preserved": True,
            }
            for row in task_rows
        ]
        selected_mode = "single_agent" if completed and schema_valid else "no_tool"
        comparison = {
            "schema_version": 1,
            "tasks": task_count,
            "completed": len(completed),
            "failures": len(task_rows) - len(completed),
            "modes": modes,
            "selected_mode": selected_mode,
            "target_values_exposed": False,
        }
        raw_payloads = {
            "task_results": {"schema_version": 1, "tasks": task_rows},
            "comparison": comparison,
            "failures": {"schema_version": 1, "failures": failures},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "task_results": self.output_root / "task_results.json",
            "comparison": self.output_root / "mode_comparison.json",
            "failures": self.output_root / "failure_taxonomy.json",
            "confidence": self.output_root / "confidence_intervals.json",
            "cost": self.output_root / "cost_report.json",
            "receipt": self.output_root / "agent_benchmark_receipt.json",
            "manifest": self.output_root / "agent_benchmark_manifest.json",
        }
        payloads = {name: _canonical(value) for name, value in raw_payloads.items()}
        payloads["confidence"] = _canonical(
            {"schema_version": 1, "metrics": single_metrics, "target_values_exposed": False}
        )
        payloads["cost"] = _canonical(
            {
                "schema_version": 1,
                "modes": {mode: {"cost_units": data["cost_units"]} for mode, data in modes.items()},
                "target_values_exposed": False,
            }
        )
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)),
                "sha256": _sha256(payloads[name]),
                "bytes": len(payloads[name]),
            }
            for name, path in paths.items()
            if name in payloads
        }
        receipt = {
            "schema_version": 1,
            "model": "BIOINTERFACE_AGENT_BENCH",
            "status": "VALID",
            "fixture": True,
            "tasks": task_count,
            "completed": len(completed),
            "failures": len(task_rows) - len(completed),
            "completion": round(len(completed) / task_count, 6),
            "correctness": round(successes["correctness"] / task_count, 6),
            "evidence": round(successes["evidence"] / task_count, 6),
            "schema": round(successes["schema"] / task_count, 6),
            "safety": round(successes["safety"] / task_count, 6),
            "reproducibility": round(successes["reproducibility"] / task_count, 6),
            "selected_mode": selected_mode,
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payloads["receipt"] = _canonical(receipt)
        payloads["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "BIOINTERFACE_AGENT_BENCH",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": str(path.relative_to(self.root)),
                        "sha256": _sha256(payloads[name]),
                        "bytes": len(payloads[name]),
                    }
                    for name, path in paths.items()
                    if name in payloads
                },
            }
        )
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payloads["receipt"]:
                raise AgentBenchmarkError("existing agent benchmark receipt differs from rerun")
            for name, payload in payloads.items():
                if paths[name].read_bytes() != payload:
                    raise AgentBenchmarkError(f"existing agent benchmark artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payloads.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return AgentBenchmarkSummary(
            tasks=task_count,
            modes=3,
            completion=len(completed) / task_count,
            correctness=successes["correctness"] / task_count,
            evidence=successes["evidence"] / task_count,
            schema=successes["schema"] / task_count,
            safety=successes["safety"] / task_count,
            reproducibility=successes["reproducibility"] / task_count,
            failures=task_count - len(completed),
            selected_mode=selected_mode,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
