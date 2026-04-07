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

from scipy.signal import hilbert, step

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

#end of step 7d###########################################################################################


# ── Step 7e: Average PLV across HFOs → connectivity matrix ──
#
# This step computes the mean PLV matrix across all HFO events.
# The result is a single (n_channels x n_channels) connectivity matrix
# showing average phase synchronization between each channel pair.
#
# We compute:
#   1. Per-run average PLV matrix
#   2. Global average PLV matrix (across all runs)

print(f"\n" + "=" * 50)
print("Step 7e: Average PLV across HFOs")
print("=" * 50)

# Per-run average PLV
AVG_PLV_PER_RUN = {}

for run in RUNS:
    plv_list = ALL_PLV[run]
    n_mat = len(plv_list)

    if n_mat == 0:
        print(f"  {run}: no PLV matrices, skipping")
        continue

    # Stack all matrices and take mean
    plv_stack = np.stack(plv_list, axis=0)  # (n_hfos, n_channels, n_channels)
    avg_plv = np.mean(plv_stack, axis=0)     # (n_channels, n_channels)

    AVG_PLV_PER_RUN[run] = avg_plv

    # Stats on upper triangle (excluding diagonal)
    upper_tri = avg_plv[np.triu_indices(avg_plv.shape[0], k=1)]
    print(f"  {run}: averaged {n_mat} matrices")
    print(f"    Mean PLV: {upper_tri.mean():.3f}, Std: {upper_tri.std():.3f}")
    print(f"    Min: {upper_tri.min():.3f}, Max: {upper_tri.max():.3f}")

# Global average (across all runs)
all_avg_matrices = list(AVG_PLV_PER_RUN.values())
if len(all_avg_matrices) > 0:
    GLOBAL_AVG_PLV = np.mean(np.stack(all_avg_matrices, axis=0), axis=0)

    upper_tri_global = GLOBAL_AVG_PLV[np.triu_indices(GLOBAL_AVG_PLV.shape[0], k=1)]
    print(f"\n  Global average (all runs combined):")
    print(f"    Mean PLV: {upper_tri_global.mean():.3f}, Std: {upper_tri_global.std():.3f}")
    print(f"    Min: {upper_tri_global.min():.3f}, Max: {upper_tri_global.max():.3f}")
else:
    GLOBAL_AVG_PLV = None
    print("  No PLV matrices to average!")

print(f"\n" + "=" * 50)
print(f"Step 7e OK: Average PLV matrices computed")

#end of step 7e############################################################################################


# ── Step 7f: Save results to .mat and .csv files ──
#
# Saves:
#   1. Per-run PLV data (.mat) - all individual HFO PLV matrices + average
#   2. Global average PLV (.mat) - single connectivity matrix across all runs
#   3. CSV exports - for easy viewing in Excel/other tools

print(f"\n" + "=" * 50)
print("Step 7f: Save results to files")
print("=" * 50)

from scipy.io import savemat
import csv

os.makedirs(PLV_OUTPUT_DIR, exist_ok=True)

