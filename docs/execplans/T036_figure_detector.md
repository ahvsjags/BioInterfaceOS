# T036: Implement scientific figure panel and axis detector

## Purpose

Detect scientifically meaningful 2D figure panels from controlled figure fixtures, preserving panel labels, axes, scale type, legends, curve candidates, uncertainty cues, and confidence evidence for downstream digitization.

## Preconditions

T032 and T034 are DONE. Figure references/captions and bounded PDF/image layout records are available. T037 will consume this detector output.

## Non-goals

This task will not digitize numeric points, execute OCR on arbitrary images, or infer quantitative values from unsupported 3D, heatmap, or image-assay panels. Unsupported panel types remain explicitly marked for review.

## Interfaces and invariants

Every detected panel and feature retains a source asset ID, stable panel/feature locator, source caption or fixture region, normalized coordinates, and confidence. Axis candidates retain labels, orientation, tick evidence, and linear/log scale classification. Legend entries and curve candidates remain separate evidence objects. Uncertain detections are queued rather than silently promoted.

## Implementation plan

1. Define panel, axis, legend, curve-candidate, uncertainty, and review schemas.
2. Build deterministic synthetic fixtures covering labelled multi-panel 2D plots, linear/log axes, legends, and error-bar cues.
3. Implement panel segmentation and panel-label detection with stable normalized locators.
4. Implement axis/orientation/tick detection and scale-type classification.
5. Implement legend and curve-candidate detection plus confidence calibration and unsupported-panel flags.
6. Add biointerfaceos extract figures --fixture, focused tests, and full acceptance gates.

## Progress

- [x] Define figure detection schemas and stable locators.
- [x] Implement fixture-backed panel, axis, legend, and curve detection.
- [x] Mark unsupported panel types and queue low-confidence detections.
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
- panel-label, axis, scale, legend, curve-candidate, confidence, and unsupported-panel assertions

## Failure recovery

Preserve original figure evidence and hashes. Quarantine unsupported or low-confidence panels for review; never emit digitized values from a detector-only task.

## Outputs

Figure detection schema, panel/axis/legend/curve candidates, review queue, fixtures/tests, CLI integration, this ExecPlan, state advancement, and task-ledger evidence.

## Completion note

T036 completed with implementation commit aee17cf. Synthetic 2D panels retain labels, axes, scale classifications, legends, curve candidates, uncertainty cues, confidence calibration, and stable locators. Unsupported heatmap content remains in the review queue; no numeric digitization is emitted.
