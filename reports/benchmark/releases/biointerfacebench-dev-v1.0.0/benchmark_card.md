# BioInterfaceBench development release 1.0.0

Release ID: `biointerfacebench-dev-v1.0.0`  
Status: `FROZEN_DEV`  
Target values exposed: `false`  
Public/hidden separation: `true`

## Frozen benchmark

- Instances: 16 across 8 families
- Development split: 8 train / 8 validation
- Grader cases: 3
- Statistical baselines: 5
- Representation baselines: 4
- Hidden layer: metadata-only registry; target values remain inaccessible

## Robustness gate

T102 negative controls passed strict mode with zero critical leakage.
All recorded inputs are checksum-pinned; a corrected benchmark requires a new semantic version.
