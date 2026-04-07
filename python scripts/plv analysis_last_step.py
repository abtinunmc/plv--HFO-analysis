"""
PLV (Phase Locking Value) Analysis - Final step of HFO pipeline.
Computes phase synchronization between channel pairs during HFO events.

Input: Bandpass filtered data (bandpass_output/) + validated HFOs (step3 .mat)
Output: PLV matrices per run (plv_output/) + connectivity plots (plots/)
"""
# ── Step 7a: Setup paths, params, load validated HFOs
#
# This step:
# 1. Sets up all file paths and parameters
# 2. Loads the step3 .mat file containing valid HFO events and good channel list
# 3. Verifies all required files exist before proceeding
import os
import numpy as np
from scipy.io import loadmat

#PARAMETERS

SUBJECT = "sub-umich0018"
SESSION = "ses-ieeg01"
RUNS = ["run-01", "run-02", "run-03", "run-04", "run-05"]

# Input directories
BANDPASS_DIR = r"C:\Users\aakhtari\Documents\MATLAB\bandpass_output"
STEP3_DIR = r"C:\Users\aakhtari\Documents\MATLAB"

# Output directories
PLV_OUTPUT_DIR = r"C:\Users\aakhtari\Documents\MATLAB\plv_output"
PLOT_DIR = r"C:\Users\aakhtari\Documents\MATLAB\plots"

# File suffixes
BP_DAT_SUFFIX = "_ieeg_CAR_bp.dat"
BP_LAY_SUFFIX = "_ieeg_CAR_bp.lay"

# Sampling rate (should match bandpass output)
FS = 4096

# === VERIFY DIRECTORIES ===

print("Step 7a: Setup and load validated HFOs")
print("=" * 50)

# Check input directories exist
assert os.path.isdir(BANDPASS_DIR), f"Bandpass directory not found: {BANDPASS_DIR}"
assert os.path.isdir(STEP3_DIR), f"Step3 directory not found: {STEP3_DIR}"

# Create output directories
os.makedirs(PLV_OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)

print(f"  Bandpass input: {BANDPASS_DIR}")
print(f"  Step3 input: {STEP3_DIR}")
print(f"  PLV output: {PLV_OUTPUT_DIR}")
print(f"  Plots output: {PLOT_DIR}")

# === VERIFY INPUT FILES ===

print(f"\nVerifying input files for {len(RUNS)} runs...")

for run in RUNS:
    # Check bandpass files
    bp_dat = os.path.join(BANDPASS_DIR, f"{SUBJECT}_{SESSION}_task-all_{run}{BP_DAT_SUFFIX}")
    bp_lay = os.path.join(BANDPASS_DIR, f"{SUBJECT}_{SESSION}_task-all_{run}{BP_LAY_SUFFIX}")

    assert os.path.isfile(bp_dat), f"Missing bandpass .dat: {bp_dat}"
    assert os.path.isfile(bp_lay), f"Missing bandpass .lay: {bp_lay}"

    # Check step3 .mat
    step3_mat = os.path.join(STEP3_DIR, f"step3_validated_qHFO_{run}.mat")
    assert os.path.isfile(step3_mat), f"Missing step3 .mat: {step3_mat}"

    print(f"  {run}: all files OK")

# === LOAD STEP3 DATA FOR ALL RUNS ===

print(f"\nLoading step3 validated HFO data...")

RUN_DATA = {}

for run in RUNS:
    step3_mat = os.path.join(STEP3_DIR, f"step3_validated_qHFO_{run}.mat")
    mat = loadmat(step3_mat, squeeze_me=True)

    # Extract valid HFO info
    valid_start = np.atleast_1d(mat['validStartTime']).astype(float)
    valid_stop = np.atleast_1d(mat['validStopTime']).astype(float)
    valid_chan = np.atleast_1d(mat['validChanIdx']).astype(int)

    # Extract good SEEG channel info
    good_idx = np.atleast_1d(mat['goodSEEG_idx']).astype(int)
    good_names = np.atleast_1d(mat['goodSEEG_names'])
    good_names = [str(n) for n in good_names]  # convert to list of strings

    n_valid = len(valid_start)
    n_good_ch = len(good_idx)

    RUN_DATA[run] = {
        'valid_start': valid_start,
        'valid_stop': valid_stop,
        'valid_chan': valid_chan,
        'good_idx': good_idx,
        'good_names': good_names,
        'n_valid': n_valid,
        'n_good_ch': n_good_ch,
    }

    # Calculate total duration of valid HFOs
    total_dur_ms = (valid_stop - valid_start).sum() * 1000
    avg_dur_ms = (valid_stop - valid_start).mean() * 1000 if n_valid > 0 else 0

    print(f"  {run}: {n_valid} valid HFOs, {n_good_ch} good channels")
    print(f"         avg HFO duration: {avg_dur_ms:.1f} ms, total: {total_dur_ms:.1f} ms")

