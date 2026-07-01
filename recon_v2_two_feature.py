"""Phase 2 Recon — two-feature architecture validation."""

import numpy as np
from core.spectral_fingerprint import extract_fingerprint, feature_vector


def make_sphere(n=2048):
    indices = np.arange(n, dtype=float) + 0.5
    phi = np.arccos(1 - 2 * indices / n)
    theta = np.pi * (1 + 5**0.5) * indices
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return np.column_stack([x, y, z])


def main():
    print("Phase 2 Recon: Two-Feature Architecture")
    print("=" * 50)
    
    ref = make_sphere(2048)
    fp_ref = extract_fingerprint(ref)
    vec_ref = feature_vector(fp_ref)
    
    # Clean variant
    clean = ref + np.random.normal(0, 0.005, ref.shape)
    fp_clean = extract_fingerprint(clean)
    vec_clean = feature_vector(fp_clean)
    
    # Bulge
    bulge = ref.copy()
    center = bulge[0]
    dists = np.linalg.norm(bulge - center, axis=1)
    mask = dists < 0.3
    bulge[mask] += 0.05
    fp_bulge = extract_fingerprint(bulge)
    vec_bulge = feature_vector(fp_bulge)
    
    # Compare
    dist_clean = np.linalg.norm(vec_ref - vec_clean)
    dist_bulge = np.linalg.norm(vec_ref - vec_bulge)
    
    print(f"Clean distance: {dist_clean:.3f}")
    print(f"Bulge distance: {dist_bulge:.3f}")
    print(f"Separation: {dist_bulge / max(dist_clean, 0.001):.1f}x")


if __name__ == "__main__":
    main()
