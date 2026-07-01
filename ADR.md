# Architecture Decision Records — GeoSpectra-Industrial

---

## ADR-IND-001: Two-Feature Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Use both spectral (kNN Laplacian eigenvalues) AND geometric features (PCA ratios, bbox, asymmetry). |
| **Rationale** | Phase 1 Recon showed spectral features alone miss local defects (bulge, dent, twist) that preserve global spectrum. Geometric features catch shape changes spectral features miss. |
| **Evidence** | `recon_phase1.py` — sphere bulge: spectral dist=0.052 (undetected), geometric PCA_ratio changes significantly. |

---

## ADR-IND-002: Single-Reference Distance Mode

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Primary mode: direct distance from single reference fingerprint. Batch calibration as secondary mode. |
| **Rationale** | Batch z-score calibration overfits to "ideal" scans — even clean variants get high z-scores due to sampling noise in PCA. Single-reference with tuned thresholds is more predictable. |
| **Evidence** | `recon_v2_two_feature.py` — batch mode classified clean scan as ANOMALOUS (z=4.51). Single-reference mode correctly classified all clean scans as NORMAL. |

---

## ADR-IND-003: Std Floor for Batch Calibration

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Minimum std = 10% of |mean| in batch calibration. |
| **Rationale** | Without floor, 5 similar scans give std≈0, making any variation extreme. 10% floor allows natural manufacturing variation without false positives. |

---

## ADR-IND-004: Scale-Invariant by Median Normalization

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED (inherited from scientific repo) |
| **Decision** | Normalize eigenvalues by median before density computation. |
| **Evidence** | Unit test: scale_invariance passes with rtol=0.1 across 2x scale change. |

---

## ADR-IND-005: Unified Loader via trimesh

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Use trimesh for all 3D format loading (STL, PLY, OBJ, XYZ). |
| **Rationale** | One dependency handles all formats. Consistent (N,3) output. Sampling built-in. |

---

## ADR-IND-006: 3-Class Verdict System

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | NORMAL (pass), DEFORMED (inspect), ANOMALOUS (rescan). |
| **Rationale** | 2 classes insufficient — need "yellow" zone between pass and fail. DEFORMED triggers human inspection without stopping line. |

---

## ADR-IND-007: Local Defects Need Patches

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Global fingerprint misses defects <5% of points. Local patch architecture required. |
| **Evidence** | `patch_defect_sweep.py` — global misses 1% defect entirely; patch layer catches it. |

---

## ADR-IND-008: Patch Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | FPS sampling + kNN patches + top-k mean aggregation. |
| **Rationale** | FPS gives diverse, well-distributed centers. kNN ensures local neighborhoods. Top-k mean focuses on worst regions. |
| **Evidence** | 75% at 1%, 100% at 5% defect. |

---

## ADR-IND-009: Hierarchical Detector

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Global + patch + rule-based decision. |
| **Rationale** | Global catches overall issues; patch catches local defects. Rule-based override prevents patch high/global low confusion. |

---

## ADR-IND-010: Deterministic Centers

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | FPS seed=42 for reproducible center positions. |
| **Rationale** | Random centers caused irreproducible results between runs. Deterministic enables debugging and regression testing. |

---

## ADR-IND-011: Rule-Based Override

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | If patch_score >= threshold → LOCAL_DEFECT regardless of global. |
| **Rationale** | Weighted sum dilutes strong local signal with weak global signal. Rule-based preserves local defect detection. |

---

## ADR-IND-012: Registration Required

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | VALIDATED |
| **Decision** | Patch detector without registration = 100% FP on rotated scans. |
| **Evidence** | `robustness_lock.py` — 100% FP on 15° rotation without registration. |

---

## ADR-IND-013: Registration Gate

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | Block patch layer if registration confidence < threshold. |
| **Rationale** | Prevents false defect alarms from misalignment artifacts. |

---

## ADR-IND-014: PCA Coarse + ICP Fine

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | VALIDATED |
| **Decision** | Two-stage alignment: PCA principal axes for coarse, ICP for fine. |
| **Rationale** | Without PCA coarse, ICP fails on large rotations (local minimum). PCA handles up to 180°. |

---

## ADR-IND-015: Confidence Threshold 0.5

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED (MVP default) |
| **Decision** | registration_confidence_threshold = 0.5 |
| **Trade-off** | 0.3 → 38% FP, 83% detection. 0.5 → 23% FP, 67% detection. 0.7 → 15% FP, 33% detection. |

---

## ADR-IND-016: Mechanism Design — Payoff Audit Before Boundary Tests

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | VALIDATED |
| **Decision** | Conduct payoff audit BEFORE running boundary/edge-case experiments. Explicitly identify threshold_gaming risk (8/10 for sub-1% detection). Test ALL thresholds, not just best one. Report ALL results, not just positive ones. |
| **Rationale** | Without audit guard, agent could lower patch_threshold to show acceptable detection at 0.5%, gaming the metric. With audit: all thresholds shown, honest "below validated range" reported. |
| **Evidence** | `mechanism_design_test.py` — 0.5%: 0% detection at ALL thresholds (1.0-3.0). System honestly reported [BELOW-VALIDATED-RANGE] with confidence cap 0.3 instead of gaming threshold. Minority Veto: PASS (no suspicious results). |

---

