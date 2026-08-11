"""Material alias and formulation graph resolution."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class MaterialResolutionError(ValueError):
    """Raised when a material/formulation fixture violates its contract."""


@dataclass(frozen=True)
class MaterialResolutionSummary:
    """Counts and output paths from one fixture run."""

    mentions: int
    resolved_entities: int
    ambiguous_mentions: int
    formulations: int
    valid_formulations: int
    graph_edges: int
    review_items: int
    entities_path: Path
    graphs_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _float(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise MaterialResolutionError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise MaterialResolutionError(f"{name} must be finite")
    return result


class MaterialResolver:
    """Resolve material mentions and build role-aware formulation graphs."""

    ROLES = frozenset({"core_material", "coating_material", "ligand", "polymer", "lipid"})
    MATERIAL_CLASSES = frozenset({"lipid", "polymer", "ligand"})

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        entities_path: Path | None = None,
        graphs_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/materials/material_resolution.json"
        )
        self.entities_path = entities_path or (self.root / "registry/material_entities.json")
        self.graphs_path = graphs_path or (self.root / "registry/formulation_graphs.json")
        self.review_path = review_path or (self.root / "registry/material_review_queue.jsonl")
        self.report_path = report_path or self.root / "reports/material_resolution.md"

    @staticmethod
    def _load_fixture(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MaterialResolutionError(f"cannot load material fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {
            "schema_version",
            "mentions",
            "formulations",
        }:
            raise MaterialResolutionError("material fixture envelope is invalid")
        if value["schema_version"] != 1:
            raise MaterialResolutionError("material fixture schema is invalid")
        if not isinstance(value["mentions"], list) or not isinstance(value["formulations"], list):
            raise MaterialResolutionError("material mentions or formulations are invalid")
        mentions = [dict(item) for item in value["mentions"] if isinstance(item, Mapping)]
        formulations = [dict(item) for item in value["formulations"] if isinstance(item, Mapping)]
        if len(mentions) != len(value["mentions"]) or len(formulations) != len(
            value["formulations"]
        ):
            raise MaterialResolutionError("material fixture contains a non-object")
        return mentions, formulations

    def _resolve_mentions(
        self,
        mentions: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        entities: list[dict[str, Any]] = []
        by_mention: dict[str, dict[str, Any]] = {}
        required = {
            "mention_id",
            "raw_text",
            "role_hint",
            "source_locator",
            "candidates",
        }
        candidate_required = {
            "entity_id",
            "canonical_label",
            "material_class",
            "structure_id",
            "resolution_method",
            "confidence",
            "alias_kind",
        }
        for raw in mentions:
            if set(raw) != required:
                raise MaterialResolutionError("material mention fields are invalid")
            mention_id = _text(raw["mention_id"])
            raw_text = _text(raw["raw_text"])
            locator = _text(raw["source_locator"])
            role_hint = _text(raw["role_hint"])
            candidates_raw = raw["candidates"]
            if not mention_id or not raw_text or not locator.startswith("asset:"):
                raise MaterialResolutionError("material mention identifiers or locator are invalid")
            if not isinstance(candidates_raw, list) or not candidates_raw:
                raise MaterialResolutionError(f"{mention_id} has no candidates")
            candidates: list[dict[str, Any]] = []
            for candidate in candidates_raw:
                if not isinstance(candidate, Mapping) or set(candidate) != candidate_required:
                    raise MaterialResolutionError(f"{mention_id} candidate fields are invalid")
                material_class = _text(candidate["material_class"]).lower()
                confidence = _float(candidate["confidence"], f"{mention_id}.confidence")
                if material_class not in self.MATERIAL_CLASSES or not 0.0 <= confidence <= 1.0:
                    raise MaterialResolutionError(
                        f"{mention_id} candidate class/confidence invalid"
                    )
                candidates.append(dict(candidate))
            candidates.sort(key=lambda item: float(item["confidence"]), reverse=True)
            resolved = len(candidates) == 1 and float(candidates[0]["confidence"]) >= 0.8
            status = "RESOLVED" if resolved else "AMBIGUOUS"
            if not resolved:
                reviews.append(
                    {
                        "review_id": f"ambiguous-material:{mention_id}",
                        "reason": "AMBIGUOUS_MATERIAL_MENTION",
                        "mention_id": mention_id,
                        "raw_text": raw_text,
                        "source_locator": locator,
                        "candidate_entity_ids": [item["entity_id"] for item in candidates],
                        "resolution": "MANUAL_REVIEW",
                    }
                )
            entity = {
                "mention_id": mention_id,
                "raw_text": raw_text,
                "role_hint": role_hint,
                "source_locator": locator,
                "status": status,
                "resolved_entity": candidates[0] if resolved else None,
                "candidate_aliases": candidates,
            }
            entities.append(entity)
            by_mention[mention_id] = entity
        return entities, by_mention

    def _formulation_graphs(
        self,
        formulations: list[dict[str, Any]],
        by_mention: Mapping[str, dict[str, Any]],
        reviews: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int, int]:
        graphs: list[dict[str, Any]] = []
        valid_count = 0
        edge_count = 0
        required = {"formulation_id", "source_locator", "components"}
        component_required = {"mention_id", "role", "fraction", "fraction_basis", "source_locator"}
        for raw in formulations:
            if set(raw) != required:
                raise MaterialResolutionError("formulation fields are invalid")
            formulation_id = _text(raw["formulation_id"])
            locator = _text(raw["source_locator"])
            raw_components = raw["components"]
            if not formulation_id or not locator.startswith("asset:"):
                raise MaterialResolutionError("formulation identifiers or locator are invalid")
            if not isinstance(raw_components, list) or not raw_components:
                raise MaterialResolutionError(f"{formulation_id} has no components")
            components: list[dict[str, Any]] = []
            for raw_component in raw_components:
                if (
                    not isinstance(raw_component, Mapping)
                    or set(raw_component) != component_required
                ):
                    raise MaterialResolutionError(f"{formulation_id} component fields are invalid")
                mention_id = _text(raw_component["mention_id"])
                role = _text(raw_component["role"]).lower()
                fraction = _float(
                    raw_component["fraction"],
                    f"{formulation_id}.{mention_id}.fraction",
                )
                basis = _text(raw_component["fraction_basis"])
                component_locator = _text(raw_component["source_locator"])
                if mention_id not in by_mention or role not in self.ROLES:
                    raise MaterialResolutionError(
                        f"{formulation_id} component identity/role invalid"
                    )
                if (
                    not 0.0 <= fraction <= 1.0
                    or not basis
                    or not component_locator.startswith("asset:")
                ):
                    raise MaterialResolutionError(f"{formulation_id} component fraction invalid")
                mention = by_mention[mention_id]
                component_status = "RESOLVED" if mention["status"] == "RESOLVED" else "UNRESOLVED"
                components.append(
                    {
                        "mention_id": mention_id,
                        "entity_id": (
                            mention["resolved_entity"]["entity_id"]
                            if component_status == "RESOLVED"
                            else None
                        ),
                        "role": role,
                        "fraction": fraction,
                        "fraction_basis": basis,
                        "source_locator": component_locator,
                        "status": component_status,
                    }
                )
            total = sum(float(component["fraction"]) for component in components)
            basis_values = {component["fraction_basis"] for component in components}
            valid = (
                abs(total - 1.0) <= 1e-9
                and len(basis_values) == 1
                and all(component["status"] == "RESOLVED" for component in components)
            )
            if not valid:
                reason = (
                    "MIXTURE_FRACTIONS_DO_NOT_SUM_TO_ONE"
                    if abs(total - 1.0) > 1e-9 or len(basis_values) != 1
                    else "FORMULATION_HAS_UNRESOLVED_MATERIAL"
                )
                reviews.append(
                    {
                        "review_id": f"formulation-review:{formulation_id}",
                        "reason": reason,
                        "formulation_id": formulation_id,
                        "source_locator": locator,
                        "fraction_total": total,
                        "resolution": "MANUAL_REVIEW",
                    }
                )
            else:
                valid_count += 1
            nodes = [component["entity_id"] for component in components if component["entity_id"]]
            edges: list[dict[str, Any]] = []
            if nodes:
                core = nodes[0]
                for target in nodes[1:]:
                    edges.append(
                        {
                            "edge_id": f"{formulation_id}:{core}->{target}",
                            "formulation_id": formulation_id,
                            "source_entity_id": core,
                            "target_entity_id": target,
                            "relation": "FORMULATION_COMPONENT",
                            "status": "RESOLVED" if valid else "UNRESOLVED",
                        }
                    )
            edge_count += len(edges)
            graphs.append(
                {
                    "formulation_id": formulation_id,
                    "source_locator": locator,
                    "fraction_total": total,
                    "fraction_basis": sorted(basis_values)[0] if len(basis_values) == 1 else None,
                    "valid": valid,
                    "components": components,
                    "edges": edges,
                }
            )
        return graphs, valid_count, edge_count

    def run(self) -> MaterialResolutionSummary:
        """Resolve mentions, build formulation graphs, and write review evidence."""
        mentions, formulations = self._load_fixture(self.fixture_path)
        reviews: list[dict[str, Any]] = []
        entities, by_mention = self._resolve_mentions(mentions, reviews)
        graphs, valid_formulations, edge_count = self._formulation_graphs(
            formulations, by_mention, reviews
        )
        self.entities_path.parent.mkdir(parents=True, exist_ok=True)
        self.entities_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "entities": entities},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.graphs_path.parent.mkdir(parents=True, exist_ok=True)
        self.graphs_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "formulations": graphs},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        review_ledger = AppendOnlyJSONL(self.review_path)
        review_ledger.initialize()
        existing = {
            json.loads(line).get("review_id")
            for line in review_ledger.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for review in reviews:
            if review["review_id"] not in existing:
                review_ledger.append(review)

        resolved_count = sum(entity["status"] == "RESOLVED" for entity in entities)
        ambiguous_count = sum(entity["status"] == "AMBIGUOUS" for entity in entities)
        report = (
            "\n".join(
                [
                    "# Material and Formulation Resolution Report",
                    "",
                    "Aliases, structures, roles, and mixture fractions retain source provenance.",
                    "",
                    f"- mentions: {len(mentions)}",
                    f"- resolved entities: {resolved_count}",
                    f"- ambiguous mentions: {ambiguous_count}",
                    f"- formulations: {len(formulations)}",
                    f"- valid formulations: {valid_formulations}",
                    f"- graph edges: {edge_count}",
                    f"- review items: {len(reviews)}",
                    "",
                    "Ambiguous trade names and invalid fraction bases remain unresolved.",
                ]
            )
            + "\n"
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(report, encoding="utf-8")
        return MaterialResolutionSummary(
            mentions=len(mentions),
            resolved_entities=sum(entity["status"] == "RESOLVED" for entity in entities),
            ambiguous_mentions=sum(entity["status"] == "AMBIGUOUS" for entity in entities),
            formulations=len(formulations),
            valid_formulations=valid_formulations,
            graph_edges=edge_count,
            review_items=len(reviews),
            entities_path=self.entities_path,
            graphs_path=self.graphs_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
