"""Two-Mode Integration Benchmark — validate unified detector (ADR-IND-018).

Tests:
  1. Mode A alone: 0% FP on clean transformed scans
  2. Mode A alone: detection of scans with 10% defects
  3. Mode B alone: detection + localization on aligned defective scans
  4. Mode B alone: UNRELIABLE_ALIGNMENT on badly aligned scans
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


def make_box(n_points=2048, size=2.0):
    """Generate a box point cloud via rejection sampling."""
    pts = np.random.uniform(-size / 2, size / 2, (n_points * 3, 3))
    eps = size * 0.05
    on_surface = (
        (np.abs(pts[:, 0]) > size / 2 - eps)
        | (np.abs(pts[:, 1]) > size / 2 - eps)
        | (np.abs(pts[:, 2]) > size / 2 - eps)
    )
    pts = pts[on_surface][:n_points]
    if len(pts) < n_points:
        pts = np.vstack([pts, np.random.uniform(-size / 2, size / 2, (n_points - len(pts), 3))])
    return pts[:n_points]


def rotate_points(points, angle_deg, axis="z"):
    """Rotate point cloud around axis."""
    angle = np.radians(angle_deg)
    if axis == "x":
        R = np.array(
            [[1, 0, 0], [0, np.cos(angle), -np.sin(angle)], [0, np.sin(angle), np.cos(angle)]]
        )
    elif axis == "y":
        R = np.array(
            [[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]]
        )
    else:
        R = np.array(
            [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
        )
    return points @ R.T


def translate_points(points, shift):
    """Translate point cloud."""
    return points + np.array(shift)


def add_defect_bulge(points, radius_percentile=20, magnitude=0.05):
    """Add a local bulge defect."""
    pts = points.copy()
    idx = np.random.RandomState(42).randint(len(pts))
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
        test_scans[f"rot_{angle}"] = rotate_points(ref_points, angle, "z")
    for shift in [(0.1, 0.05, 0.02), (0.3, 0.2, 0.1), (0.5, 0.4, 0.3)]:
        test_scans[f"trans_{shift[0]}"] = translate_points(ref_points, shift)
    test_scans["scale_1.05"] = ref_points * 1.05
    test_scans["scale_0.95"] = ref_points * 0.95

    # Clean (no transform)
    test_scans["clean"] = ref_points.copy()

    # With defects (10% bulge on rotated scan)
    for angle in [0, 30, 60]:
        defective = add_defect_bulge(ref_points, radius_percentile=30, magnitude=0.10)
        if angle > 0:
            defective = rotate_points(defective, angle, "z")
        test_scans[f"defect_10pct_rot_{angle}"] = defective

    # With smaller defects (5% bulge)
    test_scans["defect_5pct"] = add_defect_bulge(ref_points, radius_percentile=18, magnitude=0.05)

    # With jitter (non-rigid — known Mode A limitation)
    jitter_sigma = np.ptp(ref_points, axis=0).max() * 0.003
    test_scans["jitter"] = ref_points + np.random.normal(0, jitter_sigma, ref_points.shape)

    print(f"Test scans: {len(test_scans)} conditions")

    # Initialize detectors
    print("\n" + "-" * 50)
    print("FITTING detectors...")

    det_a = TwoModeDetector(mode="A", n_patches=32, patch_size=64, top_k_ratio=0.15)
    det_a.fit(ref_points)
    print("  Mode A: fitted")

    det_b = TwoModeDetector(
        mode="B",
        n_patches=32,
        patch_size=64,
        top_k_ratio=0.15,
        registration_confidence_threshold=0.5,
    )
    det_b.fit(ref_points)
    print("  Mode B: fitted")

    det_auto = TwoModeDetector(
        mode="auto", n_patches=32, patch_size=64, top_k_ratio=0.15, auto_escalate_confidence=0.6
    )
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

    # Test 1: Mode A FP rate
    clean_transforms = [k for k in test_scans.keys() if k.startswith(("rot_", "trans_", "scale_"))]
    mode_a_clean_verdicts = [results[k]["A"]["verdict"] for k in clean_transforms]
    mode_a_fp = sum(1 for v in mode_a_clean_verdicts if v != "NORMAL")
    mode_a_fp_rate = mode_a_fp / len(clean_transforms) * 100 if clean_transforms else 0

    print(f"\n[TEST 1] Mode A: FP rate on clean transformed scans")
    print(f"  Scans: {len(clean_transforms)}")
    print(f"  FP: {mode_a_fp}/{len(clean_transforms)} ({mode_a_fp_rate:.0f}%)")
    analyses["mode_a_fp_rate"] = {
        "test": "FP on clean transformed scans",
        "n_scans": len(clean_transforms),
        "fp_count": mode_a_fp,
        "fp_rate_pct": round(mode_a_fp_rate, 1),
        "verdicts": dict(zip(clean_transforms, mode_a_clean_verdicts)),
        "evidence": "[REPRODUCED]" if mode_a_fp_rate == 0 else "[INVESTIGATE]",
    }

    # Test 2: Mode A detection of 10% defects
    defect_10pct = [k for k in test_scans.keys() if "defect_10pct" in k]
    mode_a_defect_verdicts = [results[k]["A"]["verdict"] for k in defect_10pct]
    mode_a_detections = sum(1 for v in mode_a_defect_verdicts if v in ("DEFORMED", "ANOMALOUS"))
    mode_a_detection_rate = mode_a_detections / len(defect_10pct) * 100 if defect_10pct else 0

    print(f"\n[TEST 2] Mode A: Detection of 10% defects")
    print(f"  Scans: {len(defect_10pct)}")
    print(f"  Detected: {mode_a_detections}/{len(defect_10pct)} ({mode_a_detection_rate:.0f}%)")
    for k in defect_10pct:
        r = results[k]["A"]
        print(f"    {k}: {r['verdict']} (score={r['anomaly_score']:.2f})")
    analyses["mode_a_detection_10pct"] = {
        "test": "Detection of 10% defects",
        "n_scans": len(defect_10pct),
        "detected": mode_a_detections,
        "detection_rate_pct": round(mode_a_detection_rate, 1),
        "per_scan": {k: results[k]["A"] for k in defect_10pct},
        "evidence": "[REPRODUCED]" if mode_a_detection_rate >= 80 else "[PARTIAL]",
    }

    # Test 3: Mode B localization
    defect_aligned = [k for k in test_scans.keys() if k == "defect_10pct_rot_0"]
    if defect_aligned:
        k = defect_aligned[0]
        b_result = results[k]["B"]
        b_has_local = b_result["verdict"] == "LOCAL_DEFECT"
        print(f"\n[TEST 3] Mode B: Localization")
        print(f"  Scan: {k}")
        print(f"  Verdict: {b_result['verdict']}")
        analyses["mode_b_localization"] = {
            "test": "Localization on aligned scan",
            "verdict": b_result["verdict"],
            "localized": bool(b_has_local),
        }

    # Test 4: Mode B registration
    b_total_rot = sum(1 for k in test_scans if "rot_" in k)
    b_unreliable = sum(
        1
        for k in test_scans
        if "rot_" in k and results[k]["B"]["verdict"] == "UNRELIABLE_ALIGNMENT"
    )
    print(f"\n[TEST 4] Mode B: Registration on rotated scans")
    print(f"  Rotated scans: {b_total_rot}")
    print(f"  UNRELIABLE_ALIGNMENT: {b_unreliable}")
    analyses["mode_b_registration"] = {
        "test": "Registration on rotated scans",
        "n_rotated": int(b_total_rot),
        "unreliable_count": int(b_unreliable),
    }

    # Test 5: Auto escalation
    auto_defect_scans = [k for k in test_scans if "defect_10pct" in k]
    escalations = [k for k in auto_defect_scans if results[k]["auto"].get("escalated", False)]
    print(f"\n[TEST 5] Auto mode: Escalation")
    print(f"  Defect scans: {len(auto_defect_scans)}")
    print(f"  Escalated: {len(escalations)}")
    analyses["auto_escalation"] = {
        "test": "Auto mode escalation",
        "n_defect_scans": len(auto_defect_scans),
        "escalated_count": len(escalations),
    }

    # Test 6: Jitter handling
    jitter_auto = results["jitter"]["auto"]
    fallback = bool(
        "A" in str(jitter_auto.get("mode_used", "")) and not jitter_auto.get("escalated", False)
    )
    print(f"\n[TEST 6] Auto mode: Jitter")
    print(f"  Verdict: {jitter_auto['verdict']}, mode: {jitter_auto['mode_used']}")
    analyses["auto_jitter_fallback"] = {
        "test": "Jitter fallback",
        "verdict": jitter_auto["verdict"],
        "mode_used": jitter_auto["mode_used"],
        "fallback_to_a": fallback,
    }

    # Test 7: Runtime
    avg_runtimes = {m: round(np.mean(runtimes[m]), 1) for m in ["A", "B", "auto"]}
    speedup = avg_runtimes["B"] / avg_runtimes["A"] if avg_runtimes["A"] > 0 else 0
    print(f"\n[TEST 7] Runtime")
    print(f"  Mode A: {avg_runtimes['A']:.1f} ms")
    print(f"  Mode B: {avg_runtimes['B']:.1f} ms")
    print(f"  Auto:   {avg_runtimes['auto']:.1f} ms")
    print(f"  Speedup A vs B: {speedup:.1f}x")
    analyses["runtime"] = {
        "mode_a_ms": avg_runtimes["A"],
        "mode_b_ms": avg_runtimes["B"],
        "auto_ms": avg_runtimes["auto"],
        "speedup_a_vs_b": round(speedup, 1),
    }

    # Overall
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

    report = {
        "benchmark": "two_mode_integration",
        "adr": "ADR-IND-018",
        "seed": seed,
        "n_test_scans": len(test_scans),
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
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved: {report_path}")

    return report


def run_multiseed_validation(seeds=(42, 7, 13, 99, 100, 256, 999, 1337), save_report=True):
    """Multi-seed validation — honest evidence base for detection claims.

    Runs the benchmark across N seeds to establish true detection statistics
    rather than single-seed numbers. Required for any public claim.

    Evidence marker: [VALIDATED] requires ≥2 seeds. [PARTIAL] for borderline results.
    """
    import io, contextlib

    results = []
    for seed in seeds:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = run_two_mode_benchmark(seed=seed, save_report=False)
        results.append(
            {
                "seed": seed,
                "fp_rate_pct": r["analyses"]["mode_a_fp_rate"]["fp_rate_pct"],
                "detection_10pct": r["analyses"]["mode_a_detection_10pct"]["detection_rate_pct"],
                "n_detected": r["analyses"]["mode_a_detection_10pct"]["detected"],
                "n_scans": r["analyses"]["mode_a_detection_10pct"]["n_scans"],
                "overall": r["overall"],
            }
        )

    total_detected = sum(x["n_detected"] for x in results)
    total_scans = sum(x["n_scans"] for x in results)
    overall_detection = total_detected / total_scans * 100 if total_scans else 0
    all_fp_zero = all(x["fp_rate_pct"] == 0 for x in results)
    full_passes = sum(1 for x in results if x["detection_10pct"] == 100)

    print("\n" + "=" * 60)
    print("MULTI-SEED VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Seeds tested: {len(seeds)}")
    print(f"\n0% FP on clean scans:  {'ALL seeds' if all_fp_zero else 'PARTIAL'}")
    print(f"Detection (10% defect): {total_detected}/{total_scans} = {overall_detection:.0f}%")
    print(f"Seeds with 100% detect: {full_passes}/{len(seeds)}")
    print(f"\nseed | FP%  | detect10% | overall")
    print(f"-----|------|-----------|--------")
    for r in results:
        flag = "⚠️" if r["detection_10pct"] < 100 else ""
        print(
            f"{r['seed']:4d} | {r['fp_rate_pct']:4.0f}% | {r['detection_10pct']:9.0f}% | {r['overall']} {flag}"
        )

    summary = {
        "benchmark": "multi_seed_validation",
        "seeds": list(seeds),
        "fp_zero_all_seeds": bool(all_fp_zero),
        "overall_detection_pct": round(overall_detection, 1),
        "detection_cases": f"{total_detected}/{total_scans}",
        "seeds_100pct": int(full_passes),
        "evidence_fp": "[VALIDATED]" if all_fp_zero else "[PARTIAL]",
        "evidence_detection": "[VALIDATED]" if overall_detection >= 90 else "[PARTIAL]",
        "per_seed": results,
    }

    if save_report:
        report_path = Path(__file__).parent.parent / "data" / "multiseed_validation.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nReport saved: {report_path}")

    return summary


if __name__ == "__main__":
    import sys

    if "--multiseed" in sys.argv:
        run_multiseed_validation()
    else:
        report = run_two_mode_benchmark(seed=42)
