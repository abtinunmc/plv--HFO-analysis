# Session Log: 2026-04-14

## Summary
Diagnosed and fixed a critical dtype mismatch bug affecting patients 0023, 0025, 0028.
Re-processed patient 0025 successfully. Created dtype detection utility script.

## Root Cause: DataType=7 Mapped to Wrong numpy dtype

### The Bug
All three pipeline scripts mapped Persyst `DataType=7` to `np.float64` (8 bytes per sample).
The actual data for patients with `DataType=7` is **int32** (4 bytes per sample).

Reading 4-byte int32 data as 8-byte float64 caused every other byte boundary to be wrong,
producing garbage values (NaN, ~10^-300) → empty/broken PLV plots.

### Affected Patients
Patients with `DataType=7` in their raw `.lay` files:
- sub-umich0023 (92 channels)
- sub-umich0025 (42 channels)
- sub-umich0027 (113 channels, no HFO data — skipped)
- sub-umich0028 (86 channels)
- sub-umich0029 (113 channels, ECoG — skipped)

### Unaffected Patients (DataType=0, int16)
- sub-umich0018, 0020, 0021, 0022, 0024, 0026, 0030

## Fixes Applied

### 1. car_reref.py (line 66)
```python
# Before:
dtype = {0: np.int16, 1: np.int32, 7: np.float64}.get(dt, np.int16)
# After:
dtype = {0: np.int16, 1: np.int32, 7: np.int32}.get(dt, np.int16)
```

### 2. band_pass.py (line 275)
```python
# Before:
7: np.float64,
# After:
7: np.int32,
```

### 3. plv_analysis.py (line 189)
```python
# Before:
dtype_map = {0: np.int16, 1: np.int32, 7: np.float64}
# After:
dtype_map = {0: np.int16, 1: np.int32, 7: np.int32}
```

## New Script: detect_dtype_mismatch.py
Created `scripts/detect_dtype_mismatch.py` to scan all subjects' `.lay`/`.dat` pairs
and detect which dtype code each patient uses before running the pipeline.

Usage:
```bash
python detect_dtype_mismatch.py              # scan all subjects
python detect_dtype_mismatch.py sub-umich0025  # scan one subject
```

## Patient 0025 Re-processed

| Step | Status | Notes |
|------|--------|-------|
| Step 1 (preprocesspython.py) | Already done | Not re-run |
| Step 2 (car_reref.py) | OK | Re-run with int32 fix |
| Step 3 (band_pass.py) | OK | Re-run with int32 fix |
| Step 4 (plv_analysis.py) | OK | Re-run with int32 fix |

**Results:**
- Runs: 12
- Channels: 20 good SEEG
- Total HFOs: 5993
- Global mean PLV: 0.620 ± 0.058
- PLV range: [0.544, 0.792]
- Strongest connections: RH5-RH6 (0.792), RH6-RH7 (0.787), RH7-RH8 (0.779)
- Clear block structure: LH and RH electrode clusters

## Still To Do
- Re-run pipeline for sub-umich0023 (steps 2-4)
- Re-run pipeline for sub-umich0028 (steps 2-4)
- Process remaining ~107 SEEG subjects
- Fix final PLV visualization crash (NaN histogram) — now resolved by dtype fix

## Dtype Detection Method
DataType codes in Persyst `.lay` files for this dataset:
- `DataType=0` → `np.int16` (2 bytes/sample)
- `DataType=1` → `np.int32` (4 bytes/sample)
- `DataType=7` → `np.int32` (4 bytes/sample) ← was wrongly float64

Note: int32 and float32 both use 4 bytes, so file size alone cannot distinguish them.
Dtype is confirmed by reading raw bytes and checking if values are plausible EEG ADC counts
(e.g., small integers × calibration 0.2 = µV values in ~0–30 µV range for SEEG).
