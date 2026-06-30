"""Synthetic defect suite: 10 defect types for benchmarking.

Each defect simulates a real industrial anomaly:
- noise_low / noise_high: scan noise (sensor artifacts)
- outliers: sensor outliers (reflections, dust)
- bulge / dent: local deformation (impact, pressure)
- twist: global torsional deformation
- scale_drift: non-uniform scaling (thermal expansion, wrong material)
- erosion: material loss (wear, corrosion)
- hole: missing material (drilling error, void)
"""

import numpy as np


def defect_none(points):
    return points.copy()


def defect_noise_low(points):
    sigma = np.ptp(points, axis=0).max() * 0.005
    return points + np.random.normal(0, sigma, points.shape)


def defect_noise_high(points):
    sigma = np.ptp(points, axis=0).max() * 0.02
    return points + np.random.normal(0, sigma, points.shape)


def defect_outliers(points, ratio=0.03):
    n = int(len(points) * ratio)
    bbox = np.ptp(points, axis=0)
    center = points.mean(axis=0)
    outliers = center + (np.random.rand(n, 3) - 0.5) * bbox * 2
    return np.vstack([points, outliers])


def defect_bulge(points, radius_percentile=20, magnitude=0.05):
    pts = points.copy()
    idx = np.random.randint(len(pts))
    bulge_center = pts[idx]
    dists = np.linalg.norm(pts - bulge_center, axis=1)
    mask = dists < np.percentile(dists, radius_percentile)
    dirs = pts[mask] - bulge_center
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    falloff = 1 - dists[mask][:, None] / (dists[mask].max() + 1e-10)
    pts[mask] += magnitude * (dirs / norms) * falloff
    return pts


def defect_dent(points, radius_percentile=15, magnitude=0.04):
    pts = points.copy()
    idx = np.random.randint(len(pts))
    dent_center = pts[idx]
    dists = np.linalg.norm(pts - dent_center, axis=1)
    mask = dists < np.percentile(dists, radius_percentile)
    dirs = pts[mask] - dent_center
    norms = np.linalg.norm(dirs, axis=1, keepdims=True)
    norms[norms == 0] = 1
    pts[mask] -= magnitude * (dirs / norms)
    return pts


def defect_twist(points, angle=0.3):
    pts = points.copy()
    center = pts.mean(axis=0)
    centered = pts - center
    angles = angle * centered[:, 2] / (np.ptp(centered[:, 2]) + 1e-10)
    cos_a, sin_a = np.cos(angles), np.sin(angles)
    x_new = cos_a * centered[:, 0] - sin_a * centered[:, 1]
    y_new = sin_a * centered[:, 0] + cos_a * centered[:, 1]
    pts[:, 0] = x_new + center[0]
    pts[:, 1] = y_new + center[1]
    return pts


def defect_scale_drift(points, axis=0, factor=1.08):
    pts = points.copy()
    center = pts.mean(axis=0)
    pts -= center
    pts[:, axis] *= factor
    pts += center
    return pts


def defect_erosion(points, ratio=0.15):
    center = points.mean(axis=0)
    mask = (points[:, 0] - center[0]) > 0
    keep = ~(mask & (np.random.rand(len(points)) < ratio))
    return points[keep].copy()


def defect_hole(points, radius_percentile=10):
    center = points.mean(axis=0)
    dists = np.linalg.norm(points - center, axis=1)
    keep = dists > np.percentile(dists, radius_percentile)
    return points[keep].copy()


DEFECT_REGISTRY = {
    "none": {"fn": defect_none, "expected": "NORMAL", "category": "clean"},
    "noise_low": {"fn": defect_noise_low, "expected": "DEFORMED", "category": "noise"},
    "noise_high": {"fn": defect_noise_high, "expected": "ANOMALOUS", "category": "noise"},
    "outliers": {"fn": defect_outliers, "expected": "ANOMALOUS", "category": "noise"},
    "bulge": {"fn": defect_bulge, "expected": "DEFORMED", "category": "structural"},
    "dent": {"fn": defect_dent, "expected": "DEFORMED", "category": "structural"},
    "twist": {"fn": defect_twist, "expected": "DEFORMED", "category": "structural"},
    "scale_drift": {"fn": defect_scale_drift, "expected": "ANOMALOUS", "category": "structural"},
    "erosion": {"fn": defect_erosion, "expected": "DEFORMED", "category": "structural"},
    "hole": {"fn": defect_hole, "expected": "ANOMALOUS", "category": "structural"},
}


def apply_defect(points, defect_name, seed=None):
    if seed is not None:
        np.random.seed(seed)
    if defect_name not in DEFECT_REGISTRY:
        raise ValueError(f"Unknown defect: {defect_name}")
    return DEFECT_REGISTRY[defect_name]["fn"](points)


def list_defects():
    return [{"name": name, "category": info["category"], "expected_verdict": info["expected"]}
            for name, info in DEFECT_REGISTRY.items()]
