# R2 empirical data dictionary

| Field | Meaning | Source of truth |
| --- | --- | --- |
| `observation_id` | Stable identifier for one released measurement | empirical registry |
| `source_id`, `doi`, `landing_url`, `license_id` | Dataset identity and reuse status | source-level record |
| `study_id`, `laboratory`, `affiliation` | Study and laboratory lineage | source-level record |
| `material`, `biological_system`, `protocol_id` | Context inherited by each row | source-level record |
| `independent_unit_id` | Released GUV label | worksheet column A |
| `raw_locator` | Exact original cell used by the audit | worksheet + column + row |
| `raw_value`, `unit` | Value read from the original workbook cell | worksheet column B |

The current endpoint is `GUV_SHRINKING_RATE`, reported exactly as `um2/s` in `Shrinking_rates!B2:B15` of the University of Leeds workbook. Values remain developmental observations and do not constitute a statistical conclusion.
