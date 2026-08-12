"""Offline hypothesis tournament freeze and preregistration workflow."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import _canonical, _mapping, _sha256
from biointerfaceos.lockbox import LockboxFirewall


class TournamentError(RuntimeError):
    """Raised when tournament preregistration or lockbox gates fail."""


@dataclass(frozen=True)
class TournamentSummary:
    """Summary of one frozen exploratory hypothesis tournament."""

    candidates: int
    ranked: int
    duplicates_removed: int
    exclusions: int
    config_frozen: bool
    lockbox_clean: bool
    claims_auto_accepted: bool
    selected_pipeline: str
    resumed: int
    receipt_path: Path


def _keys(value: dict[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise TournamentError(f"{label} fields do not match schema")


class HypothesisTournamentWorkflow:
    """Freeze ranking rules before ranking training-only exploratory candidates."""

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
            self.root / "tests/fixtures/agents/tournament_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/claims/tournament"
        self.schema_path = schema_path or self.root / "agents/claims/tournament.v1.json"

    def _schema_valid(self) -> bool:
        try:
            schema = _mapping(
                json.loads(self.schema_path.read_text(encoding="utf-8")),
                "tournament schema",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TournamentError(f"cannot load tournament schema: {exc}") from exc
        _keys(
            schema,
            {"schema_version", "claim_type", "config_fields", "candidate_fields"},
            "tournament schema",
        )
        if (
            schema.get("schema_version") != 1
            or schema.get("claim_type") != "exploratory_hypothesis"
        ):
            raise TournamentError("tournament schema version or claim type is invalid")
        if not isinstance(schema.get("config_fields"), list) or not isinstance(
            schema.get("candidate_fields"), list
        ):
            raise TournamentError("tournament schema fields are invalid")
        return True

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "tournament fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TournamentError(f"cannot load tournament fixture: {exc}") from exc
        _keys(
            fixture,
            {"schema_version", "mode", "inputs", "config", "candidate_records"},
            "tournament fixture",
        )
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "tournament_fixture":
            raise TournamentError("tournament fixture schema or mode is invalid")
        if not isinstance(fixture.get("inputs"), list) or not isinstance(
            fixture.get("candidate_records"), list
        ):
            raise TournamentError("tournament fixture inputs or candidates are invalid")
        return fixture

    def _inputs(self, fixture: dict[str, Any]) -> tuple[dict[str, Any], ...]:
        expected = {
            "T084 hypothesis proposals": (
                self.root / "reports/agents/hypothesis/hypothesis_proposals.json",
                "8f133a7636bbb5ffb1104f55fced7aecb9cbf4deebf148b5a69624e6beebcbb4",
            ),
            "T085 preregistration": (
                self.root / "reports/agents/modeling/preregistration.json",
                "beb39ee7cf2f58fd1c89d6a33791cc3e5fd4773a7c3961e6538fc4f2d3834801",
            ),
            "T065 frozen split": (
                self.root / "reports/splits/frozen_dev/split_manifest.json",
                "c1b32d9b2b23cca7ec9ba7bf7cc0471514fdf2a0fb07a3204461b5b8cfa150c2",
            ),
        }
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for value in fixture["inputs"]:
            row = _mapping(value, "tournament input")
            _keys(row, {"label", "path", "sha256", "split"}, "tournament input")
            label = row.get("label")
            if label not in expected:
                raise TournamentError(f"unexpected tournament input: {label}")
            path, checksum = expected[label]
            declared = (self.root / row["path"]).resolve(strict=True)
            if declared != path.resolve(strict=True) or row["sha256"] != checksum:
                raise TournamentError(f"tournament input path or checksum differs: {label}")
            if _sha256(path.read_bytes()) != checksum:
                raise TournamentError(f"tournament input checksum differs: {label}")
            rows.append({"label": label, "path": row["path"], "split": row["split"]})
            seen.add(label)
        if seen != set(expected):
            raise TournamentError("tournament inputs are incomplete")
        proposals = _mapping(
            json.loads(expected["T084 hypothesis proposals"][0].read_text(encoding="utf-8")),
            "hypothesis proposals",
        )
        if proposals.get("target_values_exposed") is not False:
            raise TournamentError("hypothesis proposals expose target values")
        if any(
            row.get("status") != "EXPLORATORY_PROPOSAL"
            or row.get("claim_accepted") is not False
            or row.get("split") != "train"
            for row in proposals.get("proposals", [])
        ):
            raise TournamentError("tournament input contains non-exploratory proposal")
        prereg = _mapping(
            json.loads(expected["T085 preregistration"][0].read_text(encoding="utf-8")),
            "modeling preregistration",
        )
        if prereg.get("complete") is not True or prereg.get("target_values_exposed") is not False:
            raise TournamentError("modeling preregistration is incomplete")
        return tuple(rows)

    @staticmethod
    def _config(value: Any) -> dict[str, Any]:
        config = _mapping(value, "tournament config")
        required = {
            "version",
            "K",
            "primary_outcome",
            "direction",
            "minimum_effect",
            "weights",
            "exclusion_rules",
            "tests",
            "frozen_before_primary",
        }
        _keys(config, required, "tournament config")
        if config["version"] != "T089-v1" or not isinstance(config["K"], int) or config["K"] < 1:
            raise TournamentError("tournament config version or K is invalid")
        if (
            config["direction"] not in {"minimize", "maximize"}
            or config["frozen_before_primary"] is not True
        ):
            raise TournamentError("tournament config freeze or direction is invalid")
        weights = _mapping(config["weights"], "tournament weights")
        if set(weights) != {"evidence", "falsifiability", "formalization", "simplicity"}:
            raise TournamentError("tournament weights are invalid")
        if abs(sum(weights.values()) - 1.0) > 1e-9 or any(
            not isinstance(weight, int | float) or weight < 0 for weight in weights.values()
        ):
            raise TournamentError("tournament weights must be nonnegative and sum to one")
        if not isinstance(config["exclusion_rules"], list) or not config["exclusion_rules"]:
            raise TournamentError("tournament exclusion rules are missing")
        if not isinstance(config["tests"], list) or not config["tests"]:
            raise TournamentError("tournament tests are missing")
        return config

    def _lockbox(self, inputs: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        firewall = LockboxFirewall(self.root)
        report = firewall.scan([self.root / row["path"] for row in inputs])
        return {
            "schema_version": 1,
            "clean": report.clean,
            "checked_paths": list(report.checked_paths),
            "findings": [finding.__dict__ for finding in report.findings],
            "locked_payload_opened": False,
        }

    def run(self, *, development: bool = True) -> TournamentSummary:
        """Freeze config, deduplicate candidates, rank, and persist preregistration."""
        if not development:
            raise TournamentError("--dev is required for tournament preregistration")
        schema_valid = self._schema_valid()
        fixture = self._fixture()
        inputs = self._inputs(fixture)
        config = self._config(fixture["config"])
        config_bytes = _canonical(config)
        config_hash = _sha256(config_bytes)
        lockbox = self._lockbox(inputs)
        proposals = {
            row["case_id"]: row
            for row in _mapping(
                json.loads(
                    (self.root / "reports/agents/hypothesis/hypothesis_proposals.json").read_text(
                        encoding="utf-8"
                    )
                ),
                "hypothesis proposals",
            )["proposals"]
        }
        candidates = []
        for value in fixture["candidate_records"]:
            row = _mapping(value, "tournament candidate")
            _keys(
                row,
                {"candidate_id", "source_case_id", "normalized_key", "split"},
                "tournament candidate",
            )
            source = proposals.get(row["source_case_id"])
            if source is None or row["split"] != "train" or source["split"] != "train":
                raise TournamentError(f"candidate is not training-only: {row.get('candidate_id')}")
            candidates.append({"fixture": row, "source": source})
        seen_keys: set[str] = set()
        ranked: list[dict[str, Any]] = []
        exclusions: list[dict[str, Any]] = []
        weights = config["weights"]
        for candidate in candidates:
            fixture_row = candidate["fixture"]
            source = candidate["source"]
            key = fixture_row["normalized_key"]
            if key in seen_keys:
                exclusions.append(
                    {
                        "candidate_id": fixture_row["candidate_id"],
                        "source_case_id": fixture_row["source_case_id"],
                        "reason": "DUPLICATE_NORMALIZED_HYPOTHESIS",
                        "preserved": True,
                    }
                )
                continue
            seen_keys.add(key)
            evidence_score = min(1.0, len(source["evidence_links"]) / 2)
            falsifiability_score = 1.0 if source["falsifiability"]["test"] else 0.0
            formalization_score = 1.0 if source["formalization"]["equation"] else 0.0
            simplicity_score = 1.0 if len(source["formalization"]["variables"]) <= 3 else 0.5
            score = round(
                weights["evidence"] * evidence_score
                + weights["falsifiability"] * falsifiability_score
                + weights["formalization"] * formalization_score
                + weights["simplicity"] * simplicity_score,
                6,
            )
            ranked.append(
                {
                    "rank": 0,
                    "candidate_id": fixture_row["candidate_id"],
                    "source_case_id": fixture_row["source_case_id"],
                    "normalized_key": key,
                    "score": score,
                    "status": "EXPLORATORY_RANKED",
                    "claim_accepted": False,
                    "split": "train",
                    "evidence_links": source["evidence_links"],
                    "falsifiability": source["falsifiability"],
                    "formalization": source["formalization"],
                }
            )
        ranked.sort(key=lambda row: (-row["score"], row["candidate_id"]))
        for index, row in enumerate(ranked, start=1):
            row["rank"] = index
        ranked = ranked[: config["K"]]
        if not schema_valid or not lockbox["clean"] or not ranked:
            raise TournamentError("tournament gate failed")
        rank_bytes = _canonical(ranked)
        receipt_hash = _sha256(config_bytes + rank_bytes)
        comparison = {
            "schema_version": 1,
            "K": config["K"],
            "candidates": len(candidates),
            "ranked": len(ranked),
            "duplicates_removed": len(exclusions),
            "exclusions": len(exclusions),
            "config_hash": config_hash,
            "ranking_hash": _sha256(rank_bytes),
            "receipt_hash": receipt_hash,
            "config_frozen": True,
            "primary_analysis_started_after_freeze": True,
            "lockbox_clean": lockbox["clean"],
            "claims_auto_accepted": False,
            "target_values_exposed": False,
        }
        raw_payloads = {
            "config": config,
            "ranking": {"schema_version": 1, "ranked": ranked},
            "exclusions": {"schema_version": 1, "exclusions": exclusions},
            "lockbox": lockbox,
            "comparison": comparison,
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "config": self.output_root / "tournament_config.json",
            "ranking": self.output_root / "hypothesis_ranking.json",
            "exclusions": self.output_root / "exclusion_ledger.json",
            "lockbox": self.output_root / "lockbox_scan.json",
            "comparison": self.output_root / "tournament_comparison.json",
            "receipt_hash": self.output_root / "preregistration_hash_receipt.json",
            "receipt": self.output_root / "preregistration_receipt.json",
            "manifest": self.output_root / "tournament_manifest.json",
        }
        payloads = {name: _canonical(value) for name, value in raw_payloads.items()}
        payloads["receipt_hash"] = _canonical(
            {
                "schema_version": 1,
                "config_hash": config_hash,
                "ranking_hash": _sha256(rank_bytes),
                "receipt_hash": receipt_hash,
                "frozen_before_primary": True,
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
            "model": "HYPOTHESIS_TOURNAMENT_PREREGISTRATION",
            "status": "FROZEN_EXPLORATORY",
            "fixture": True,
            "K": config["K"],
            "candidates": len(candidates),
            "ranked": len(ranked),
            "duplicates_removed": len(exclusions),
            "config_frozen": True,
            "lockbox_clean": lockbox["clean"],
            "claims_auto_accepted": False,
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payloads["receipt"] = _canonical(receipt)
        payloads["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "HYPOTHESIS_TOURNAMENT_PREREGISTRATION",
                "status": "FROZEN_EXPLORATORY",
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
                raise TournamentError("existing preregistration receipt differs from rerun")
            for name, payload in payloads.items():
                if paths[name].read_bytes() != payload:
                    raise TournamentError(f"existing tournament artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payloads.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return TournamentSummary(
            candidates=len(candidates),
            ranked=len(ranked),
            duplicates_removed=len(exclusions),
            exclusions=len(exclusions),
            config_frozen=True,
            lockbox_clean=lockbox["clean"],
            claims_auto_accepted=False,
            selected_pipeline="preregistered_tournament",
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
