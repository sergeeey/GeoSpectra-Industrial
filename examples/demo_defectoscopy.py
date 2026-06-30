"""
Demo: Industrial defectoscopy with spectral fingerprinting.

Simulates quality control scenario:
1. Reference: normal sphere point cloud
2. Test scans: spheres with variations + different shapes
3. Verdict: NORMAL / DEFORMED / ANOMALOUS

Usage: python examples/demo_defectoscopy.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from core.anomaly_detector import SpectralAnomalyDetector


def sphere(n=500, r=1.0, noise=0.0, seed=42):
    """Generate sphere point cloud."""
    rng = np.random.default_rng(seed)
    pts = rng.standard_normal((n, 3))
    pts = pts / np.linalg.norm(pts, axis=1, keepdims=True) * r
    if noise > 0:
        pts += rng.normal(0, noise, pts.shape)
    return pts


def cube(n=500, size=1.0, seed=42):
    """Generate cube point cloud."""
    rng = np.random.default_rng(seed)
    return rng.uniform(-size/2, size/2, (n, 3))


def cylinder(n=500, r=1.0, h=2.0, seed=42):
    """Generate cylinder point cloud."""
    rng = np.random.default_rng(seed)
    theta = rng.uniform(0, 2*np.pi, n)
    z = rng.uniform(-h/2, h/2, n)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.column_stack([x, y, z])


def sphere_with_pit(n=500, r=1.0, pit_size=0.3, seed=42):
    """Sphere with pit/crack (simulating defect)."""
    rng = np.random.default_rng(seed)
    pts = rng.standard_normal((n, 3))
    pts = pts / np.linalg.norm(pts, axis=1, keepdims=True) * r
    pit_center = np.array([r, 0, 0])
    dists = np.linalg.norm(pts - pit_center, axis=1)
    mask = dists > pit_size
    pts_filtered = pts[mask]
    n_pit = n - len(pts_filtered)
    if n_pit > 0:
        pit_pts = pit_center + rng.normal(0, pit_size/3, (n_pit, 3))
        pts_filtered = np.vstack([pts_filtered, pit_pts])
    return pts_filtered[:n]


def main():
    print("="*60)
    print("GEOSPECTRA INDUSTRIAL — Defectoscopy Demo")
    print("="*60)
    
    # 1. Reference: normal sphere
    print("\n[1] Training reference fingerprint...")
    ref = sphere(n_points=500, radius=1.0, noise=0.01)
    detector = SpectralAnomalyDetector(k_neighbors=12, k_eigen=15)
    detector.fit_reference(ref)
    
    # 2. Calibrate thresholds with normal variants
    normal_scans = [
        sphere(500, 1.0, 0.02, 43),
        sphere(500, 1.0, 0.03, 44),
        sphere(500, 0.95, 0.01, 45),
        sphere(500, 1.05, 0.01, 46),
    ]
    t_n, t_d = detector.calibrate(normal_scans)
    print(f"    Calibrated: NORMAL<{t_n:.4f}, DEFORMED<{t_d:.4f}")
    
    # 3. Test parts
    print("\n[2] Testing parts:")
    tests = [
        ("Normal (low noise)", sphere(500, 1.0, 0.02, 47)),
        ("Normal (med noise)", sphere(500, 1.0, 0.04, 48)),
        ("Deformed (small pit)", sphere_with_pit(500, 1.0, 0.2, 49)),
        ("Deformed (large pit)", sphere_with_pit(500, 1.0, 0.4, 50)),
        ("Wrong shape (cube)", cube(500, 1.5)),
        ("Wrong shape (cylinder)", cylinder(500, 0.7, 1.5)),
    ]
    
    results = []
    for name, pts in tests:
        r = detector.detect(pts)
        results.append((name, r))
        sym = {"NORMAL": "G", "DEFORMED": "Y", "ANOMALOUS": "R"}[r["verdict"]]
        print(f"    [{sym}] {name:25s}: score={r['score']:.4f} -> {r['verdict']}")
    
    # 4. Summary
    print("\n[3] Summary:")
    n = sum(1 for _, r in results if r["verdict"] == "NORMAL")
    d = sum(1 for _, r in results if r["verdict"] == "DEFORMED")
    a = sum(1 for _, r in results if r["verdict"] == "ANOMALOUS")
    print(f"    NORMAL: {n}, DEFORMED: {d}, ANOMALOUS: {a}")
    
    print("\n    Expected: normals detected, defects flagged,")
    print("    wrong shapes marked ANOMALOUS")
    print("="*60)
    print("\nNext steps for real industrial use:")
    print("  1. Load real 3D scans (STL/PLY/OBJ)")
    print("  2. Calibrate on your normal parts")
    print("  3. Set thresholds per industry standard")
    print("  4. Integrate into CT/3D scanning pipeline")
    print("="*60)


if __name__ == "__main__":
    main()