# === SUMMARY ===

total_hfos = sum(d['n_valid'] for d in RUN_DATA.values())
n_channels = RUN_DATA[RUNS[0]]['n_good_ch']  # same for all runs
channel_names = RUN_DATA[RUNS[0]]['good_names']

print(f"\n" + "=" * 50)
print(f"Step 7a OK: Setup complete")
print(f"  Total valid HFOs across all runs: {total_hfos}")
print(f"  Good SEEG channels: {n_channels}")
print(f"  Channel names: {', '.join(channel_names[:5])}... (first 5)")
print(f"  PLV matrix size: {n_channels} x {n_channels} = {n_channels**2} pairs")


# Step 7b: Load bandpass data and extract HFO segments ──

# This step:
# 1. Parses .lay header to get data format info (dtype, calibration, n_channels)
# 2. For each valid HFO, reads the corresponding segment from bandpass .dat
# 3. Extracts only the good SEEG channels (not all 62)
# 4. Stores segments in a list for PLV computation in next step
#
# HFO segment: a short time window (typically 20-200 ms) of filtered EEG
# across all good channels during one HFO event

print(f"\n" + "=" * 50)
print("Step 7b: Load bandpass data and extract HFO segments")
print("=" * 50)


#Parse Persyst .lay file to get data format info.
def parse_lay_header(lay_path):
    header = {}
    with open(lay_path, 'r', encoding='utf-8', errors='replace') as f:
        current_section = None
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue
            if '=' in line and current_section == 'FileInfo':
                key, value = line.split('=', 1)
                key, value = key.strip(), value.strip()
                if key == 'SamplingRate':
                    header['fs'] = float(value)
                elif key == 'WaveformCount':
                    header['n_channels'] = int(value)
                elif key == 'DataType':
                    header['dtype_code'] = int(value)
                elif key == 'Calibration':
                    header['calibration'] = float(value)

    # Map dtype code to numpy dtype
    dtype_map = {0: np.int16, 1: np.int32, 7: np.float64}
    header['dtype'] = dtype_map.get(header.get('dtype_code', 0), np.int16)

    return header


def extract_hfo_segments(run, run_data, bandpass_dir, subject, session, bp_dat_suffix, bp_lay_suffix):
    """
    Extract all HFO segments for one run.

    Returns:
        segments: list of arrays, each (n_samples, n_good_channels)
        durations: list of segment durations in seconds
    """
    # Build file paths
    bp_dat = os.path.join(bandpass_dir, f"{subject}_{session}_task-all_{run}{bp_dat_suffix}")
    bp_lay = os.path.join(bandpass_dir, f"{subject}_{session}_task-all_{run}{bp_lay_suffix}")

    # Parse header
    header = parse_lay_header(bp_lay)
    fs = header['fs']
    n_ch_total = header['n_channels']
    dtype = header['dtype']
    calib = header['calibration']
    bytes_per_sample = np.dtype(dtype).itemsize

    # Get HFO times and good channel indices
    valid_start = run_data['valid_start']
    valid_stop = run_data['valid_stop']
    good_idx = run_data['good_idx'] - 1  # convert 1-based to 0-based

    segments = []
    durations = []

    with open(bp_dat, 'rb') as f:
        for t_start, t_stop in zip(valid_start, valid_stop):
            # Convert time to sample indices
            samp_start = int(t_start * fs)
            samp_stop = int(t_stop * fs)
            n_samp = samp_stop - samp_start

            if n_samp <= 0:
                continue

            # Seek to start position and read segment
            byte_offset = samp_start * n_ch_total * bytes_per_sample
            f.seek(byte_offset)
            raw = np.fromfile(f, dtype=dtype, count=n_samp * n_ch_total)

            # Check if we got enough data
            if len(raw) < n_samp * n_ch_total:
                # Truncate if near end of file
                n_samp = len(raw) // n_ch_total
                if n_samp == 0:
                    continue
                raw = raw[:n_samp * n_ch_total]

            # Reshape to (samples, channels) and extract good channels only
            data = raw.reshape(n_samp, n_ch_total).astype(np.float64)
            data *= calib  # convert to microvolts
            data = data[:, good_idx]  # keep only good channels

            segments.append(data)
            durations.append(n_samp / fs)

    return segments, durations, header


