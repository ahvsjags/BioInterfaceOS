"""Typed, deterministic mock/rule multi-agent runtime with append-only traces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256, _string


class AgentRuntimeError(RuntimeError):
    """Base runtime contract error."""


class ToolNotAllowed(AgentRuntimeError):
    """Raised when a task requests a tool outside its agent allowlist."""


class BudgetExceeded(AgentRuntimeError):
    """Raised when a task exceeds its declared tool-call budget."""


class TransientBackendError(AgentRuntimeError):
    """Raised by the mock backend to exercise deterministic retry behavior."""


def _strict_keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise AgentRuntimeError(f"{label} fields do not match schema")


@dataclass(frozen=True)
class AgentSpec:
    """Typed agent contract."""

    agent_id: str
    role: str
    enabled: bool

    @classmethod
    def from_value(cls, value: Any) -> AgentSpec:
        row = _mapping(value, "agent")
        _strict_keys(row, {"agent_id", "role", "enabled"}, "agent")
        role = _string(row.get("role"), "agent role")
        if role not in {"retrieval", "extraction", "validation"}:
            raise AgentRuntimeError(f"unsupported agent role: {role}")
        enabled = row.get("enabled")
        if not isinstance(enabled, bool):
            raise AgentRuntimeError("agent enabled must be boolean")
        return cls(_string(row.get("agent_id"), "agent ID"), role, enabled)


@dataclass(frozen=True)
class TaskStep:
    """One typed tool invocation in a task."""

    tool: str
    arguments: dict[str, Any]

    @classmethod
    def from_value(cls, value: Any) -> TaskStep:
        row = _mapping(value, "task step")
        _strict_keys(row, {"tool", "arguments"}, "task step")
        arguments = row.get("arguments")
        if not isinstance(arguments, dict):
            raise AgentRuntimeError("task step arguments must be an object")
        return cls(_string(row.get("tool"), "task step tool"), dict(arguments))


@dataclass(frozen=True)
class TaskSpec:
    """Typed task contract with explicit tools, budget, and retry limit."""

    task_id: str
    agent_id: str
    tool_allowlist: tuple[str, ...]
    budget_steps: int
    max_retries: int
    steps: tuple[TaskStep, ...]

    @classmethod
    def from_value(cls, value: Any) -> TaskSpec:
        row = _mapping(value, "task")
        _strict_keys(
            row,
            {"task_id", "agent_id", "tool_allowlist", "budget_steps", "max_retries", "steps"},
            "task",
        )
        allowlist = row.get("tool_allowlist")
        steps = row.get("steps")
        if not isinstance(allowlist, list) or not allowlist or any(not isinstance(tool, str) for tool in allowlist):
            raise AgentRuntimeError("task tool_allowlist must be a non-empty string list")
        if not isinstance(steps, list) or not steps:
            raise AgentRuntimeError("task steps must be a non-empty list")
        budget = row.get("budget_steps")
        retries = row.get("max_retries")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
            raise AgentRuntimeError("task budget_steps must be a positive integer")
        if isinstance(retries, bool) or not isinstance(retries, int) or retries < 0:
            raise AgentRuntimeError("task max_retries must be a non-negative integer")
        return cls(
            _string(row.get("task_id"), "task ID"),
            _string(row.get("agent_id"), "task agent ID"),
            tuple(allowlist),
            budget,
            retries,
            tuple(TaskStep.from_value(step) for step in steps),
        )


class TraceLedger:
    """In-memory append-only hash-chain trace."""

    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def append(self, event_type: str, task_id: str, attempt: int, payload: dict[str, Any]) -> None:
        record = {
            "sequence": len(self.records) + 1,
            "event_type": event_type,
            "task_id": task_id,
            "attempt": attempt,
            "payload": payload,
            "previous_hash": self.records[-1]["event_hash"] if self.records else None,
        }
        record["event_hash"] = _sha256(_canonical(record))
        self.records.append(record)

    def validate(self) -> None:
        previous: str | None = None
        for index, record in enumerate(self.records, start=1):
            if record.get("sequence") != index or record.get("previous_hash") != previous:
                raise AgentRuntimeError("trace sequence or previous hash is invalid")
            event_hash = record.get("event_hash")
            unsigned = {key: value for key, value in record.items() if key != "event_hash"}
            if event_hash != _sha256(_canonical(unsigned)):
                raise AgentRuntimeError("trace event hash is invalid")
            previous = event_hash

    def to_bytes(self) -> bytes:
        self.validate()
        return b"".join(_canonical(record) for record in self.records)

    def seal(self) -> dict[str, Any]:
        trace_bytes = self.to_bytes()
        return {
            "schema_version": 1,
            "events": len(self.records),
            "trace_sha256": _sha256(trace_bytes),
            "last_event_hash": self.records[-1]["event_hash"] if self.records else None,
        }


class RuleBackend:
    """Offline deterministic backend used by CI and replay."""

    provider_key_required = False

    def __init__(self) -> None:
        self._flaky_calls: dict[str, int] = {}

    def call(self, tool: str, arguments: dict[str, Any], task_id: str) -> dict[str, Any]:
        if tool == "fixture.lookup":
            return {"status": "ok", "key": arguments.get("key"), "value": "fixture-value"}
        if tool == "claim.validate":
            return {"status": "ok", "valid": True, "claim_id": arguments.get("claim_id")}
        if tool == "flaky.check":
            calls = self._flaky_calls.get(task_id, 0)
            self._flaky_calls[task_id] = calls + 1
            if calls == 0:
                raise TransientBackendError("deterministic transient fixture failure")
            return {"status": "ok", "recovered": True}
        raise AgentRuntimeError(f"rule backend has no tool: {tool}")


class RuntimeEngine:
    """Execute typed tasks with allowlists, budgets, retries, and traces."""

    def __init__(
        self,
        agents: list[AgentSpec],
        backend: RuleBackend,
        trace: TraceLedger,
    ) -> None:
        self.agents = {agent.agent_id: agent for agent in agents}
        self.backend = backend
        self.trace = trace

    def run_task(self, task: TaskSpec) -> dict[str, Any]:
        agent = self.agents.get(task.agent_id)
        if agent is None or not agent.enabled:
            raise AgentRuntimeError(f"task agent is unavailable: {task.agent_id}")
        self.trace.append("task_started", task.task_id, 0, {"agent_id": agent.agent_id})
        calls = 0
        retries = 0
        outputs: list[dict[str, Any]] = []
        for step_index, step in enumerate(task.steps):
            attempt = 0
            while True:
                if calls >= task.budget_steps:
                    self.trace.append("budget_exceeded", task.task_id, attempt, {"calls": calls})
                    raise BudgetExceeded(f"task budget exceeded: {task.task_id}")
                if step.tool not in task.tool_allowlist:
                    self.trace.append("tool_rejected", task.task_id, attempt, {"tool": step.tool})
                    raise ToolNotAllowed(f"tool not allowed: {step.tool}")
                calls += 1
                attempt += 1
                self.trace.append(
                    "tool_call",
                    task.task_id,
                    attempt,
                    {"step": step_index, "tool": step.tool, "arguments": step.arguments},
                )
                try:
                    result = self.backend.call(step.tool, step.arguments, task.task_id)
                except TransientBackendError as exc:
                    if retries >= task.max_retries:
                        self.trace.append("task_failed", task.task_id, attempt, {"error": str(exc)})
                        raise
                    retries += 1
                    self.trace.append(
                        "retry_scheduled",
                        task.task_id,
                        attempt,
                        {"retry": retries, "error": str(exc)},
                    )
                    continue
                self.trace.append("tool_result", task.task_id, attempt, result)
                outputs.append(result)
                break
        self.trace.append(
            "task_completed",
            task.task_id,
            0,
            {"calls": calls, "retries": retries, "outputs": len(outputs)},
        )
        return {
            "task_id": task.task_id,
            "status": "COMPLETED",
            "calls": calls,
            "retries": retries,
            "outputs": outputs,
        }

    def run_all(self, tasks: list[TaskSpec]) -> list[dict[str, Any]]:
        return [self.run_task(task) for task in tasks]


@dataclass(frozen=True)
class AgentRuntimeSummary:
    """Summary of the complete offline runtime self-test."""

    agents: int
    tasks: int
    events: int
    schema_validated: bool
    tool_allowlist_passed: bool
    budget_passed: bool
    replay_passed: bool
    retry_passed: bool
    trace_sealed: bool
    provider_key_required: bool
    resumed: int
    receipt_path: Path


class AgentRuntime:
    """Load the fixture contract, self-test the runtime, and persist audit artifacts."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/agents/runtime_fixture.json"
        self.output_root = output_root or self.root / "reports/agents"
        self.schema_path = self.root / "agents/runtime/agent_runtime.v1.json"

    def _fixture(self) -> tuple[list[AgentSpec], list[TaskSpec]]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "agent runtime fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AgentRuntimeError(f"cannot load agent runtime fixture: {exc}") from exc
        _strict_keys(data, {"schema_version", "mode", "agents", "tasks"}, "agent runtime fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "agent_runtime_fixture":
            raise AgentRuntimeError("agent runtime fixture schema or mode is invalid")
        agents_raw = data.get("agents")
        tasks_raw = data.get("tasks")
        if not isinstance(agents_raw, list) or not isinstance(tasks_raw, list):
            raise AgentRuntimeError("agent runtime agents/tasks must be arrays")
        agents = [AgentSpec.from_value(value) for value in agents_raw]
        tasks = [TaskSpec.from_value(value) for value in tasks_raw]
        if len({agent.agent_id for agent in agents}) != len(agents):
            raise AgentRuntimeError("agent IDs must be unique")
        if len({task.task_id for task in tasks}) != len(tasks):
            raise AgentRuntimeError("task IDs must be unique")
        return agents, tasks

    def _schema_valid(self) -> bool:
        try:
            document = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "agent runtime schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AgentRuntimeError(f"cannot load agent runtime schema: {exc}") from exc
        _strict_keys(
            document,
            {"schema_version", "title", "required", "properties"},
            "runtime schema",
        )
        if document.get("schema_version") != 1 or document.get("required") != ["agents", "tasks"]:
            raise AgentRuntimeError("agent runtime schema metadata is invalid")
        properties = document.get("properties")
        if not isinstance(properties, dict) or set(properties) != {"agents", "tasks"}:
            raise AgentRuntimeError("agent runtime schema properties are invalid")
        return True

    @staticmethod
    def _negative_checks(agents: list[AgentSpec]) -> tuple[bool, bool]:
        probe_agent = agents[0]
        bad_tool_task = TaskSpec(
            "probe-tool",
            probe_agent.agent_id,
            ("fixture.lookup",),
            1,
            0,
            (TaskStep("claim.validate", {"claim_id": "blocked"}),),
        )
        bad_budget_task = TaskSpec(
            "probe-budget",
            probe_agent.agent_id,
            ("fixture.lookup",),
            1,
            0,
            (
                TaskStep("fixture.lookup", {"key": "a"}),
                TaskStep("fixture.lookup", {"key": "b"}),
            ),
        )
        allowlist_passed = False
        budget_passed = False
        try:
            RuntimeEngine(agents, RuleBackend(), TraceLedger()).run_task(bad_tool_task)
        except ToolNotAllowed:
            allowlist_passed = True
        try:
            RuntimeEngine(agents, RuleBackend(), TraceLedger()).run_task(bad_budget_task)
        except BudgetExceeded:
            budget_passed = True
        return allowlist_passed, budget_passed

    def run(self, *, fixture: bool = True) -> AgentRuntimeSummary:
        """Run all offline runtime checks and persist a sealed deterministic trace."""
        if not fixture:
            raise AgentRuntimeError("--fixture is required for agent self-test")
        schema_validated = self._schema_valid()
        agents, tasks = self._fixture()
        trace = TraceLedger()
        results = RuntimeEngine(agents, RuleBackend(), trace).run_all(tasks)
        trace.validate()
        replay_trace = TraceLedger()
        replay_results = RuntimeEngine(agents, RuleBackend(), replay_trace).run_all(tasks)
        replay_passed = results == replay_results and trace.to_bytes() == replay_trace.to_bytes()
        tool_allowlist_passed, budget_passed = self._negative_checks(agents)
        retry_passed = any(result["retries"] == 1 for result in results)
        trace_sealed = trace.seal()["trace_sha256"] == _sha256(trace.to_bytes())
        checks_passed = (
            schema_validated
            and tool_allowlist_passed
            and budget_passed
            and replay_passed
            and retry_passed
            and trace_sealed
            and not RuleBackend.provider_key_required
        )
        audit = {
            "schema_version": 1,
            "agents": len(agents),
            "tasks": len(tasks),
            "schema_validated": schema_validated,
            "tool_allowlist_passed": tool_allowlist_passed,
            "budget_passed": budget_passed,
            "replay_passed": replay_passed,
            "retry_passed": retry_passed,
            "trace_sealed": trace_sealed,
            "provider_key_required": RuleBackend.provider_key_required,
            "target_values_exposed": False,
        }
        failures = {
            "schema_version": 1,
            "status": "VALID" if checks_passed else "INVALID",
            "failures": [
                key
                for key, value in audit.items()
                if isinstance(value, bool)
                and not value
                and key not in {"provider_key_required", "target_values_exposed"}
            ],
        }
        raw_payloads: dict[str, Any] = {
            "results": {"schema_version": 1, "tasks": results, "target_values_exposed": False},
            "audit": audit,
            "failures": failures,
        }
        trace_bytes = trace.to_bytes()
        seal = trace.seal()
        resume_key = _sha256(_canonical(raw_payloads) + trace_bytes + _canonical(seal))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "results": self.output_root / "runtime_results.json",
            "audit": self.output_root / "runtime_audit.json",
            "failures": self.output_root / "failure_ledger.json",
            "trace": self.output_root / "runtime_trace.jsonl",
            "seal": self.output_root / "trace_seal.json",
            "receipt": self.output_root / "agent_receipt.json",
            "log": self.output_root / "agent_log.json",
            "manifest": self.output_root / "agent_manifest.json",
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
            "model": "AGENT_RUNTIME",
            "status": "VALID" if checks_passed else "INVALID",
            "fixture": True,
            "agents": len(agents),
            "tasks": len(tasks),
            "events": len(trace.records),
            "schema_validated": schema_validated,
            "tool_allowlist_passed": tool_allowlist_passed,
            "budget_passed": budget_passed,
            "replay_passed": replay_passed,
            "retry_passed": retry_passed,
            "trace_sealed": trace_sealed,
            "provider_key_required": RuleBackend.provider_key_required,
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
                    {
                        "event": "typed_contracts_validated",
                        "agents": len(agents),
                        "tasks": len(tasks),
                    },
                    {
                        "event": "allowlist_and_budget_negative_checks",
                        "passed": tool_allowlist_passed and budget_passed,
                    },
                    {"event": "deterministic_replay_completed", "passed": replay_passed},
                    {"event": "append_only_trace_sealed", "events": len(trace.records)},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "AGENT_RUNTIME",
                "status": receipt["status"],
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
                raise AgentRuntimeError("existing agent receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise AgentRuntimeError(f"existing agent artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return AgentRuntimeSummary(
            agents=len(agents),
            tasks=len(tasks),
            events=len(trace.records),
            schema_validated=schema_validated,
            tool_allowlist_passed=tool_allowlist_passed,
            budget_passed=budget_passed,
            replay_passed=replay_passed,
            retry_passed=retry_passed,
            trace_sealed=trace_sealed,
            provider_key_required=RuleBackend.provider_key_required,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
