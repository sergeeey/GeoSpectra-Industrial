# Robustness Lock Results — Phase 2.1

## Critical Discovery

**Without registration, patch detector produces 100% false positives on ANY rotated or translated scan.**

This is not a bug — it is a fundamental architectural constraint. Deterministic patch centers require the scan to be in the same coordinate frame as the reference.

### Implications

1. **Registration is mandatory** for patch-based anomaly detection (ADR-IND-012)
2. Scans must be approximately aligned before patch comparison
3. The system should reject (not misclassify) poorly aligned scans

### Solutions Implemented

1. **ADR-IND-013**: Registration gate — block patch layer if alignment fails
2. **ADR-IND-014**: PCA coarse + ICP fine alignment
3. **ADR-IND-018**: Two-mode architecture — registration-free Mode A as alternative