# Extract segments for all runs
ALL_SEGMENTS = {}
ALL_DURATIONS = {}

for run in RUNS:
    print(f"\n  Processing {run}...")

    segments, durations, header = extract_hfo_segments(
        run, RUN_DATA[run], BANDPASS_DIR, SUBJECT, SESSION, BP_DAT_SUFFIX, BP_LAY_SUFFIX
    )

    ALL_SEGMENTS[run] = segments
    ALL_DURATIONS[run] = durations

    n_seg = len(segments)
    if n_seg > 0:
        avg_dur_ms = np.mean(durations) * 1000
        total_dur_ms = np.sum(durations) * 1000
        avg_samples = np.mean([s.shape[0] for s in segments])
        print(f"    Extracted {n_seg} segments")
        print(f"    Avg duration: {avg_dur_ms:.1f} ms ({avg_samples:.0f} samples)")
        print(f"    Total duration: {total_dur_ms:.1f} ms")
        print(f"    Segment shape: ({segments[0].shape[0]}, {segments[0].shape[1]}) = (samples, channels)")
    else:
        print(f"    No segments extracted!")

# Summary
total_segments = sum(len(s) for s in ALL_SEGMENTS.values())
all_durations_flat = [d for durs in ALL_DURATIONS.values() for d in durs]

print(f"\n" + "=" * 50)
print(f"Step 7b OK: HFO segments extracted")
print(f"  Total segments: {total_segments}")
print(f"  Avg duration: {np.mean(all_durations_flat)*1000:.1f} ms")
print(f"  Min duration: {np.min(all_durations_flat)*1000:.1f} ms")
print(f"  Max duration: {np.max(all_durations_flat)*1000:.1f} ms")

#end of step 7b
################################################################################################
#Step 7c: Compute Hilbert phase for each HFO segment

# REQUIREMENT: Signal must be narrowband (filtered) - our 80-500 Hz bandpass satisfies this
# OUTPUT: ALL_PHASES[run] = list of phase arrays, each (n_samples, n_channels)

print(f"\n" + "=" * 50)
print("Step 7c: Compute Hilbert phase")
print("=" * 50)

from scipy.signal import hilbert

ALL_PHASES = {}

for run in RUNS:
    segments = ALL_SEGMENTS[run]
    n_seg = len(segments)

    if n_seg == 0:
        ALL_PHASES[run] = []
        print(f"  {run}: no segments, skipping")
        continue

    phases = []
    for seg in segments:
        # seg shape: (n_samples, n_channels)
        # Apply Hilbert transform to each channel
        analytic = hilbert(seg, axis=0)  # complex analytic signal
        phase = np.angle(analytic)        # instantaneous phase in radians (-pi to pi)
        phases.append(phase)

    ALL_PHASES[run] = phases

    # Quick stats on first segment for verification
    first_phase = phases[0]
    print(f"  {run}: {n_seg} segments processed")
    print(f"    Phase range: [{first_phase.min():.2f}, {first_phase.max():.2f}] rad")
    print(f"    Phase shape: {first_phase.shape} (samples, channels)")

print(f"\n" + "=" * 50)
print(f"Step 7c OK: Hilbert phase computed for all segments")
#end of step 7c##################################################################################

# ── Step 7d: Compute PLV for all channel pairs per HFO ──
#
# PLV FORMULA:
#   PLV = |mean(exp(i * (phase1 - phase2)))|
#
# For each HFO segment:
#   - Compute phase difference between every pair of channels
#   - Average the unit vectors (exp(i*diff)) across time points
#   - PLV = magnitude of this average (0 = no sync, 1 = perfect sync)
#
# OUTPUT:
#   - ALL_PLV[run] = list of PLV matrices, each (n_channels, n_channels)
#   - Diagonal is always 1 (channel with itself)

print(f"\n" + "=" * 50)
print("Step 7d: Compute PLV for all channel pairs")
print("=" * 50)


