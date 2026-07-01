# Benchmark Results Summary

## Phase 1 — Global Detector
- Scale invariance: diff = 0.000
- Speed: 0.39s/scan
- Heavy noise detection: PASS
- Hole detection: PASS

## Phase 2 — Patch Architecture
- 1% defect: 75% detection
- 5% defect: 100% detection
- 20% defect: 100% detection

## Phase 2.1 — Robustness Lock
- Without registration: 100% FP
- Confirmed: registration is required

## Phase 2.2 — Registration Module
- With PCA + ICP: 0% FP on pose variation
- Confidence threshold 0.5: balanced trade-off

## Phase 2.2A — Two-Mode Integration
- Mode A FP on clean: 0%
- Mode A detection (10%): 100%
- Auto escalation: 100%
- A vs B speedup: 3.6x
