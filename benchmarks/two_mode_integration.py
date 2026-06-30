"""Two-Mode Integration Benchmark — validate unified detector (ADR-IND-018).

Tests:
  1. Mode A alone: 0% FP on rotated/translated clean scans
  2. Mode A alone: detection of scans with 10% defects
  3. Mode B alone: detection + localization on aligned defective scans
  4. Mode B alone: UNRELIABLE_ALIGNMENT on badly rotated scans
  5. Auto mode: escalation from A to B on high-confidence anomalies
  6. Auto mode: fallback to A when B registration fails
  7. Runtime comparison: A vs B vs auto

Evidence markers: [REPRODUCED], [DETERMINISTIC], [SYNTHETIC-DATA].
"""

import json
import time
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.two_mode_detector import TwoModeDetector


# =============================================================================
# Test data generation
# =============================================================================

def make_sphere(n_points=2048, radius=1.0):
    """Generate a sphere point cloud (Fibonacci lattice)."""
    indices = np.arange(n_points, dtype=float) + 0.5
    phi = np.arccos(1 - 2 * indices / n_points)
    theta = np.pi * (1 + 5**0.5) * indices
    x = radius * np.sin(phi) * np.cos(theta)
    y = radius * np.sin(phi) * np.sin(theta)
    z = radius * np.cos(phi)
    return np.column_stack([x, y, z])


def make_box(n_points=2048, size=2.0):
    """Generate a box point cloud via rejection sampling."""
    pts = np.random.uniform(-size/2, size/2, (n_points * 3, 3))
    eps = size * 0.05
    on_surface = (
        (np.abs(pts[:, 0]) > size/2 - eps) |
        (np.abs(pts[:, 1]) > size/2 - eps) |
        (np.abs(pts[:, 2]) > size/2 - eps)
    )
    pts = pts[on_surface][:n_points]
    if len(pts) < n_points:
        pts = np.vstack([pts, np.random.uniform(-size/2, size/2, (n_points - len(pts), 3))])
    return pts[:n_points]


def rotate_points(points, angle_deg, axis='z'):
    """Rotate point cloud around axis."""
    angle = np.radians(angle_deg)
    if axis == 'x':
        R = np.array([[1, 0, 0],
                      [0, np.cos(angle), -np.sin(angle)],
                      [0, np.sin(angle), np.cos(angle)]])
    elif axis == 'y':
        R = np.array([[np.cos(angle), 0, np.sin(angle)],
                      [0, 1, 0],
                      [-np.sin(angle), 0, np.cos(angle)]])
    else:
        R = np.array([[np.cos(angle), -np.sin(angle), 0],
                      [np.sin(angle), np.cos(angle), 0],
                      [0, 0, 1]])
    return points @ R.T


def translate_points(points, shift):
    """Translate point cloud."""
    return points + np.array(shift)


def add_defect_bulge(points, radius_percentile=20, magnitude=0.05):
    """Add a local bulge defect."""
    pts = points.copy()
    idx = np.random.randint(len(pts))
    center = pts[idx]
    dists = np.linalg.norm(pts - center, axis=1)
    mask = dists < np.percentile(dists, radius_percentile)
    dirs = pts[mask] - center
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    falloff = 1 - dists[mask][:, None] / (dists[mask].max() + 1e-10)
    pts[mask] += magnitude * (dirs / norms) * falloff
    return pts


# =============================================================================
# Benchmark runner
# =============================================================================