def compute_plv_matrix(phase_array):
    """
    Compute PLV matrix for one HFO segment.

    Args:
        phase_array: (n_samples, n_channels) array of instantaneous phases

    Returns:
        plv_matrix: (n_channels, n_channels) symmetric PLV matrix
    """
    _, n_ch = phase_array.shape
    plv_matrix = np.zeros((n_ch, n_ch))

    for i in range(n_ch):
        for j in range(i, n_ch):  # only upper triangle (symmetric)
            if i == j:
                plv_matrix[i, j] = 1.0  # PLV with itself is always 1
            else:
                # Phase difference between channels i and j
                phase_diff = phase_array[:, i] - phase_array[:, j]
                # PLV = magnitude of mean unit vector
                plv = np.abs(np.mean(np.exp(1j * phase_diff)))
                plv_matrix[i, j] = plv
                plv_matrix[j, i] = plv  # symmetric

    return plv_matrix


ALL_PLV = {}

for run in RUNS:
    phases = ALL_PHASES[run]
    n_seg = len(phases)

    if n_seg == 0:
        ALL_PLV[run] = []
        print(f"  {run}: no segments, skipping")
        continue

    plv_matrices = []
    for phase_array in phases:
        plv_mat = compute_plv_matrix(phase_array)
        plv_matrices.append(plv_mat)

    ALL_PLV[run] = plv_matrices

    # Stats
    all_plv_values = np.array([m[np.triu_indices(m.shape[0], k=1)] for m in plv_matrices]).flatten()
    print(f"  {run}: {n_seg} PLV matrices computed")
    print(f"    PLV range: [{all_plv_values.min():.3f}, {all_plv_values.max():.3f}]")
    print(f"    PLV mean: {all_plv_values.mean():.3f}, std: {all_plv_values.std():.3f}")

# Summary
total_matrices = sum(len(p) for p in ALL_PLV.values())
print(f"\n" + "=" * 50)
print(f"Step 7d OK: PLV matrices computed")
print(f"  Total PLV matrices: {total_matrices}")
print(f"  Matrix size: {n_channels} x {n_channels}")

# === VALIDATION PLOT: Show sample PLV matrices ===

print(f"\nGenerating Step 7d validation plot...")

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Find first run with PLV matrices
viz_run = None
for r in RUNS:
    if len(ALL_PLV[r]) > 0:
        viz_run = r
        break

if viz_run is None:
    print("  No PLV matrices found, skipping validation plot")
else:
    # Get first 4 PLV matrices (or fewer if not enough)
    plv_list = ALL_PLV[viz_run]
    n_show = min(4, len(plv_list))

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for i in range(4):
        ax = axes[i]
        if i < n_show:
            plv_mat = plv_list[i]
            im = ax.imshow(plv_mat, cmap='hot', vmin=0, vmax=1, aspect='equal')
            ax.set_title(f'HFO #{i+1} PLV Matrix', fontweight='bold')
            ax.set_xlabel('Channel')
            ax.set_ylabel('Channel')

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('PLV')

            # Show channel names on axes (subsample if too many)
            n_ch = plv_mat.shape[0]
            if n_ch <= 16:
                ax.set_xticks(range(n_ch))
                ax.set_yticks(range(n_ch))
                ax.set_xticklabels(channel_names[:n_ch], rotation=90, fontsize=6)
                ax.set_yticklabels(channel_names[:n_ch], fontsize=6)
            else:
                # Show every 4th channel
                tick_idx = list(range(0, n_ch, 4))
                ax.set_xticks(tick_idx)
                ax.set_yticks(tick_idx)
                ax.set_xticklabels([channel_names[j] for j in tick_idx], rotation=90, fontsize=6)
                ax.set_yticklabels([channel_names[j] for j in tick_idx], fontsize=6)
        else:
            ax.axis('off')

    fig.suptitle(f'Step 7d: PLV Matrices Validation - {SUBJECT} {viz_run}\n(0=no sync, 1=perfect sync)',
                 fontweight='bold', fontsize=14)
    fig.tight_layout()

    # Save plot
    plot_path = os.path.join(PLOT_DIR, "step7d_plv_matrices_validation.png")
    fig.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"  Plot saved: {plot_path}")

    # Open the plot
    try:
        os.startfile(plot_path)
    except Exception:
        import subprocess
        subprocess.run(['start', '', plot_path], shell=True)

print(f"\nReady for Step 7e: Average PLV across HFOs")

