# Phase 3 Protocol — Real3D-AD Validation

## Objective

Validate ScanGuard on Real3D-AD benchmark dataset.

## Prerequisites

1. Download Real3D-AD dataset
2. Install requirements: `pip install numpy scipy scikit-learn trimesh`
3. Verify PCD loader works with dataset format

## Protocol Steps

1. **Data Loading**: Load each category's training set (normal samples)
2. **Calibration**: Fit detector on 5 normal samples per category
3. **Testing**: Run detection on test set (mix of normal and anomalous)
4. **Metrics**: Compute AUROC, precision, recall
5. **Reporting**: Document honest limitations and failure modes

## Expected Challenges

- Real scans may have different noise characteristics than synthetic data
- Registration may fail on some real-world scan poses
- Thresholds tuned for synthetic data may need adjustment

## Success Criteria

- AUROC > 0.8 on at least 3 categories
- <10% false positive rate on normal test samples
- Processing time <5 seconds per scan
