# HFO-PLV Analysis Pipeline

Analysis of phase-locking values (PLV) during high-frequency oscillations (HFOs) in stereo-EEG (SEEG) recordings from epilepsy patients.

## Folder Structure

```
MATLAB/
├── scripts/              # Active Python pipeline scripts
│   ├── preprocesspython.py    # Step 1: HFO validation
│   ├── car_reref.py           # Step 2: CAR re-referencing
│   ├── band_pass.py           # Step 3: Bandpass filtering (80-500 Hz)
│   ├── plv_analysis.py        # Step 4: PLV computation
│   └── generate_preprint_pdf.py
│
├── subjects/             # Per-patient output data
│   └── sub-umichXXXX/
│       ├── step1_hfo_validation/   # Validated HFO .mat files
│       ├── step2_car/              # CAR re-referenced .dat/.lay
│       ├── step3_bandpass/         # Bandpass filtered data
│       ├── step4_plv/              # PLV matrices and CSV outputs
│       └── plots/                  # All plots for this patient
│
├── docs/                 # Documentation
│   ├── README.md               # This file
│   ├── CLAUDE.md               # Project context for Claude
│   ├── preprint_draft.md       # Preprint manuscript
│   └── preprint_HFO_PLV_analysis.pdf
│
├── archive/              # Old scripts and debug files
└── .claude/              # Claude Code memory and session data
```

## Pipeline Steps

| Step | Script | Description |
|------|--------|-------------|
| 1 | `preprocesspython.py` | Validate HFOs against clean signal windows |
| 2 | `car_reref.py` | Common Average Reference using good SEEG channels |
| 3 | `band_pass.py` | 80-500 Hz elliptic bandpass filter |
| 4 | `plv_analysis.py` | Hilbert phase extraction and PLV computation |

## Usage

```bash
cd "C:\Users\aakhtari\Documents\MATLAB\scripts"
python preprocesspython.py sub-umich0020    # Step 1
python car_reref.py sub-umich0020           # Step 2
python band_pass.py sub-umich0020           # Step 3
python plv_analysis.py sub-umich0020        # Step 4
```

## Key Parameters

- Sampling rate: 4096 Hz
- HFO band: 80-500 Hz
- Filter: Elliptic, order 10
- Max HFOs per run: 500 (random subset)
- Hilbert edge trim: 15 samples (~3.7 ms)

## Data Sources

- Raw data: `U:\shared\database\ieeg-UM\rawdata\`
- HFO detections: `U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\`
