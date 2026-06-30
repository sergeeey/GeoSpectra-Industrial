# Evidence Status Labels -- GeoSpectra ScanGuard

> **"Uncertainty is not a bug -- it is a product feature."**

---

## Label Hierarchy

| Label | Confidence Cap | Meaning | Action |
|-------|---------------|---------|--------|
| **VALIDATED** | <= 0.90 | Confirmed by independent reproduction | Use for decisions |
| **PARTIAL** | <= 0.70 | Works in controlled conditions, needs more data | Use with caution |
| **BELOW-VALIDATED-RANGE** | <= 0.30 | Outside validated operating range | Do not use for decisions; document limitation |
| **UNRELIABLE_ALIGNMENT** | N/A | Registration failed or scan quality insufficient | Rescan and retry |
| **BAD_SCAN** | N/A | Fingerprint extraction failed | Check scan format and quality |

## Label Assignment Rules

### VALIDATED
- Clean-clone reproduction successful
- Multiple runs give consistent results
- Hard negatives pass
- Independent reviewer confirmed

### PARTIAL
- Synthetic validation successful
- Structure verified but numerical values stochastic
- Real data pending
- Known limitations documented

### BELOW-VALIDATED-RANGE
- Below minimum validated defect size (e.g., < 1% for local defects)
- Below minimum validated point count
- New mesh type not in validation set
- Threshold sensitivity high in this region

### UNRELIABLE_ALIGNMENT
- Registration confidence < threshold (0.5)
- ICP did not converge
- RMSE > 3% of object size
- Significant pose variation detected

### BAD_SCAN
- Too few points (< 100)
- Non-finite coordinates (NaN/Inf)
- Unsupported file format
- Fingerprint extraction error

---

*Evidence Labels v1.0 | June 30, 2026*