## ADR-IND-017: Evidence Marker [BELOW-VALIDATED-RANGE]

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Status** | ACCEPTED |
| **Decision** | New evidence marker for results below validated operating range. Confidence cap ≤ 0.3. Cannot be promoted to L1 without extended validation at this boundary. |
| **Rationale** | Distinguishes "honest limitation" from "failure". System operates reliably at ≥1% defects. Below 1%: detection drops to 0%. This is expected behavior, not a bug — but must be honestly documented. |

---

## ADR-IND-018: Registration-Free Patch Bank (Two-Mode Architecture)

| Field | Value |
|-------|-------|
| **Date** | 2026-07-01 |
| **Status** | VALIDATED |
| **Decision** | Implement TWO independent modes instead of forcing registration as gate: **Mode A** (Registration-Free Patch Bank) for coarse screening under unknown pose, **Mode B** (Location-Aware Patch Detector) for precise inspection after ICP alignment. Modes are not sequential — they are alternative strategies selected by use case. |
| **Rationale** | ADR-IND-012 found that patch detector without registration produces 100% FP. Two approaches to solve this: (1) add registration gate (ADR-IND-013, done) or (2) make patches themselves rotation/translation invariant. This ADR implements approach (2), giving operator choice between speed+pose-invariance (Mode A) vs precision+localization (Mode B). |
| **Mode A — Registration-Free Patch Bank** | **Evidence** |
| **Principle** | Each patch fingerprinted by relative geometry (PCA ratios, histogram distances), not absolute coordinates. Scan patches compared to reference patch bank via nearest-neighbor in descriptor space. |
| **Rotation** | 0% FP at 15°, 45°, 90° ✅ |
| **Translation** | 0% FP at small, medium, large ✅ |
| **Scale ±5%** | 0% FP ✅ |
| **5% defects** | 100% detection ✅ |
| **Runtime** | ~0.27s/scan (4x faster than Mode B) ✅ |
| **Limitation** | No defect location; jitter/occlusion 100% FP (non-rigid sensitivity) |
| **Mode B — Location-Aware Patch Detector** | **Evidence** |
| **Principle** | Deterministic centers aligned to reference frame via ICP. Per-patch anomaly scores aggregated to heatmap. |
| **Localization** | Exact patch position of defect ✅ |
| **Jitter (0.3%)** | 0% FP (aligned patches survive jitter) ✅ |
| **5% defects** | 100% detection ✅ |
| **Runtime** | ~2.5s/scan (with ICP) |
| **Limitation** | Requires successful registration; 23% FP if registration fails |
| **When to use which?** | |
| Use **Mode A** when: scan pose unknown, speed critical, coarse screening acceptable, no time for ICP | |
| Use **Mode B** when: scan already roughly aligned, precise localization needed, metrology-grade inspection, jitter tolerance required | |
| Use **Both** when: Mode A flags anomaly → run Mode B on cropped/aligned region for precise localization | |

---

## ADR-IND-019: Auto Escalation Policy (Mode A → Mode B)

| Field | Value |
|-------|-------|
| **Date** | 2026-07-01 |
| **Status** | VALIDATED |
| **Decision** | In "auto" mode: run Mode A first, escalate to Mode B only if Mode A reports anomaly with confidence >= auto_escalate_confidence (default 0.8). If Mode B registration fails, fall back to Mode A result with reduced confidence. |
| **Rationale** | Sequential A→B wastes time on normal scans (Mode B ICP is expensive). Auto mode gives fast path for normal scans (Mode A only: ~0.3s) and precise localization for anomalies (A+B: ~1.4s avg). Fallback ensures no data loss when registration fails. |
| **Evidence** | `benchmarks/two_mode_integration.py` — 4/4 checks PASS: 0% FP on clean, 100% detection at 10% defects, escalation on all anomalies, 3.6x speedup. Auto avg runtime 688ms vs Mode B alone 1108ms (38% faster). |
| **Escalation trigger** | Mode A verdict in (DEFORMED, ANOMALOUS) AND confidence >= auto_escalate_confidence |
| **Fallback condition** | Mode B returns UNRELIABLE_ALIGNMENT or error → use Mode A result with confidence *= 0.8 |
| **Confidence reduction** | Fallback confidence capped at 0.8 to signal uncertainty from failed registration |

---

## ADR-IND-020: Deterministic FPS with Calibration

| Field | Value |
|-------|-------|
| **Date** | 2026-07-01 |
| **Status** | VALIDATED |
| **Decision** | Use deterministic FPS (fixed seed=42) + calibration on 30 clean transformed variants with fixed critical rotations (90°, 180° on all axes) + random variants. Thresholds set at 95th/99th percentile of clean score distribution. |
| **Rationale** | Random FPS caused irreproducible patch sets between reference and scan — defect scores sometimes LOWER than clean due to sampling luck. Deterministic FPS removes this variance. Calibration with diverse rotations ensures thresholds cover the pose space. Without calibration, default thresholds (1.5, 4.0) produced 88% FP on clean scans. |
| **Evidence** | Before: 88% FP on clean rotated scans. After deterministic FPS + calibration: 0% FP, 100% detection at 10% defects. Calibration stats: mean=1.56, std=0.82, p95=2.44, p99=2.49 on bracket shape. |
| **Limitation** | Exact 90° rotations on near-symmetric objects may still trigger DEFORMED at p95 threshold — use non-axis-aligned angles in production deployment. |

---

*20 ADRs recorded. 11 ACCEPTED, 9 VALIDATED, 0 BLOCKING.*
*Two-mode architecture active since ADR-IND-018.*
*Auto escalation policy active since ADR-IND-019.*
*Last updated: 2026-07-01*
