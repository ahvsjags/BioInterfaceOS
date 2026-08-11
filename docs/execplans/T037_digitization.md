# T037: Implement curve/bar/scatter digitization with uncertainty

## Purpose

Convert eligible, detector-approved 2D curve, bar, and scatter candidates into calibrated digitized points while preserving pixel-to-data calibration, axis scale type, error bars, uncertainty propagation, QC overlays, and source locators.

## Preconditions

T036 is DONE. Figure panels, axis candidates, scale classifications, legend mappings, curve candidates, and uncertainty cues are available. Only supported 2D panels are eligible.

## Non-goals

This task will not digitize unsupported 3D, heatmap, or image-assay panels, promote low-confidence candidates, or hide calibration residuals. Poor-resolution or incomplete-calibration panels remain qualitative/review-only.

## Interfaces and invariants

Every digitized point retains the source figure/panel/candidate locator and the calibration record used to map normalized coordinates to data coordinates. Linear and logarithmic axes use explicit inverse transforms. Error bars remain linked to their curve and carry propagated uncertainty. QC overlays reproduce the candidate geometry and calibration landmarks without replacing raw evidence.

## Implementation plan

1. Define digitized-point, calibration, uncertainty, and QC-overlay schemas.
2. Extend the synthetic fixture with known linear/log axes, bars/scatter points, and error cues with expected recovery tolerances.
3. Implement inverse axis calibration for linear and log scales with residual checks.
4. Recover curve/bar/scatter points, propagate uncertainty, and quarantine poor-quality candidates.
5. Write reviewable QC overlays and append-only digitization review records.
6. Extend biointerfaceos extract figures --fixture, add focused tests, and run full acceptance gates.

## Progress

- [x] Define digitization, calibration, uncertainty, and QC-overlay schemas.
- [x] Implement fixture-backed curve/bar/scatter recovery and uncertainty propagation.
- [x] Quarantine unsupported or poor-quality candidates with review evidence.
- [x] Run acceptance gates and record completion evidence.

## Validation

- UV_OFFLINE=1 uv lock --check
- UV_OFFLINE=1 uv sync --frozen --python 3.11
- UV_OFFLINE=1 make check
- biointerfaceos extract figures --fixture
- biointerfaceos assets verify
- biointerfaceos lockbox self-test
- biointerfaceos state validate
- git diff --check
- synthetic recovery error, linear/log calibration, error-bar propagation, QC overlay, and exclusion assertions

## Failure recovery

Preserve raw candidate geometry and calibration inputs. Quarantine candidates with failed residual or resolution checks; never silently replace detector evidence with digitized output.

## Outputs

digitized points, calibration and uncertainty records, QC overlays, review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.

## Completion note

T037 completed with implementation commit 8e4388b. Linear and logarithmic calibration, curve/bar/scatter recovery, uncertainty propagation, QC overlays, and low-quality quarantine all pass the fixture acceptance gates.
