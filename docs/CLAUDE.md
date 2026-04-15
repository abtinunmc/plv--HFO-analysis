# HFO-PLV Analysis Project

## Overview
Phase-Locking Value (PLV) analysis pipeline for High-Frequency Oscillations (HFOs) in SEEG data from epilepsy patients. Goal: measure synchronization between brain regions during HFOs to understand connectivity patterns, especially thalamus involvement.

## Folder Structure

```
MATLAB/
├── scripts/                    # Active Python scripts
│   ├── preprocesspython.py    # Step 1: HFO validation
│   ├── car_reref.py           # Step 2: CAR re-referencing
│   ├── band_pass.py           # Step 3: Bandpass filtering
│   ├── plv_analysis.py        # Step 4: PLV computation
│   └── generate_preprint_pdf.py
├── subjects/                   # Per-patient output
│   └── sub-umichXXXX/
│       ├── step1_hfo_validation/
│       ├── step2_car/
│       ├── step3_bandpass/
│       ├── step4_plv/
│       └── plots/
├── docs/                       # Documentation
├── archive/                    # Old files
└── .claude/                    # Claude memory
```

## Pipeline Steps

| Step | Script | Input | Output | Status |
|------|--------|-------|--------|--------|
| 1 | `preprocesspython.py` | H5 (qHFO), channels.tsv | `step1_hfo_validation/step3_validated_qHFO_run-XX.mat` | Done |
| 2 | `car_reref.py` | Raw .dat/.lay, step1 .mat | `step2_car/*.dat, *.lay, *_seg_lengths.npy` | Done |
| 3 | `band_pass.py` | step2_car/ | `step3_bandpass/*_CAR_bp.dat` | Done |
| 4 | `plv_analysis.py` | step3_bandpass/, step1 | `step4_plv/plv_*.mat, *.csv` | Done |

## Data Paths

- **Raw data:** `U:\shared\database\ieeg-UM\rawdata\{subject}\ses-ieeg01\ieeg\`
- **H5 files:** `U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\`
- **Output base:** `C:\Users\aakhtari\Documents\MATLAB\subjects\{subject}\`

## Analyzed Patients (9 total)
| Subject | Runs | Channels | HFOs | Mean PLV | DataType |
|---------|------|----------|------|----------|----------|
| sub-umich0018 | 5 | 32 | ~2,500 | - | int16 (0) |
| sub-umich0020 | 5 | 26 | 3,846 | 0.761 | int16 (0) |
| sub-umich0021 | 11 | 46 | 4,590 | 0.665 | int16 (0) |
| sub-umich0022 | 11 | 44 | 5,476 | 0.577 | int16 (0) |
| sub-umich0023 | 11 | 34 | 5,496 | needs rerun | int32 (7) |
| sub-umich0024 | 10 | 75 | 5,000 | 0.526 | int16 (0) |
| sub-umich0025 | 12 | 20 | 5,993 | 0.620 | int32 (7) |
| sub-umich0026 | 12 | 52 | 6,000 | saved | int16 (0) |
| sub-umich0028 | 6 | 6 | 3,000 | needs rerun | int32 (7) |

## Skipped Patients
- **sub-umich0027**: Missing qHFO data in H5 file (SEEG patient)
- **sub-umich0029**: ECoG patient (pipeline filters SEEG only)
- **sub-umich0030**: ECoG patient (pipeline filters SEEG only)

## Key Parameters
- Sampling rate: 4096 Hz
- HFO band: 80-500 Hz
- Filter: Elliptic, order 10, 0.5dB passband ripple, 65dB stopband
- Max HFOs per run: 500 (random subset)
- Filter padding: 100 samples reflection padding per segment
- Hilbert edge trim: 15 samples (~3.7 ms) from each edge

## Technical Fixes Applied
1. **Segment ordering**: CAR saves `seg_lengths.npy` to track exact order of segments written
2. **Filter transients**: Segment-wise filtering with reflection padding (not continuous)
3. **Hilbert edge effects**: Trim 15 samples from each segment edge before PLV
4. **Integer dtype clip check**: Check `np.issubdtype(dtype, np.integer)` before clipping in car_reref.py and band_pass.py
5. **DataType=7 mapping**: Persyst code 7 = int32 (NOT float64 or float32). Fixed in car_reref.py, band_pass.py, plv_analysis.py. Affected patients: 0023, 0025, 0028.

## File Formats
- `.dat`: Raw binary EEG (int16, interleaved channels)
- `.lay`: Persyst header (INI-style)
- `.mat`: MATLAB format (scipy.io compatible)
- `.h5`: HDF5 format for HFO events

## How to Run
```bash
cd "C:\Users\aakhtari\Documents\MATLAB\scripts"
python preprocesspython.py sub-umich0020
python car_reref.py sub-umich0020
python band_pass.py sub-umich0020
python plv_analysis.py sub-umich0020
```

## GitHub
- Repo: https://github.com/abtinunmc/HFO-GLISKE

## Next Steps
- Re-run pipeline (steps 2-4) for sub-umich0023 and sub-umich0028 (dtype fix now applied)
- Implement surrogate-based statistical testing (baseline comparison)
- Weighted PLV averaging across runs (by HFO count)
- Process remaining ~107 SEEG patients
- Consider adding ECoG support (currently SEEG only)
- Clinical correlation with seizure outcomes

## Data Availability
- **Total in database:** 119 subjects (sub-umich0018 to sub-umich0136)
- **Processed:** 9 subjects
- **Remaining:** ~107 (excluding ECoG and missing data)
