# GeoSpectra ScanGuard

> **Spectral 3D Inspection for Noisy Scans**

---

## In One Sentence

ScanGuard compares a 3D scan to a reference -- and tells you if the part is normal, deformed, has a local defect, or if the scan itself is unreliable.

## The Problem

3D scans are noisy, incomplete, and hard to compare to CAD. Existing tools:
- Need perfect alignment (expensive, slow)
- Report "defect" on misaligned scans (false alarms)
- Miss small local defects (< 5% of surface)

## The Solution

Three-layer inspection:

```
+-----------------------------------------+
|  1. REGISTRATION                        |
|     PCA coarse + ICP fine alignment     |
|     -> confidence score                 |
+-----------------------------------------+
|  2. GLOBAL LAYER                        |
|     Whole-object spectral fingerprint   |
|     -> scan noise / scale / deformation |
+-----------------------------------------+
|  3. PATCH LAYER                         |
|     Local patch fingerprints (top-k)    |
|     -> bulge, dent, erosion, void       |
+-----------------------------------------+
|  DECISION: rule-based, not black box    |
|  NORMAL / DEFORMED / LOCAL_DEFECT /     |
|  UNRELIABLE_ALIGNMENT                   |
+-----------------------------------------+
```

## Key Differentiator

> **Safe rejection of bad scans.**
>
> Instead of falsely calling a misaligned scan "defective",
> ScanGuard says "UNRELIABLE_ALIGNMENT -- rescan needed."
>
> This prevents expensive false rejections of good parts.

## Two-Mode Architecture (v2.3)

**Mode A -- Registration-Free Patch Bank:**
- No alignment needed -- works on scans in any pose
- Fast: ~0.3s per scan
- Best for: coarse screening, unknown scan orientation

**Mode B -- ICP-Aligned Patch Detector:**
- Precise alignment + exact defect localization
- ~1.1s per scan
- Best for: metrology-grade inspection, known orientation

**Auto Mode:**
- Fast screening (Mode A) + automatic escalation to precise mode (Mode B) only when anomaly detected
- 38% faster than running Mode B on every scan

## Demo

```bash
# Install dependencies
pip install numpy scipy scikit-learn trimesh

# Run two-mode benchmark
python benchmarks/two_mode_integration.py

# Check a scan (via Python module)
python -m cli.geospectra_check reference.stl scan.ply --mode auto
```

## Current Status (Honest)

| Capability | Status | Evidence |
|------------|--------|----------|
| Scale-invariant fingerprint | Validated | Perfect (diff = 0.000) |
| Noise/outlier detection | Validated | 100% synthetic detection |
| Local defects (5-20%) | Validated | 100% after registration |
| Local defects (1%) | Partial | 75% after registration |
| Registration (pose variation) | Validated | 0% false positives |
| Registration-free screening (Mode A) | Validated | 0% FP on rigid transforms |
| Auto escalation | Validated | 100% success (3/3) |
| **Real scan validation** | **PENDING** | **Seeking partners** |
| Heavy noise (1%) | 23% FP | Known limitation |
| Production certification | No | R&D prototype |

## What We Need

**5-20 anonymized 3D scans** (STL/PLY/PCD) from industrial partners:
- 3D printing service bureaus
- CT / metrology labs
- Additive manufacturing R&D
- Reverse engineering studios

## Technology Stack

- **Language:** Python 3.11+
- **Core:** NumPy, SciPy sparse, scikit-learn
- **3D:** trimesh, PCD loader (no Open3D dependency)
- **Speed:** CPU-only, < 2s per scan
- **No deep learning** -- deterministic, interpretable
- **No GPU required**

## Architecture Decisions (20 ADRs)

All key decisions documented with evidence. See: `ADR.md`

## License

MIT -- open core. Free for research and pilot evaluation.
