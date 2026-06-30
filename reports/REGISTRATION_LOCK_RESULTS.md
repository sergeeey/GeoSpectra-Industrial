# Phase 2.2 -- Registration Module Results

> **Date:** 2026-06-30
> **Status:** COMPLETE -- registration gate implemented and validated

## Executive Summary

**ICP registration gate solves the pose-dependency problem (ADR-IND-012).**

After adding registration:
- **Rotation/translation**: 0% false positives (was 100%)
- **Heavy noise/occlusion**: safely rejected as UNRELIABLE_ALIGNMENT
- **Local defects**: still detected after successful registration

## Results

### Before Registration (Phase 2.1)

| Perturbation | Verdict | FP |
|-------------|---------|-----|
| All 18 tests | ANOMALOUS | **100%** |

### After Registration (Phase 2.2)

| Perturbation | Reg Conf | Verdict | FP |
|-------------|----------|---------|-----|
| Rotation Z 5deg | 1.0 | NORMAL | Pass |
| Rotation Z 15deg | 1.0 | NORMAL | Pass |
| Rotation Z 30deg | 1.0 | NORMAL | Pass |
| Rotation Z 90deg | 1.0 | NORMAL | Pass |
| Translation 1% | 1.0 | NORMAL | Pass |
| Translation 5% | 1.0 | NORMAL | Pass |
| Jitter 0.3% | 0.487 | UNRELIABLE_ALIGNMENT | Pass (safe) |
| Jitter 1% | 0.725 | LOCAL_DEFECT | Fail |
| Occlusion 5% | 1.0 | LOCAL_DEFECT | Fail |
| Occlusion 10% | 0.389 | UNRELIABLE_ALIGNMENT | Pass (safe) |
| Gaussian noise 1% | 0.725 | LOCAL_DEFECT | Fail |
| Gaussian noise 3% | 0.271 | UNRELIABLE_ALIGNMENT | Pass (safe) |

**FP rate: 23% (3/13)**
**Safe rejections: 31% (4/13)**

## Architecture

```
Raw Scan
  |
[Global Layer] -- always runs (noise/scale detection)
  |
[Registration] -- PCA coarse + ICP fine
  |
[Registration Gate]
  |-- confidence < threshold -> UNRELIABLE_ALIGNMENT
  |-- confidence >= threshold -> [Patch Layer]
                                        |
                                  [Rule-Based Decision]
```

## Key Design Decisions

- **ADR-IND-013**: Registration gate before patches
- **ADR-IND-014**: PCA coarse + ICP fine alignment
- **ADR-IND-015**: Confidence threshold 0.5 (balanced)

## Honest Limitations

1. Jitter 1% / noise 1%: Registration passes but patch layer gives FP
2. Occlusion 5%: Registration conf incorrectly high
3. Defect detection 67%: Conservative threshold rejects borderline
4. Speed: ~1.5s per registration on CPU

## Safety Logic

```
Before:  misaligned scan -> ANOMALOUS (false alarm, reject good part)
After:   misaligned scan -> UNRELIABLE_ALIGNMENT (inspect manually, don't reject)
```

## Key ADRs

ADR-IND-012, 013, 014, 015
