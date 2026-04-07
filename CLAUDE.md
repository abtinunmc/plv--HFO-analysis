# HFO-GLISKE Project

## Overview
HFO (High-Frequency Oscillation) analysis pipeline for iEEG/SEEG data. Identifies and validates HFOs, applies preprocessing, and computes phase-locking values (PLV) for connectivity analysis.

## Pipeline Steps

| Step | Script | Input | Output | Status |
|------|--------|-------|--------|--------|
| 1. HFO Validation | `python scripts/preprocesspython.py` | H5 (qHFO), channels.tsv | `step3_validated_qHFO_run-XX.mat` | Done |
| 2. CAR Re-referencing | `python scripts/car_reref.py` | Raw .dat/.lay, step3 .mat | `car_output/*.dat, *.lay` | Done |
| 3. Bandpass Filter | `python scripts/band pass.py` | CAR .dat/.lay | `bandpass_output/*_CAR_bp.dat` | Done |
| 4. PLV Analysis | `python scripts/plvhfo1.py` | Bandpass output, step3 .mat | TBD | Next |

## Data Paths

- **Raw data:** `U:\shared\database\ieeg-UM\rawdata\sub-umich0018\ses-ieeg01\ieeg\`
- **H5 files:** `U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\`
- **Step3 output:** `C:\Users\aakhtari\Documents\MATLAB\`
- **CAR output:** `C:\Users\aakhtari\Documents\MATLAB\car_output\`
- **Bandpass output:** `C:\Users\aakhtari\Documents\MATLAB\bandpass_output\`
- **Plots:** `C:\Users\aakhtari\Documents\MATLAB\plots\`

## Current Subject
- Subject: `sub-umich0018`
- Session: `ses-ieeg01`
- Runs: `run-01` through `run-05`
- Sampling rate: 4096 Hz
- Channels: 62 (32 good SEEG)

## Key Parameters
- Bandpass filter: 80-500 Hz (HFO band)
- Filter type: Elliptic, order 10, 0.5dB passband ripple, 65dB stopband
- Max valid HFOs per run: 500 (random subset)

## File Formats
- `.dat`: Raw binary EEG (int16, interleaved channels)
- `.lay`: Persyst header (INI-style, contains fs, calibration, channel names)
- `.mat`: MATLAB format (scipy.io compatible)
- `.h5`: HDF5 format for HFO events and valid times

## Conventions
- All scripts in `python scripts/` folder
- Plots saved to `plots/` folder
- Session notes in `session_chat_and_changes.md`
- ASCII only in print statements (no Unicode symbols)

## GitHub
- Private repo (with data): https://github.com/abtinunmc/HFO-GLISKE
- Public repo (code only): https://github.com/abtinunmc/HFO-GLISKE-code

## How to Run
```powershell
cd "C:\Users\aakhtari\Documents\MATLAB\python scripts"
python preprocesspython.py      # Step 1: HFO validation
python car_reref.py             # Step 2: CAR
python "band pass.py"           # Step 3: Bandpass filter
python plvhfo1.py               # Step 4: PLV (next)
```
