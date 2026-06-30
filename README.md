# GeoSpectra Industrial

**Spectral fingerprinting for industrial defectoscopy and quality control.**

Detect hidden deformations, global geometry changes, and anomalies in 3D scans using graph Laplacian spectral analysis.

---

## What it does

```
Normal part 3D scan     →  spectral fingerprint (reference)
Test part 3D scan       →  spectral fingerprint (test)
                         →  anomaly score
                         →  verdict: NORMAL / DEFORMED / ANOMALOUS
```

**Core idea:** Every 3D geometry has a unique spectral signature. Disorder (defects, deformations, noise) changes this signature in measurable ways. By comparing spectral fingerprints, we detect anomalies that visual inspection misses.

---

## Applications

| Industry | Use Case |
|----------|----------|
| **Aerospace** | Turbine blade deformation, crack detection |
| **Automotive** | Part conformity, casting defect detection |
| **3D Printing** | Print quality control, layer anomaly detection |
| **Micromechanics** | MEMS structure verification |
| **Medical implants** | Prosthetic geometry conformity |
| **CT/3D Scanning** | Internal defect detection via point clouds |

---

## Quick Start

```bash
git clone https://github.com/sergeeey/GeoSpectra-Industrial.git
cd GeoSpectra-Industrial
pip install -r requirements.txt
python examples/demo_defectoscopy.py
```

---

## How it works

1. **Point cloud → kNN graph** — build graph from 3D points
2. **Graph → Laplacian spectrum** — extract low eigenvalues
3. **Spectrum → fingerprint** — density bins + geometric invariants
4. **Fingerprint comparison** — L1 distance between reference and test
5. **Anomaly score** — normalized distance → verdict

Based on verified spectral recoverability research from [GeoSpectra Lab](https://github.com/sergeeey/N-7-GeoSpectra-Lab).

---

## Status

**MVP — early development.** Core algorithm verified on synthetic geometries. Industrial datasets integration in progress.

---

## License

MIT
