# BioInterfaceOS ExecPlan Standard

For every task expected to require more than a small isolated patch, create or update an ExecPlan in `docs/execplans/<TASK_ID>_<slug>.md`.

An ExecPlan is a living document. It must remain understandable to a new Codex session with no access to previous chat history.

## Required structure

```markdown
# <TASK_ID>: <title>

## Purpose
What scientific or engineering capability this task creates and why it is needed.

## Preconditions
Dependencies, required files, available data and environmental assumptions.

## Non-goals
What this task deliberately does not attempt.

## Interfaces and invariants
Input/output schemas, public functions, command-line interfaces and rules that must remain true.

## Implementation plan
A concrete ordered list of edits and commands. Include paths and expected intermediate artifacts.

## Progress
- [ ] timestamp — item
- [x] timestamp — completed item and evidence

## Discoveries
Unexpected behavior, data limitations, useful observations and implications.

## Decisions
Decision, alternatives considered and reason.

## Validation
Exact commands, expected results and acceptance thresholds.

## Failure recovery
How to resume safely, clean partial outputs and avoid data corruption.

## Outputs
Files, tables, reports, tests and commit expected at completion.

## Completion note
What was accomplished, remaining limitations and links to ledger records.
```

## Planning rules

- Start from observable behavior and artifacts, not implementation buzzwords.
- Include exact paths and commands.
- Break work into checkpoints that independently leave the repository usable.
- Update the plan while working, not only at the end.
- Record deviations and negative findings.
- Do not declare an uncertain or untested assumption as fact.
- When a source or package changes, pin the tested version or implement a compatibility adapter.
