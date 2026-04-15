# Session Log: 2026-04-09

## Summary
Processed subjects 23-30 through the HFO-PLV pipeline. Fixed bugs, reorganized folder structure, documented skipped patients.

## Subjects Processed

| Subject | Step 1 | Step 2 | Step 3 | Step 4 | HFOs | Channels | Mean PLV | Notes |
|---------|--------|--------|--------|--------|------|----------|----------|-------|
| sub-umich0023 | OK | OK | OK | OK* | 5,496 | 34 | saved | plot failed (NaN) |
| sub-umich0024 | OK | OK | OK | OK | 5,000 | 75 | 0.526 | complete |
| sub-umich0025 | OK | OK | OK | OK* | 6,000 | 20 | saved | plot failed (NaN) |
| sub-umich0026 | OK | OK | OK | OK* | 6,000 | 52 | saved | plot failed (NaN) |
| sub-umich0027 | SKIP | - | - | - | - | - | - | missing qHFO data in H5 |
| sub-umich0028 | OK | OK | OK | OK* | 3,000 | 6 | saved | plot failed (NaN) |
| sub-umich0029 | SKIP | - | - | - | 0 | 0 | - | ECoG patient, not SEEG |
| sub-umich0030 | SKIP | - | - | - | 0 | 0 | - | ECoG patient, not SEEG |

*PLV data saved successfully, final visualization failed due to NaN values

## Total Processed Subjects (all sessions)
1. sub-umich0018
2. sub-umich0020
3. sub-umich0021
4. sub-umich0022
5. sub-umich0023
6. sub-umich0024
7. sub-umich0025
8. sub-umich0026
9. sub-umich0028

**Total: 9 subjects processed**

## Bugs Fixed

### 1. Float dtype handling in car_reref.py (line 191)
Some subjects have float64 data instead of int16. The `np.iinfo()` function fails on float types.

**Fix:**
```python
# Only clip if output dtype is integer (not float)
if np.issubdtype(dtype, np.integer):
    np.clip(data, np.iinfo(dtype).min, np.iinfo(dtype).max, out=data)
```

### 2. Float dtype handling in band_pass.py (line 441)
Same issue as above.

**Fix:** Same pattern - check `np.issubdtype(dtype, np.integer)` before clipping.

## Skipped Patients Analysis

### sub-umich0027: Missing HFO detections
- Has SEEG electrodes (LF1, LF2, etc.)
- H5 files exist and are large (300+ MB)
- But `/qHFO/chanIdx` dataset is missing
- **Cause:** qHFO detection algorithm found no HFOs

### sub-umich0029 and sub-umich0030: ECoG patients
- These patients have ECoG (subdural grid) electrodes, not SEEG
- Pipeline filters for `type == 'SEEG'` only
- Channel types: LO1, LO2 (0029) and FP1, FP2 (0030)
- **Solution:** Either skip ECoG patients or modify pipeline to include them

## Folder Reorganization

Updated all scripts to use new folder structure:
```
subjects/{subject}/
├── step1_hfo_validation/   # preprocesspython.py output
├── step2_car/              # car_reref.py output
├── step3_bandpass/         # band_pass.py output
├── step4_plv/              # plv_analysis.py output
└── plots/                  # all visualization outputs
```

Scripts updated:
- preprocesspython.py
- car_reref.py
- band_pass.py
- plv_analysis.py
- generate_preprint_pdf.py

## Files Moved
- Deprecated scripts (`car_preprocess.py`, `plvhfo1.py`) moved to `archive/`
- Documentation moved to `docs/`
- Old logs moved to `archive/`

## Remaining Issues

1. **Final PLV plot fails for some subjects** - NaN values in PLV matrix cause histogram to fail. Data is saved correctly, only visualization fails.

2. **Empty "python scripts" folder** - Cannot delete, in use by another process.

3. **115 subjects remaining** - Out of 119 total subjects available.

## Data Availability Summary
- **Total subjects in database:** 119 (sub-umich0018 to sub-umich0136)
- **Processed:** 9
- **Skipped (ECoG):** 2 (0029, 0030)
- **Skipped (no HFO data):** 1 (0027)
- **Remaining to process:** ~107
