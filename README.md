# GeoSpectra-Industrial

> **Spectral fingerprinting for 3D defect detection.**
> Compare a 3D scan to a reference -- get NORMAL / DEFORMED / ANOMALOUS in under a second.

```bash
python -m cli.geospectra_check reference.stl scan.ply
# ✅ NORMAL -- scan matches reference
```

## What This Does

GeoSpectra ScanGuard is a **spectral 3D inspection prototype** that detects global and local anomalies in noisy 3D scans using graph Laplacian eigenvalue fingerprinting.

**Pipeline:** 3D scan -> kNN graph -> Laplacian eigenvalues -> spectral + geometric fingerprint -> compare to reference -> verdict.

**Two-Mode Architecture (ADR-IND-018):**
- **Mode A** (Patch Bank): Registration-free, pose-invariant, ~0.3s/scan -- coarse screening
- **Mode B** (Patch Detector): ICP-aligned, exact localization, ~1.1s/scan -- precise inspection
- **Auto mode**: Fast screening -> escalation to precise mode only when needed (38% faster)

## Quick Start

```bash
git clone https://github.com/sergeeey/GeoSpectra-Industrial.git
cd GeoSpectra-Industrial
pip install -r requirements.txt
python benchmarks/two_mode_integration.py
```

## Architecture

```
core/
├── spectral_fingerprint.py    # Scale-invariant spectral + geometric features
├── anomaly_detector.py        # 3-class detector (NORMAL/DEFORMED/ANOMALOUS)
├── patch_fingerprint.py       # FPS patch sampling, local fingerprints
├── patch_detector.py          # Mode B: hierarchical with registration gate
├── patch_bank_detector.py     # Mode A: registration-free patch bank
├── two_mode_detector.py       # Unified A/B/auto selector
├── registration.py            # PCA coarse + ICP fine alignment
├── loaders.py                 # STL/PLY/OBJ/XYZ loader
└── pcd_loader.py              # PCD format for Real3D-AD

benchmarks/
├── two_mode_integration.py    # ✅ 4/4 PASS -- validates two-mode architecture
├── synthetic_defect_suite.py  # 10 defect types
├── industrial_mesh_suite.py   # 5 realistic mesh types
└── ...

tests/
└── test_core.py               # 11 tests (pytest)
```

## Project Status

**Version:** Pilot-Ready MVP v2.3 (Two-Mode)
**Date:** July 1, 2026
**ADRs:** 20 architectural decisions documented
**Code:** ~5,100 lines Python + Markdown
**Tests:** 11 tests (pytest)

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for full details.

## Key Results

| Metric | Result |
|--------|--------|
| Mode A FP (rigid transforms) | 0% |
| Mode A detection (10% defect) | 100% |
| Mode B localization | Exact patch position |
| Auto escalation | 100% (3/3) |
| Auto runtime vs Mode B | 38% faster |
| Speed (Mode A) | ~0.3s/scan |
| Speed (Mode B) | ~1.1s/scan |

## License

MIT
