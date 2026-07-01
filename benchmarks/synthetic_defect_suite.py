"""Synthetic defect suite: 10 defect types for benchmarking."""

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
    n_remove = int(len(points) * ratio)
    idx = np.random.choice(len(points), len(points) - n_remove, replace=False)
    return points[idx]


def defect_hole(points, radius_percentile=10):
    pts = points.copy()
    center = pts[np.random.randint(len(pts))]
    dists = np.linalg.norm(pts - center, axis=1)
    threshold = np.percentile(dists, radius_percentile)
    return pts[dists > threshold]


DEFECTS = {
    "none": defect_none,
    "noise_low": defect_noise_low,
    "noise_high": defect_noise_high,
    "outliers": defect_outliers,
    "bulge": defect_bulge,
    "dent": defect_dent,
    "twist": defect_twist,
    "scale_drift": defect_scale_drift,
    "erosion": defect_erosion,
    "hole": defect_hole,
}
