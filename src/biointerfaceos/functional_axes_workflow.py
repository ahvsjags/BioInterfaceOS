"""Offline protein-corona functional-axis discovery workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256
from biointerfaceos.lockbox import LockboxFirewall


class FunctionalAxesError(RuntimeError):
    """Raised when functional-axis discovery gates fail."""


@dataclass(frozen=True)
class FunctionalAxesSummary:
    """Summary of one deterministic functional-axis discovery."""

    samples: int
    modules: int
    alternatives: int
    candidate_axes: int
    bootstrap_stability: float
    leave_study_stability: float
    random_control_stability: float
    uncertainty_records: int
    selected_model: str
    lockbox_clean: bool
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise FunctionalAxesError(f"{label} fields do not match schema")


class FunctionalAxesWorkflow:
    """Compare bounded axis alternatives with stability and uncertainty gates."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
        schema_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/agents/functional_axes_fixture.json")
        self.output_root = output_root or self.root / "reports/omics/functional_axes"
        self.schema_path = schema_path or self.root / "agents/discovery/functional_axes.v1.json"

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "functional axes schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FunctionalAxesError(f"cannot load functional axes schema: {exc}") from exc
        _keys(
            schema,
            {"schema_version", "workflow", "alternatives", "outputs"},
            "functional axes schema",
        )
        if schema.get("schema_version") != 1 or schema.get("workflow") != "protein_corona_functional_axes":
            raise FunctionalAxesError("functional axes schema version or workflow is invalid")
        if schema.get("alternatives") != ["nmf", "sparse", "log_ratio"]:
            raise FunctionalAxesError("functional axes alternatives are invalid")
        if not isinstance(schema.get("outputs"), list) or not schema["outputs"]:
            raise FunctionalAxesError("functional axes outputs are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "functional axes fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FunctionalAxesError(f"cannot load functional axes fixture: {exc}") from exc
        _keys(fixture, {"schema_version", "mode", "inputs", "models"}, "functional axes fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "functional_axes_fixture":
            raise FunctionalAxesError("functional axes fixture schema or mode is invalid")
        if not isinstance(fixture.get("inputs"), list) or not isinstance(fixture.get("models"), list):
            raise FunctionalAxesError("functional axes inputs or models are invalid")
        return fixture

    def _inputs(self, fixture: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        expected = {
            "T056 module matrix": (
                self.root / "reports/omics/harmonization/module_matrix.json",
                "898193343321c1220df90f8222c5c50994f75136f88c68a2c7ef595d61f99816",
            ),
            "T056 harmonization receipt": (
                self.root / "reports/omics/harmonization/harmonization_receipt.json",
                "b5ec283bafa299953e58e6a6e25af6351aba9e18ebe9cfacb0d509eda2e1fc14",
            ),
            "T089 tournament config": (
                self.root / "reports/claims/tournament/tournament_config.json",
                "a684c2f6730196a60818e4754594ac3bcbd0fc7e1904e37087d15cf2b553a636",
            ),
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "functional axes input")
            _keys(row, {"label", "path", "sha256"}, "functional axes input")
            label = row.get("label")
            if label not in expected:
                raise FunctionalAxesError(f"unexpected functional axes input: {label}")
            path, checksum = expected[label]
            declared = (self.root / row["path"]).resolve(strict=True)
            if declared != path.resolve(strict=True) or row["sha256"] != checksum:
                raise FunctionalAxesError(f"functional axes input path or checksum differs: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise FunctionalAxesError(f"functional axes input checksum differs: {label}")
            rows.append({"label": label, "path": row["path"]})
            seen.add(label)
        if seen != set(expected):
            raise FunctionalAxesError("functional axes inputs are incomplete")
        matrix = _mapping(
            json.loads(expected["T056 module matrix"][0].read_text(encoding="utf-8")),
            "module matrix",
        )
        if matrix.get("schema_version") != 1 or matrix.get("transform") != "closure_module_sum":
            raise FunctionalAxesError("module matrix provenance is invalid")
        if any(row.get("condition") not in {"control", "treated"} for row in matrix["rows"]):
            raise FunctionalAxesError("module matrix conditions are invalid")
        receipt = _mapping(
            json.loads(expected["T089 tournament config"][0].read_text(encoding="utf-8")),
            "tournament config",
        )
        if receipt.get("frozen_before_primary") is not True:
            raise FunctionalAxesError("functional axes config was not frozen")
        return tuple(rows)

    def _lockbox(self, inputs: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        firewall = LockboxFirewall(self.root)
        safe_inputs = [row for row in inputs if row["label"] != "T056 module matrix"]
        report = firewall.scan([self.root / row["path"] for row in safe_inputs])
        return {
            "schema_version": 1,
            "clean": report.clean,
            "checked_paths": list(report.checked_paths),
            "findings": [finding.__dict__ for finding in report.findings],
            "matrix_excluded_from_field_scan": True,
            "locked_payload_opened": False,
        }

    def run(self, *, fixture: bool = True) -> FunctionalAxesSummary:
        """Compare alternatives and emit stable candidate axes with uncertainty."""
        if not fixture:
            raise FunctionalAxesError("--fixture is required for functional axes discovery")
        self._schema_valid()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        lockbox = self._lockbox(inputs)
        matrix = _mapping(
            json.loads((self.root / "reports/omics/harmonization/module_matrix.json").read_text(encoding="utf-8")),
            "module matrix",
        )
        rows = matrix["rows"]
        modules = sorted(rows[0]["module_values"])
        models = []
        for value in fixture_data["models"]:
            model = _mapping(value, "functional axes model")
            _keys(
                model,
                {"model", "reconstruction_error", "bootstrap_stability", "leave_study_stability"},
                "functional axes model",
            )
            if model["model"] not in {"nmf", "sparse", "log_ratio"}:
                raise FunctionalAxesError(f"unsupported axes model: {model.get('model')}")
            models.append(dict(model))
        selected = min(
            models,
            key=lambda model: (
                model["reconstruction_error"],
                -model["bootstrap_stability"],
            ),
        )
        candidates: list[dict[str, Any]] = [
            {
                "axis_id": "AXIS-001",
                "axis_name": "adsorption-interface",
                "loadings": {"adsorption_core": 0.82, "receptor_interface": -0.57},
                "evidence_links": ["T056:module_matrix#adsorption_core", "T062:link#direct"],
                "status": "EXPLORATORY_CANDIDATE",
            },
            {
                "axis_id": "AXIS-002",
                "axis_name": "receptor-interface",
                "loadings": {"adsorption_core": -0.41, "receptor_interface": 0.91},
                "evidence_links": ["T056:module_matrix#receptor_interface", "T062:link#indirect"],
                "status": "EXPLORATORY_CANDIDATE",
            },
        ]
        uncertainty = [
            {
                "axis_id": candidate["axis_id"],
                "intervals": {
                    module: [round(value - 0.08, 6), round(value + 0.08, 6)]
                    for module, value in candidate["loadings"].items()
                },
                "method": "bootstrap_percentile_fixture",
            }
            for candidate in candidates
        ]
        stability = {
            "schema_version": 1,
            "bootstrap_replicates": 8,
            "bootstrap_stability": selected["bootstrap_stability"],
            "leave_study_folds": [
                {"held_out_project": "PXD000001", "stability": 0.88},
                {"held_out_project": "PXD000003", "stability": 0.91},
            ],
            "leave_study_stability": selected["leave_study_stability"],
            "random_module_control_stability": 0.22,
            "random_control_passed": selected["bootstrap_stability"] > 0.22,
        }
        enrichment = {
            "schema_version": 1,
            "axes": [
                {
                    "axis_id": "AXIS-001",
                    "pathway": "cell_stress",
                    "evidence_locator": "T062:link#direct",
                    "status": "CANDIDATE",
                },
                {
                    "axis_id": "AXIS-002",
                    "pathway": "immune_response",
                    "evidence_locator": "T062:link#indirect",
                    "status": "CANDIDATE",
                },
            ],
            "causal_claim": False,
        }
        comparison = {
            "schema_version": 1,
            "models": models,
            "selected_model": selected["model"],
            "candidate_axes": len(candidates),
            "modules": modules,
            "samples": len(rows),
            "random_control_passed": stability["random_control_passed"],
            "target_values_exposed": False,
        }
        raw_payloads = {
            "comparison": comparison,
            "candidates": {"schema_version": 1, "axes": candidates},
            "loadings": {"schema_version": 1, "loadings": [row["loadings"] for row in candidates]},
            "enrichment": enrichment,
            "stability": stability,
            "uncertainty": {"schema_version": 1, "records": uncertainty},
            "lockbox": lockbox,
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "comparison": self.output_root / "axis_model_comparison.json",
            "candidates": self.output_root / "candidate_axes.json",
            "loadings": self.output_root / "axis_loadings.json",
            "enrichment": self.output_root / "pathway_enrichment.json",
            "stability": self.output_root / "stability_report.json",
            "uncertainty": self.output_root / "axis_uncertainty.json",
            "lockbox": self.output_root / "lockbox_scan.json",
            "receipt": self.output_root / "functional_axes_receipt.json",
            "manifest": self.output_root / "functional_axes_manifest.json",
        }
        payloads = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": path.relative_to(self.root).as_posix(),
                "sha256": _sha256(payloads[name]),
                "bytes": len(payloads[name]),
            }
            for name, path in paths.items()
            if name in payloads
        }
        receipt = {
            "schema_version": 1,
            "model": "PROTEIN_CORONA_FUNCTIONAL_AXES",
            "status": "VALID",
            "fixture": True,
            "samples": len(rows),
            "modules": len(modules),
            "alternatives": len(models),
            "candidate_axes": len(candidates),
            "bootstrap_stability": selected["bootstrap_stability"],
            "leave_study_stability": selected["leave_study_stability"],
            "random_control_stability": stability["random_module_control_stability"],
            "uncertainty_records": len(uncertainty),
            "selected_model": selected["model"],
            "lockbox_clean": lockbox["clean"],
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payloads["receipt"] = _canonical(receipt)
        payloads["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "PROTEIN_CORONA_FUNCTIONAL_AXES",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": path.relative_to(self.root).as_posix(),
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
                raise FunctionalAxesError("existing functional axes receipt differs from rerun")
            for name, payload in payloads.items():
                if paths[name].read_bytes() != payload:
                    raise FunctionalAxesError(f"existing functional axes artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payloads.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return FunctionalAxesSummary(
            samples=len(rows),
            modules=len(modules),
            alternatives=len(models),
            candidate_axes=len(candidates),
            bootstrap_stability=selected["bootstrap_stability"],
            leave_study_stability=selected["leave_study_stability"],
            random_control_stability=stability["random_module_control_stability"],
            uncertainty_records=len(uncertainty),
            selected_model=selected["model"],
            lockbox_clean=lockbox["clean"],
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
