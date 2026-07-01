# GeoSpectra ScanGuard

Spectral 3D inspection for industrial defect detection.

## Quick Start

```bash
pip install numpy scipy scikit-learn trimesh
python -m pytest tests/test_core.py -v
python benchmarks/two_mode_integration.py
```

## Architecture

- **Mode A** (`core/patch_bank_detector.py`): Registration-free coarse screening. 0% FP on rigid transforms, ~0.3s/scan.
- **Mode B** (`core/patch_detector.py`): ICP-based precise localization. Exact defect position, ~1.1s/scan.
- **Auto** (`core/two_mode_detector.py`): Escalates from A to B on high-confidence anomalies. 38% faster than B alone.

## Key Files

| File | Purpose |
|------|---------|
| `core/spectral_fingerprint.py` | kNN Laplacian eigenvalue fingerprinting |
| `core/anomaly_detector.py` | 3-class detector (NORMAL/DEFORMED/ANOMALOUS) |
| `core/patch_bank_detector.py` | Mode A: registration-free patch bank |
| `core/two_mode_detector.py` | Unified A/B/auto selector |
| `core/registration.py` | PCA coarse + ICP fine alignment |
| `benchmarks/two_mode_integration.py` | Integration validation (4/4 PASS) |
| `ADR.md` | 20 architectural decisions |

## License

MIT
