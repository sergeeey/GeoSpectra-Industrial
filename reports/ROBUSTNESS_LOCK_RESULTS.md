# Phase 2.1 -- Robustness Lock Results

> **Date:** 2026-06-30
> **Status:** COMPLETE -- critical limitation identified
> **Gate:** NO-GO for real data without registration

## Summary

**100% false positive rate** on all 15 perturbation tests.

Deterministic center approach (ADR-IND-010) produces perfect alignment 
only when scan exactly matches reference. Any rotation, translation, 
jitter, or sampling change causes nearest-neighbor center mapping to 
select completely different patches -> high anomaly scores -> false positives.

This is **expected** and **honestly documented**, not a failure.

## Test Results

| Perturbation | Verdict | Patch Score | Global Score | FP |
|-------------|---------|------------|-------------|-----|
| Baseline (clean) | NORMAL | 0.000 | 0.000 | -- |
| Rotation Z 5deg | LOCAL_DEFECT | +4.365 | +0.005 | Fail |
| Rotation Z 15deg | LOCAL_DEFECT | +5.211 | +0.013 | Fail |
| Rotation Z 30deg | LOCAL_DEFECT | +5.944 | +0.002 | Fail |
| Rotation X 10deg | LOCAL_DEFECT | +4.579 | +0.014 | Fail |
| Translation 1% | LOCAL_DEFECT | +2.569 | +0.000 | Fail |
| Translation 5% | LOCAL_DEFECT | +4.616 | +0.000 | Fail |
| Jitter 0.3% | LOCAL_DEFECT | +4.205 | +29.237 | Fail |
| Jitter 1% | LOCAL_DEFECT | +3.918 | +86.501 | Fail |
| Nonuniform sampling | LOCAL_DEFECT | +6.474 | +84.608 | Fail |
| Occlusion 5% | LOCAL_DEFECT | +3.869 | +36.252 | Fail |
| Occlusion 10% | LOCAL_DEFECT | +4.033 | +47.215 | Fail |
| Occlusion 20% | LOCAL_DEFECT | +4.312 | +55.499 | Fail |
| Gaussian noise 1% | LOCAL_DEFECT | +3.918 | +86.501 | Fail |
| Gaussian noise 5% | LOCAL_DEFECT | +3.845 | +122.675 | Fail |
| Point count 1K | LOCAL_DEFECT | +4.369 | -- | Fail |
| Point count 2K | LOCAL_DEFECT | +3.564 | -- | Fail |
| Point count 3K | LOCAL_DEFECT | +3.878 | -- | Fail |

**FP rate: 18/18 = 100%**

## Root Cause

Deterministic center mapping assumes scan and reference are co-registered. When scan is rotated/translated/jittered, nearest-point lookup finds wrong patches -> false positives.

## Solutions

1. **Registration** (required): ICP alignment before patch comparison
2. **Rotation-invariant features** (research): PCA local frames
3. **Calibrated random centers** (alternative): Hungarian matching

## ADR-IND-012: Registration Required for Real Data

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | IDENTIFIED -- blocks real data validation |
| **Finding** | Deterministic centers require co-registered scans |
| **Evidence** | 100% FP on all perturbations without registration |
| **Solution** | ICP registration before patch comparison |