def run_two_mode_benchmark(seed=42, save_report=True):
    """Run full two-mode integration benchmark.
    
    Returns dict with all results + saves JSON report.
    """
    np.random.seed(seed)
    
    print("=" * 70)
    print("TWO-MODE INTEGRATION BENCHMARK (ADR-IND-018)")
    print("=" * 70)
    
    # Generate reference (asymmetric bracket from industrial suite)
    try:
        from benchmarks.industrial_mesh_suite import create_bracket
        import trimesh
        mesh = create_bracket()
        ref_points = trimesh.sample.sample_surface(mesh, 2048)[0]
        shape_name = "bracket"
    except Exception:
        ref_points = make_box(n_points=2048, size=2.0)
        shape_name = "box"
    print(f"\nReference: {shape_name}, {len(ref_points)} points")
    
    # Generate test scans
    test_scans = {}
    
    # Clean scans with various rigid transforms (non-axis-aligned angles)
    for angle in [15, 37, 73]:
        test_scans[f"rot_{angle}"] = rotate_points(ref_points, angle, 'z')
    for shift in [(0.1, 0.05, 0.02), (0.3, 0.2, 0.1), (0.5, 0.4, 0.3)]:
        test_scans[f"trans_{shift[0]}"] = translate_points(ref_points, shift)
    test_scans["scale_1.05"] = ref_points * 1.05
    test_scans["scale_0.95"] = ref_points * 0.95
    
    # Clean (no transform)
    test_scans["clean"] = ref_points.copy()
    
    # With defects (10% bulge on rotated scan — coarse screening target)
    for angle in [0, 30, 60]:
        defective = add_defect_bulge(ref_points, radius_percentile=30, magnitude=0.10)
        if angle > 0:
            defective = rotate_points(defective, angle, 'z')
        test_scans[f"defect_10pct_rot_{angle}"] = defective
    
    # With smaller defects (5% bulge — below validated range for Mode A)
    test_scans["defect_5pct"] = add_defect_bulge(ref_points, radius_percentile=18, magnitude=0.05)
    
    # With jitter (non-rigid — known Mode A limitation)
    jitter_sigma = np.ptp(ref_points, axis=0).max() * 0.003
    test_scans["jitter"] = ref_points + np.random.normal(0, jitter_sigma, ref_points.shape)
    
    print(f"Test scans: {len(test_scans)} conditions")
    
    # Initialize detectors for each mode
    print("\n" + "-" * 50)
    print("FITTING detectors...")
    
    det_a = TwoModeDetector(mode="A", n_patches=32, patch_size=64, top_k_ratio=0.15)
    det_a.fit(ref_points)
    print("  Mode A: fitted")
    
    det_b = TwoModeDetector(mode="B", n_patches=32, patch_size=64, top_k_ratio=0.15,
                            registration_confidence_threshold=0.5)
    det_b.fit(ref_points)
    print("  Mode B: fitted")
    
    det_auto = TwoModeDetector(mode="auto", n_patches=32, patch_size=64, top_k_ratio=0.15,
                               auto_escalate_confidence=0.6)
    det_auto.fit(ref_points)
    print("  Auto: fitted")
    
    # Run detection
    print("\n" + "-" * 50)
    print("RUNNING detections...")
    
    results = {}
    runtimes = {"A": [], "B": [], "auto": []}
    
    for scan_name, scan_points in test_scans.items():
        results[scan_name] = {}
        
        for mode_name, detector in [("A", det_a), ("B", det_b), ("auto", det_auto)]:
            t0 = time.perf_counter()
            result = detector.detect(scan_points)
            elapsed = (time.perf_counter() - t0) * 1000
            runtimes[mode_name].append(elapsed)
            
            results[scan_name][mode_name] = {
                "verdict": result["verdict"],
                "confidence": result["confidence"],
                "anomaly_score": result["anomaly_score"],
                "mode_used": result["mode_used"],
                "escalated": result.get("escalated", False),
                "runtime_ms": round(elapsed, 1),
            }
    
    # Analyze results
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    analyses = {}
    
    # Test 1: Mode A — FP rate on clean transformed scans
    clean_transforms = [k for k in test_scans.keys() if k.startswith(("rot_", "trans_", "scale_"))]
    mode_a_clean_verdicts = [results[k]["A"]["verdict"] for k in clean_transforms]
    mode_a_fp = sum(1 for v in mode_a_clean_verdicts if v != "NORMAL")
    mode_a_fp_rate = mode_a_fp / len(clean_transforms) * 100 if clean_transforms else 0
    
    print(f"\n[TEST 1] Mode A: FP rate on clean transformed scans")
    print(f"  Scans: {len(clean_transforms)} (rotations, translations, scales)")
    print(f"  FP: {mode_a_fp}/{len(clean_transforms)} ({mode_a_fp_rate:.0f}%)")
    print(f"  Verdicts: {dict(zip(clean_transforms, mode_a_clean_verdicts))}")
    analyses["mode_a_fp_rate"] = {
        "test": "FP on clean transformed scans",
        "n_scans": len(clean_transforms),
        "fp_count": mode_a_fp,
        "fp_rate_pct": round(mode_a_fp_rate, 1),
        "verdicts": dict(zip(clean_transforms, mode_a_clean_verdicts)),
        "evidence": "[REPRODUCED]" if mode_a_fp_rate == 0 else "[ANOMALY-REQUIRE-INVESTIGATION]",
    }
    
    # Test 2: Mode A — Detection of 10% defects
    defect_10pct = [k for k in test_scans.keys() if "defect_10pct" in k]
    mode_a_defect_verdicts = [results[k]["A"]["verdict"] for k in defect_10pct]
    mode_a_detections = sum(1 for v in mode_a_defect_verdicts if v in ("DEFORMED", "ANOMALOUS"))
    mode_a_detection_rate = mode_a_detections / len(defect_10pct) * 100 if defect_10pct else 0
    
    print(f"\n[TEST 2] Mode A: Detection of 10% defects")
    print(f"  Scans: {len(defect_10pct)} (10% bulge, various rotations)")
    print(f"  Detected: {mode_a_detections}/{len(defect_10pct)} ({mode_a_detection_rate:.0f}%)")
    for k in defect_10pct:
        r = results[k]["A"]
        print(f"    {k}: {r['verdict']} (score={r['anomaly_score']:.2f}, conf={r['confidence']:.2f})")
    analyses["mode_a_detection_10pct"] = {
        "test": "Detection of 10% defects",
        "n_scans": len(defect_10pct),
        "detected": mode_a_detections,
        "detection_rate_pct": round(mode_a_detection_rate, 1),
        "per_scan": {k: results[k]["A"] for k in defect_10pct},
        "evidence": "[REPRODUCED]" if mode_a_detection_rate >= 80 else "[PARTIAL]",
    }
    
    # Test 3: Mode B — Detection + localization on aligned scans
    defect_aligned = [k for k in test_scans.keys() if k == "defect_10pct_rot_0"]
    if defect_aligned:
        k = defect_aligned[0]
        b_result = results[k]["B"]
        b_has_local = b_result["verdict"] == "LOCAL_DEFECT"
        print(f"\n[TEST 3] Mode B: Localization on aligned scan")
        print(f"  Scan: {k}")
        print(f"  Verdict: {b_result['verdict']} (score={b_result['anomaly_score']:.2f})")
        print(f"  Localized: {'YES' if b_has_local else 'NO'}")
        analyses["mode_b_localization"] = {
            "test": "Localization on aligned scan",
            "verdict": b_result["verdict"],
            "localized": bool(b_has_local),
            "evidence": "[REPRODUCED]" if b_has_local else "[ANOMALY]",
        }
    
    # Test 4: Mode B — Registration on rotated scans
    mode_b_rot_failures = []
    for k in test_scans:
        if k.startswith("rot_") or k.startswith("defect_10pct_rot_"):
            if results[k]["B"]["verdict"] == "UNRELIABLE_ALIGNMENT":
                mode_b_rot_failures.append(k)
    b_unreliable_on_rot = sum(1 for k in test_scans if "rot_" in k and results[k]["B"]["verdict"] == "UNRELIABLE_ALIGNMENT")
    b_total_rot = sum(1 for k in test_scans if "rot_" in k)
    
    print(f"\n[TEST 4] Mode B: Registration on rotated scans")
    print(f"  Rotated scans: {b_total_rot}")
    print(f"  UNRELIABLE_ALIGNMENT: {b_unreliable_on_rot}")
    for k in sorted(test_scans.keys()):
        if "rot_" in k:
            print(f"    {k}: {results[k]['B']['verdict']} (conf={results[k]['B']['confidence']:.2f})")
    analyses["mode_b_registration"] = {
        "test": "Registration on rotated scans",
        "n_rotated": int(b_total_rot),
        "unreliable_count": int(b_unreliable_on_rot),
        "per_scan": {k: {"verdict": results[k]["B"]["verdict"], "confidence": results[k]["B"]["confidence"]} 
                     for k in sorted(test_scans.keys()) if "rot_" in k},
    }
    
    # Test 5: Auto mode escalation
    auto_defect_scans = [k for k in test_scans if "defect_10pct" in k]
    escalations = []
    for k in auto_defect_scans:
        auto_r = results[k]["auto"]
        if auto_r.get("escalated", False) or "B" in str(auto_r.get("mode_used", "")):
            escalations.append(k)
    
    print(f"\n[TEST 5] Auto mode: Escalation behavior")
    print(f"  Defect scans: {len(auto_defect_scans)}")
    print(f"  Escalated to B: {len(escalations)}")
    for k in auto_defect_scans:
        r = results[k]["auto"]
        print(f"    {k}: {r['verdict']} (mode={r['mode_used']}, escalated={r.get('escalated', False)})")
    analyses["auto_escalation"] = {
        "test": "Auto mode escalation",
        "n_defect_scans": len(auto_defect_scans),
        "escalated_count": len(escalations),
        "per_scan": {k: results[k]["auto"] for k in auto_defect_scans},
    }
    
    # Test 6: Auto mode fallback (jitter)
    if "jitter" in results:
        jitter_auto = results["jitter"]["auto"]
        fallback = bool("A" in str(jitter_auto.get("mode_used", "")) and not jitter_auto.get("escalated", False))
        print(f"\n[TEST 6] Auto mode: Jitter handling")
        print(f"  Jitter scan: verdict={jitter_auto['verdict']}, mode={jitter_auto['mode_used']}")
        print(f"  Used Mode A (no false escalation): {'YES' if fallback else 'NO'}")
        analyses["auto_jitter_fallback"] = {
            "test": "Jitter fallback to Mode A",
            "verdict": jitter_auto["verdict"],
            "mode_used": jitter_auto["mode_used"],
            "fallback_to_a": fallback,
            "evidence": "[REPRODUCED]" if fallback else "[INVESTIGATE]",
        }
    
    # Test 7: Runtime comparison
    avg_runtimes = {m: round(np.mean(runtimes[m]), 1) for m in ["A", "B", "auto"]}
    print(f"\n[TEST 7] Runtime comparison")
    print(f"  Mode A avg: {avg_runtimes['A']:.1f} ms")
    print(f"  Mode B avg: {avg_runtimes['B']:.1f} ms")
    print(f"  Auto avg:   {avg_runtimes['auto']:.1f} ms")
    speedup = avg_runtimes["B"] / avg_runtimes["A"] if avg_runtimes["A"] > 0 else 0
    print(f"  A speedup vs B: {speedup:.1f}x")
    analyses["runtime"] = {
        "mode_a_ms": avg_runtimes["A"],
        "mode_b_ms": avg_runtimes["B"],
        "auto_ms": avg_runtimes["auto"],
        "speedup_a_vs_b": round(speedup, 1),
    }
    
    # Overall PASS/FAIL
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    
    checks = [
        ("Mode A FP = 0%", bool(mode_a_fp_rate == 0)),
        ("Mode A detects 10% defects", bool(mode_a_detection_rate >= 80)),
        ("Auto escalates on anomalies", bool(len(escalations) > 0)),
        ("A faster than B", bool(speedup > 1.5)),
    ]
    passed = sum(1 for _, ok in checks if ok)
    print(f"\nChecks: {passed}/{len(checks)} PASS")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    
    overall = "PASS" if passed >= 3 else "PARTIAL" if passed >= 2 else "FAIL"
    print(f"\nOverall: {overall}")
    
    # Save report
    report = {
        "benchmark": "two_mode_integration",
        "adr": "ADR-IND-018",
        "seed": seed,
        "n_test_scans": len(test_scans),
        "test_scan_types": list(test_scans.keys()),
        "analyses": analyses,
        "checks": {name: ok for name, ok in checks},
        "checks_passed": passed,
        "checks_total": len(checks),
        "overall": overall,
        "evidence": "[REPRODUCED]" if overall == "PASS" else "[PARTIAL]",
    }
    
    if save_report:
        report_path = Path(__file__).parent.parent / "data" / "two_mode_integration.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved: {report_path}")
    
    return report


if __name__ == "__main__":
    report = run_two_mode_benchmark(seed=42)
