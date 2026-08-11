#!/usr/bin/env python3
"""Validate the BioInterfaceOS Codex execution pack without third-party dependencies."""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md",
    "GOAL.md",
    "PLANS.md",
    "PROJECT_STATE.yaml",
    "TASKS.tsv",
    "TASKS.md",
    "CODEX_START_PROMPT.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def yaml_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*['\"]?([^'\"\n#]+)", text)
    return match.group(1).strip() if match else None


def validate_fences(path: Path) -> list[str]:
    errors: list[str] = []
    fence_lines = [i for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if line.lstrip().startswith("```")]
    if len(fence_lines) % 2:
        errors.append(f"{path.name}: odd number of Markdown code fences; last fence line {fence_lines[-1]}")
    return errors


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED:
        path = ROOT / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty required file: {name}")

    tasks_path = ROOT / "TASKS.tsv"
    rows: list[dict[str, str]] = []
    if tasks_path.is_file():
        with tasks_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            expected = {
                "id", "phase", "title", "depends_on", "status", "priority",
                "inputs", "outputs", "command", "acceptance", "failure_policy",
            }
            if set(reader.fieldnames or []) != expected:
                errors.append(f"TASKS.tsv columns differ: {reader.fieldnames}")
            rows = list(reader)

    ids = [row.get("id", "") for row in rows]
    duplicates = [task_id for task_id, count in Counter(ids).items() if count > 1]
    if duplicates:
        errors.append(f"duplicate task IDs: {duplicates}")
    known = set(ids)

    allowed_status = {"READY", "BLOCKED", "IN_PROGRESS", "DONE", "FAILED_RETRYABLE", "FAILED_FINAL", "WAIVED"}
    for row in rows:
        task_id = row.get("id", "<missing>")
        if not re.fullmatch(r"T\d{3}", task_id):
            errors.append(f"invalid task ID: {task_id}")
        if row.get("status") not in allowed_status:
            errors.append(f"{task_id}: invalid status {row.get('status')}")
        if not row.get("command") or not row.get("acceptance") or not row.get("failure_policy"):
            errors.append(f"{task_id}: command/acceptance/failure policy cannot be empty")
        for dep in filter(None, row.get("depends_on", "").split(",")):
            if dep not in known:
                errors.append(f"{task_id}: unknown dependency {dep}")

    # Kahn topological check.
    deps = {row["id"]: [d for d in row["depends_on"].split(",") if d] for row in rows if row.get("id")}
    indegree = {node: len(ds) for node, ds in deps.items()}
    children: dict[str, list[str]] = defaultdict(list)
    for node, ds in deps.items():
        for dep in ds:
            children[dep].append(node)
    queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(deps):
        errors.append("TASKS.tsv contains a dependency cycle")

    state_path = ROOT / "PROJECT_STATE.yaml"
    if state_path.is_file():
        state = state_path.read_text(encoding="utf-8")
        current = yaml_scalar(state, "current_task")
        if current not in known:
            errors.append(f"PROJECT_STATE current_task is not in TASKS.tsv: {current}")
        declared_count = yaml_scalar(state, "task_count")
        if declared_count is not None and int(declared_count) != len(rows):
            errors.append(f"PROJECT_STATE task_count={declared_count}, actual={len(rows)}")

    for name in ["AGENTS.md", "GOAL.md", "PLANS.md", "TASKS.md", "CODEX_START_PROMPT.md"]:
        path = ROOT / name
        if path.is_file():
            errors.extend(validate_fences(path))
            if not re.search(r"(?m)^#\s+", path.read_text(encoding="utf-8")):
                warnings.append(f"{name}: no level-1 heading")

    ready = [r["id"] for r in rows if r.get("status") == "READY"]
    if ready != ["T000"]:
        warnings.append(f"initial READY tasks are {ready}, expected ['T000']")

    audit_dir = ROOT / "reports"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "CONTRACT_AUDIT.md"
    hashes = {name: sha256(ROOT / name) for name in REQUIRED if (ROOT / name).is_file()}
    lines = [
        "# Execution Pack Contract Audit",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Root: `{ROOT}`",
        f"- Task count: {len(rows)}",
        f"- Topological task count: {len(order)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
        "## Errors",
        "",
    ]
    lines += [f"- {item}" for item in errors] or ["- None"]
    lines += ["", "## Warnings", ""]
    lines += [f"- {item}" for item in warnings] or ["- None"]
    lines += ["", "## Required-file SHA-256", ""]
    lines += [f"- `{name}`: `{digest}`" for name, digest in hashes.items()]
    lines += ["", "## Result", "", "PASS" if not errors else "FAIL", ""]
    audit_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Validated {len(rows)} tasks; errors={len(errors)} warnings={len(warnings)}")
    print(f"Audit: {audit_path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
