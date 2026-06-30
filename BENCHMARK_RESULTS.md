# Benchmark Results -- GeoSpectra-Industrial MVP

> **Date:** 2026-06-30
> **Status:** Phase 1.5 (Realistic Synthetic Meshes)

## Methodology

| Parameter | Value |
|-----------|-------|
| Point cloud size | 1,500 points |
| kNN neighbors (k) | 12 |
| Eigenvalues extracted | 10 |
| Defect types tested | 10 |
| Mesh types | 3 (bracket, gear, housing) |

## Results Summary

### Batch Calibration Mode (3 normals)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Exact accuracy | 30% | >= 60% | Warning |
| **Acceptable rate** | **90%** | **>= 80%** | Pass |
| False positive rate (none->ANOMALOUS) | **100%** | <= 10% | Fail |

### Single Reference Mode

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Exact accuracy | 27% | >= 60% | Warning |
| **Acceptable rate** | **60%** | **>= 70%** | Warning |
| False positive rate | **0%** | <= 10% | Pass |

## Per-Defect Breakdown (Single Reference, 3 meshes)

| Defect | bracket | gear | housing | Avg Detection |
|--------|---------|------|---------|---------------|
| none | Pass NORMAL | Pass NORMAL | Pass NORMAL | **0% FP** |
| noise_low | Pass DEFORMED | Pass DEFORMED | Fail NORMAL | 67% |
| noise_high | Warning DEFORMED | Pass ANOMALOUS | Warning DEFORMED | 100% |
| outliers | Warning DEFORMED | Pass ANOMALOUS | Warning DEFORMED | 100% |
| **bulge** | Fail NORMAL | Fail NORMAL | Fail NORMAL | **0%** |
| **dent** | Fail NORMAL | Warning ANOMALOUS | Fail NORMAL | **33%** |
| **twist** | Fail NORMAL | Pass DEFORMED | Fail NORMAL | **33%** |
| scale_drift | Fail NORMAL | Warning DEFORMED | Fail NORMAL | **33%** |
| **erosion** | Fail NORMAL | Warning ANOMALOUS | Fail NORMAL | **33%** |
| hole | Warning DEFORMED | Warning DEFORMED | Warning DEFORMED | 100% |

## Key Findings

### What Works
1. **Scale invariance** -- perfect (diff = 0.000 across 2x scale)
2. **Speed** -- 0.39s per fingerprint on CPU
3. **Noise/outlier detection** -- 100% detection rate
4. **Hole/void detection** -- 100% detection rate
5. **No false positives** in single-reference mode

### What Needs Work
1. **Local defects** (bulge, dent, twist, erosion) -- global features miss them
2. **Threshold sensitivity** -- batch mode overfits, single-reference underdetects
3. **Exact accuracy** -- 27-30%, need 60%+ for publication

### Known Limitations
1. **No real data validation yet** -- all results synthetic
2. **Single scale of defects** -- no severity gradation
3. **No localization** -- only global verdict, no defect location

## ADR-IND-007: Local Defects Require Patch-Based Approach

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | IDENTIFIED -- needs implementation |

**Finding:** Global spectral + geometric features miss local defects (bulge, dent, erosion) because they affect <5% of points. PCA ratios and eigenvalue density of the full point cloud are insensitive to such localized changes.

**Solution Path:** Sliding window patches + per-patch fingerprint + max aggregation. This became ADR-IND-008 and was implemented in core/patch_detector.py.