# 1. Save per-run PLV data
for run in RUNS:
    if run not in AVG_PLV_PER_RUN:
        print(f"  {run}: no data, skipping")
        continue

    plv_list = ALL_PLV[run]
    avg_plv = AVG_PLV_PER_RUN[run]

    # Stack individual PLV matrices into 3D array
    plv_3d = np.stack(plv_list, axis=0)  # (n_hfos, n_channels, n_channels)

    # Save .mat file
    mat_path = os.path.join(PLV_OUTPUT_DIR, f"plv_{run}.mat")
    savemat(mat_path, {
        'plv_per_hfo': plv_3d,           # 3D: (n_hfos, n_ch, n_ch)
        'plv_average': avg_plv,           # 2D: (n_ch, n_ch)
        'channel_names': np.array(channel_names, dtype=object),
        'n_hfos': len(plv_list),
        'n_channels': n_channels,
        'subject': SUBJECT,
        'session': SESSION,
        'run': run,
    }, do_compression=True)

    # Save average PLV as CSV (easier to view)
    csv_path = os.path.join(PLV_OUTPUT_DIR, f"plv_avg_{run}.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header row with channel names
        writer.writerow([''] + channel_names)
        # Data rows
        for i, row in enumerate(avg_plv):
            writer.writerow([channel_names[i]] + [f'{v:.4f}' for v in row])

    print(f"  {run}: saved {mat_path}")
    print(f"         saved {csv_path}")

# 2. Save global average PLV
if GLOBAL_AVG_PLV is not None:
    # .mat file
    global_mat_path = os.path.join(PLV_OUTPUT_DIR, "plv_global_average.mat")
    savemat(global_mat_path, {
        'plv_global_average': GLOBAL_AVG_PLV,
        'channel_names': np.array(channel_names, dtype=object),
        'n_channels': n_channels,
        'n_runs': len(AVG_PLV_PER_RUN),
        'runs_included': list(AVG_PLV_PER_RUN.keys()),
        'subject': SUBJECT,
        'session': SESSION,
    }, do_compression=True)

    # CSV file
    global_csv_path = os.path.join(PLV_OUTPUT_DIR, "plv_global_average.csv")
    with open(global_csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([''] + channel_names)
        for i, row in enumerate(GLOBAL_AVG_PLV):
            writer.writerow([channel_names[i]] + [f'{v:.4f}' for v in row])

    print(f"\n  Global average saved:")
    print(f"    {global_mat_path}")
    print(f"    {global_csv_path}")

print(f"\n" + "=" * 50)
print(f"Step 7f OK: Results saved to {PLV_OUTPUT_DIR}")

#end of step 7f############################################################################################


# ── Step 7g: Final connectivity visualization ──
#
# Creates a comprehensive figure showing:
#   1. Global average PLV heatmap with channel labels
#   2. Top N strongest connections (bar chart)
#   3. PLV distribution histogram
#   4. Per-run comparison

print(f"\n" + "=" * 50)
print("Step 7g: Final connectivity visualization")
print("=" * 50)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if GLOBAL_AVG_PLV is None:
    print("  No PLV data available, skipping final plot")
else:
    print("  Generating final connectivity figure...")

    fig = plt.figure(figsize=(16, 12))

    # Create grid layout
    gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

    # 1. Global average PLV heatmap (large, left side)
    ax1 = fig.add_subplot(gs[:, 0])
    im1 = ax1.imshow(GLOBAL_AVG_PLV, cmap='hot', vmin=0, vmax=1, aspect='equal')
    ax1.set_title('Global Average PLV\nConnectivity Matrix', fontweight='bold', fontsize=12)
    ax1.set_xlabel('Channel')
    ax1.set_ylabel('Channel')
    cbar1 = plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    cbar1.set_label('PLV (0=no sync, 1=perfect)')

    # Channel labels
    n_ch = GLOBAL_AVG_PLV.shape[0]
    if n_ch <= 20:
        ax1.set_xticks(range(n_ch))
        ax1.set_yticks(range(n_ch))
        ax1.set_xticklabels(channel_names[:n_ch], rotation=90, fontsize=6)
        ax1.set_yticklabels(channel_names[:n_ch], fontsize=6)
    else:
        tick_idx = list(range(0, n_ch, 4))
        ax1.set_xticks(tick_idx)
        ax1.set_yticks(tick_idx)
        ax1.set_xticklabels([channel_names[j] for j in tick_idx], rotation=90, fontsize=7)
        ax1.set_yticklabels([channel_names[j] for j in tick_idx], fontsize=7)

    # 2. Top 15 strongest connections (bar chart)
    ax2 = fig.add_subplot(gs[0, 1:])

    # Get upper triangle indices and values
    triu_i, triu_j = np.triu_indices(n_ch, k=1)
    plv_values = GLOBAL_AVG_PLV[triu_i, triu_j]

    # Sort and get top 15
    n_top = min(15, len(plv_values))
    top_idx = np.argsort(plv_values)[-n_top:][::-1]

    top_labels = [f"{channel_names[triu_i[k]]}-{channel_names[triu_j[k]]}" for k in top_idx]
    top_values = plv_values[top_idx]

    bars = ax2.barh(range(n_top), top_values, color='steelblue', edgecolor='black')
    ax2.set_yticks(range(n_top))
    ax2.set_yticklabels(top_labels, fontsize=8)
    ax2.set_xlabel('PLV')
    ax2.set_xlim([0, 1])
    ax2.set_title(f'Top {n_top} Strongest Connections', fontweight='bold')
    ax2.invert_yaxis()

    # Add value labels on bars
    for bar, val in zip(bars, top_values):
        ax2.text(val + 0.02, bar.get_y() + bar.get_height()/2, f'{val:.3f}',
                 va='center', fontsize=7)

    # 3. PLV distribution histogram
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.hist(plv_values, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
    ax3.axvline(plv_values.mean(), color='red', linestyle='--', linewidth=2,
                label=f'Mean: {plv_values.mean():.3f}')
    ax3.axvline(np.median(plv_values), color='orange', linestyle=':', linewidth=2,
                label=f'Median: {np.median(plv_values):.3f}')
    ax3.set_xlabel('PLV')
    ax3.set_ylabel('Count (channel pairs)')
    ax3.set_title('PLV Distribution', fontweight='bold')
    ax3.legend(fontsize=8)
    ax3.set_xlim([0, 1])

    # 4. Per-run mean PLV comparison
    ax4 = fig.add_subplot(gs[1, 2])

    run_names = list(AVG_PLV_PER_RUN.keys())
    run_means = []
    run_stds = []
    for r in run_names:
        upper = AVG_PLV_PER_RUN[r][np.triu_indices(n_ch, k=1)]
        run_means.append(upper.mean())
        run_stds.append(upper.std())

    x_pos = range(len(run_names))
    ax4.bar(x_pos, run_means, yerr=run_stds, color='lightcoral', edgecolor='black',
            capsize=5, alpha=0.8)
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(run_names, rotation=45, ha='right', fontsize=9)
    ax4.set_ylabel('Mean PLV')
    ax4.set_title('Mean PLV per Run', fontweight='bold')
    ax4.set_ylim([0, 1])

    # Add global mean line
    ax4.axhline(plv_values.mean(), color='blue', linestyle='--', alpha=0.7,
                label=f'Global: {plv_values.mean():.3f}')
    ax4.legend(fontsize=8)

    # Main title
    fig.suptitle(f'PLV Connectivity Analysis - {SUBJECT}_{SESSION}\n'
                 f'{total_matrices} HFOs, {n_ch} channels, {len(run_names)} runs',
                 fontweight='bold', fontsize=14)

    # Save plot
    plot_path = os.path.join(PLOT_DIR, "step7g_final_plv_connectivity.png")
    fig.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"  Plot saved: {plot_path}")

    # Open the plot
    try:
        os.startfile(plot_path)
    except Exception:
        import subprocess
        subprocess.run(['start', '', plot_path], shell=True)

print(f"\n" + "=" * 50)
print("PLV ANALYSIS COMPLETE")
print("=" * 50)
print(f"\nOutput files in: {PLV_OUTPUT_DIR}")
print(f"Plots in: {PLOT_DIR}")
print(f"\nSummary:")
print(f"  Subject: {SUBJECT}")
print(f"  Session: {SESSION}")
print(f"  Runs processed: {len(AVG_PLV_PER_RUN)}")
print(f"  Total HFOs analyzed: {total_matrices}")
print(f"  Channels: {n_channels}")
if GLOBAL_AVG_PLV is not None:
    upper = GLOBAL_AVG_PLV[np.triu_indices(n_ch, k=1)]
    print(f"  Global mean PLV: {upper.mean():.3f} +/- {upper.std():.3f}")
