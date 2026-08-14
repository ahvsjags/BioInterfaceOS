"""Physical and statistical plausibility checks for extracted records."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.ledgers import AppendOnlyJSONL


class PlausibilityQCError(ValueError):
    """Raised when a QC fixture or output contract is invalid."""


@dataclass(frozen=True)
class QCSummary:
    """Counts and output paths from one plausibility-QC run."""

    records: int
    clean_controls: int
    injected_error_records: int
    flags: int
    critical_flags: int
    warning_flags: int
    quarantined_records: int
    false_positive_controls: int
    injected_error_records_flagged: int
    injected_error_recall: float
    review_items: int
    flags_path: Path
    quarantine_path: Path
    metrics_path: Path
    review_path: Path
    report_path: Path


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise PlausibilityQCError(f"{name} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PlausibilityQCError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise PlausibilityQCError(f"{name} must be finite")
    return result


class PlausibilityChecker:
    """Run deterministic range, duplication, and uncertainty plausibility rules."""

    CONCENTRATION_UNITS = frozenset(
        {
            "g/L",
            "mg/L",
            "ug/L",
            "µg/L",
            "mg/mL",
            "ug/mL",
            "µg/mL",
            "ng/mL",
            "mol/L",
            "mM",
            "uM",
            "µM",
        }
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        flags_path: Path | None = None,
        quarantine_path: Path | None = None,
        metrics_path: Path | None = None,
        review_path: Path | None = None,
        report_path: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/qc/records.json"
        self.flags_path = flags_path or self.root / "registry/qc_flags.json"
        self.quarantine_path = quarantine_path or self.root / "registry/qc_quarantine.json"
        self.metrics_path = metrics_path or self.root / "reports/qc_metrics.json"
        self.review_path = review_path or self.root / "registry/qc_review_queue.jsonl"
        self.report_path = report_path or self.root / "reports/qc_records.md"

    @staticmethod
    def _load_fixture(path: Path) -> list[dict[str, Any]]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlausibilityQCError(f"cannot load QC fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "records"}:
            raise PlausibilityQCError("QC fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["records"], list):
            raise PlausibilityQCError("QC fixture schema is invalid")
        records: list[dict[str, Any]] = []
        for raw_record in value["records"]:
            if not isinstance(raw_record, Mapping):
                raise PlausibilityQCError("QC fixture contains a non-object record")
            if set(raw_record) != {
                "record_id",
                "source_locator",
                "control",
                "injected_error",
                "fields",
            }:
                raise PlausibilityQCError("QC record schema is invalid")
            record_id = _text(raw_record["record_id"])
            locator = _text(raw_record["source_locator"])
            if (
                not record_id
                or not locator.startswith("asset:")
                or not isinstance(raw_record["control"], bool)
                or not isinstance(raw_record["injected_error"], bool)
                or not isinstance(raw_record["fields"], list)
                or not raw_record["fields"]
            ):
                raise PlausibilityQCError(f"{record_id or '<unknown>'} identity/schema is invalid")
            fields: list[dict[str, Any]] = []
            for raw_field in raw_record["fields"]:
                if not isinstance(raw_field, Mapping) or set(raw_field) != {
                    "field_name",
                    "value",
                    "unit",
                    "source_locator",
                }:
                    raise PlausibilityQCError(f"{record_id} field schema is invalid")
                field_name = _text(raw_field["field_name"])
                field_locator = _text(raw_field["source_locator"])
                if not field_name or not field_locator.startswith("asset:") or not _text(raw_field["unit"]):
                    raise PlausibilityQCError(f"{record_id} field identity/unit is invalid")
                _number(raw_field["value"], f"{record_id}.{field_name}")
                fields.append(
                    {
                        "field_name": field_name,
                        "value": raw_field["value"],
                        "unit": _text(raw_field["unit"]),
                        "source_locator": field_locator,
                    }
                )
            records.append(
                {
                    "record_id": record_id,
                    "source_locator": locator,
                    "control": raw_record["control"],
                    "injected_error": raw_record["injected_error"],
                    "fields": fields,
                }
            )
        if len({record["record_id"] for record in records}) != len(records):
            raise PlausibilityQCError("QC record identifiers are not unique")
        return records

    @staticmethod
    def _flag(
        record: Mapping[str, Any],
        rule: str,
        severity: str,
        message: str,
        fields: list[Mapping[str, Any]],
    ) -> dict[str, Any]:
        field_name = fields[0]["field_name"] if fields else "record"
        flag_id = f"qc:{record['record_id']}:{rule}:{field_name}"
        return {
            "flag_id": flag_id,
            "record_id": record["record_id"],
            "rule": rule,
            "severity": severity,
            "weight": 1.0 if severity == "CRITICAL" else 0.5,
            "field_name": field_name,
            "values": [field["value"] for field in fields],
            "units": [field["unit"] for field in fields],
            "source_locators": [
                record["source_locator"],
                *(str(field["source_locator"]) for field in fields),
            ],
            "message": message,
            "control": record["control"],
            "injected_error": record["injected_error"],
            "resolution": "QUARANTINE" if severity == "CRITICAL" else "MANUAL_REVIEW",
        }

    @classmethod
    def _check_record(cls, record: Mapping[str, Any]) -> list[dict[str, Any]]:
        fields = list(record["fields"])
        by_name: dict[str, list[Mapping[str, Any]]] = {}
        for field in fields:
            by_name.setdefault(str(field["field_name"]).lower(), []).append(field)
        flags: list[dict[str, Any]] = []

        for field in fields:
            name = str(field["field_name"]).lower()
            value = float(field["value"])
            unit = str(field["unit"])
            if name == "fraction" and not 0.0 <= value <= 1.0:
                flags.append(
                    cls._flag(
                        record,
                        "FRACTION_OUT_OF_RANGE",
                        "CRITICAL",
                        "fraction must lie in [0, 1]",
                        [field],
                    )
                )
            if (name == "percent" or unit == "%") and not 0.0 <= value <= 100.0:
                flags.append(
                    cls._flag(
                        record,
                        "PERCENT_OUT_OF_RANGE",
                        "CRITICAL",
                        "percent must lie in [0, 100]",
                        [field],
                    )
                )
            if (name == "concentration" or unit in cls.CONCENTRATION_UNITS) and value < 0.0:
                flags.append(
                    cls._flag(
                        record,
                        "NEGATIVE_CONCENTRATION",
                        "CRITICAL",
                        "concentration cannot be negative",
                        [field],
                    )
                )
            if name in {"sd", "sem"} and value < 0.0:
                flags.append(
                    cls._flag(
                        record,
                        "NEGATIVE_DISPERSION",
                        "CRITICAL",
                        "standard deviation and standard error cannot be negative",
                        [field],
                    )
                )
            if name == "sample_size" and (value <= 0.0 or not value.is_integer()):
                flags.append(
                    cls._flag(
                        record,
                        "INVALID_SAMPLE_COUNT",
                        "CRITICAL",
                        "sample_size must be a positive integer",
                        [field],
                    )
                )

        sample_fields = by_name.get("sample_size", [])
        if len(sample_fields) > 1:
            flags.append(
                cls._flag(
                    record,
                    "DUPLICATE_SAMPLE_COUNT",
                    "CRITICAL",
                    "sample_size appears more than once in the same record",
                    sample_fields,
                )
            )
        sd_fields = by_name.get("sd", [])
        sem_fields = by_name.get("sem", [])
        if len(sample_fields) == 1 and len(sd_fields) == 1 and len(sem_fields) == 1:
            sample_size = float(sample_fields[0]["value"])
            sd = float(sd_fields[0]["value"])
            sem = float(sem_fields[0]["value"])
            if (
                sample_size > 1
                and math.isclose(sem, sd, rel_tol=1e-9, abs_tol=1e-12)
                and not math.isclose(sem, sd / math.sqrt(sample_size), rel_tol=1e-6, abs_tol=1e-9)
            ):
                flags.append(
                    cls._flag(
                        record,
                        "SEM_SD_CONFUSION_CANDIDATE",
                        "WARNING",
                        "sem equals sd despite sample_size > 1; uncertainty labels may be confused",
                        [sd_fields[0], sem_fields[0], sample_fields[0]],
                    )
                )
        return flags

    def run(self, *, strict: bool = False) -> QCSummary:
        """Run QC, quarantine critical records, and append review evidence."""
        records = self._load_fixture(self.fixture_path)
        flags = [flag for record in records for flag in self._check_record(record)]
        flags_by_record: dict[str, list[dict[str, Any]]] = {}
        for flag in flags:
            flags_by_record.setdefault(str(flag["record_id"]), []).append(flag)
        quarantine = [
            {
                "record_id": record["record_id"],
                "source_locator": record["source_locator"],
                "status": "QUARANTINED",
                "critical_rules": [
                    flag["rule"]
                    for flag in flags_by_record.get(str(record["record_id"]), [])
                    if flag["severity"] == "CRITICAL"
                ],
            }
            for record in records
            if any(flag["severity"] == "CRITICAL" for flag in flags_by_record.get(str(record["record_id"]), []))
        ]
        clean_controls = [record for record in records if record["control"]]
        injected_records = [record for record in records if record["injected_error"]]
        clean_ids = {record["record_id"] for record in clean_controls}
        injected_ids = {record["record_id"] for record in injected_records}
        control_flagged = {flag["record_id"] for flag in flags if flag["record_id"] in clean_ids}
        injected_flagged = {flag["record_id"] for flag in flags if flag["record_id"] in injected_ids}
        critical_flags = sum(flag["severity"] == "CRITICAL" for flag in flags)
        warning_flags = sum(flag["severity"] == "WARNING" for flag in flags)
        recall = len(injected_flagged) / len(injected_records) if injected_records else 1.0
        metrics = {
            "schema_version": 1,
            "fixture": True,
            "strict": strict,
            "records": len(records),
            "flags": len(flags),
            "critical_flags": critical_flags,
            "warning_flags": warning_flags,
            "quarantined_records": len(quarantine),
            "clean_control_records": len(clean_controls),
            "clean_control_false_positive_records": len(control_flagged),
            "clean_control_false_positive_rate": (
                len(control_flagged) / len(clean_controls) if clean_controls else 0.0
            ),
            "injected_error_records": len(injected_records),
            "injected_error_records_flagged": len(injected_flagged),
            "injected_error_recall": recall,
            "review_items": len(flags),
        }
        self.flags_path.parent.mkdir(parents=True, exist_ok=True)
        self.flags_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "flags": flags},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        self.quarantine_path.write_text(
            json.dumps(
                {"schema_version": 1, "fixture": True, "quarantine": quarantine},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        review_ledger = AppendOnlyJSONL(self.review_path)
        review_ledger.initialize()
        existing = {
            json.loads(line).get("review_id")
            for line in review_ledger.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for flag in flags:
            review = {
                "review_id": f"qc-review:{flag['flag_id']}",
                "flag_id": flag["flag_id"],
                "record_id": flag["record_id"],
                "rule": flag["rule"],
                "severity": flag["severity"],
                "source_locators": flag["source_locators"],
                "resolution": flag["resolution"],
            }
            if review["review_id"] not in existing:
                review_ledger.append(review)

        report_lines = [
            "# Physical and Statistical Plausibility QC",
            "",
            f"- mode: {'strict' if strict else 'standard'}",
            f"- records: {len(records)}",
            f"- flags: {len(flags)} ({critical_flags} critical, {warning_flags} warning)",
            f"- quarantined records: {len(quarantine)}",
            f"- clean-control false-positive rate: {metrics['clean_control_false_positive_rate']:.3f}",
            f"- injected-error recall: {recall:.3f}",
            "",
            "Rules cover bounded fractions and percentages, non-negative concentrations and "
            "dispersion, unique positive sample counts, and a candidate SEM/SD label-confusion "
            "check. Critical records are quarantined; warning records remain review-only.",
            "",
            "## Flags",
            "",
        ]
        report_lines.extend(
            f"- {flag['flag_id']} {flag['severity']} {flag['rule']}: {flag['message']}" for flag in flags
        )
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        return QCSummary(
            records=len(records),
            clean_controls=len(clean_controls),
            injected_error_records=len(injected_records),
            flags=len(flags),
            critical_flags=critical_flags,
            warning_flags=warning_flags,
            quarantined_records=len(quarantine),
            false_positive_controls=len(control_flagged),
            injected_error_records_flagged=len(injected_flagged),
            injected_error_recall=recall,
            review_items=len(flags),
            flags_path=self.flags_path,
            quarantine_path=self.quarantine_path,
            metrics_path=self.metrics_path,
            review_path=self.review_path,
            report_path=self.report_path,
        )
