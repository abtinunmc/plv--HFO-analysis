"""
Bandpass 80-500 Hz on CAR data. Reads from car_output (.lay + .dat).

Usage: python "band pass.py" [subject]
  e.g. python "band pass.py" sub-umich0019
"""

import os
import sys
import glob

# 80-500 Hz HFO band (we'll use zero-phase later)
LOW_HZ = 80
HIGH_HZ = 500
# 10 = steep rolloff for clean HFO band, elliptic filter is stable at this order
FILTER_ORDER = 10

# Default subject (can be overridden via command line)
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else "sub-umich0018"
SESSION = "ses-ieeg01"

# Base paths
BASE_OUT_DIR = r"C:\Users\aakhtari\Documents\MATLAB"

# Per-subject directories (new organized structure)
SUBJECT_DIR = os.path.join(BASE_OUT_DIR, "subjects", SUBJECT)
CAR_INPUT_DIR = os.path.join(SUBJECT_DIR, "step2_car")
PLOTS_DIR = os.path.join(SUBJECT_DIR, "plots")

CAR_LAY_SUFFIX = "_ieeg_CAR.lay"
CAR_DAT_SUFFIX = "_ieeg_CAR.dat"

# Auto-detect runs from CAR .lay files
def detect_runs():
    pattern = os.path.join(CAR_INPUT_DIR, f"{SUBJECT}_{SESSION}_task-all_run-*{CAR_LAY_SUFFIX}")
    files = glob.glob(pattern)
    runs = sorted(set(os.path.basename(f).split('_')[3] for f in files))
    return runs if runs else ["run-01", "run-02", "run-03", "run-04", "run-05"]

RUNS = detect_runs()

# make sure we don't run with bad paths or missing files, debug easily with asserts
assert os.path.exists(CAR_INPUT_DIR), (
    f"CAR input directory does not exist: {CAR_INPUT_DIR}"
)
assert os.path.isdir(CAR_INPUT_DIR), (
    f"CAR input path is not a directory: {CAR_INPUT_DIR}"
)

assert LOW_HZ > 0, f"LOW_HZ must be positive, got {LOW_HZ}"
assert HIGH_HZ > LOW_HZ, (
    f"HIGH_HZ ({HIGH_HZ}) must be greater than LOW_HZ ({LOW_HZ})"
)
assert FILTER_ORDER >= 1, f"FILTER_ORDER must be >= 1, got {FILTER_ORDER}"

# need at least one .lay in there
lay_files = [
    f for f in os.listdir(CAR_INPUT_DIR)
    if f.endswith(CAR_LAY_SUFFIX)
]
# fail fast if no .lay files found
assert len(lay_files) > 0, (
    f"No CAR .lay files found in {CAR_INPUT_DIR} "
    f"(expected filenames ending with {CAR_LAY_SUFFIX})"
)

# every run should have both .lay and .dat
for run in RUNS:
    lay_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_LAY_SUFFIX}"
    lay_path = os.path.join(CAR_INPUT_DIR, lay_name)
    dat_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_DAT_SUFFIX}"
    dat_path = os.path.join(CAR_INPUT_DIR, dat_name)
    assert os.path.isfile(lay_path), (
        f"Missing CAR .lay for {run}: {lay_path}"
    )
    assert os.path.isfile(dat_path), (
        f"Missing CAR .dat for {run}: {dat_path}"
    )

print("Step 1 OK: paths and params look good, asserts passed.")
print(f"  CAR input dir: {CAR_INPUT_DIR}")
print(f"  Filter: {LOW_HZ}-{HIGH_HZ} Hz, order {FILTER_ORDER}")
print(f"  CAR .lay files found: {len(lay_files)}")

# ── Step 2a: Read CAR .lay file and parse header ──

def parse_lay_header(lay_path: str) -> dict:
    """
    Parse a Persyst .lay header file and extract key fields.
    
    Returns a dict with:
        - SamplingRate: float
        - WaveformCount: int (number of channels)
        - DataType: int (typically 7 for int16)
        - Calibration: float
        - ChannelNames: list of str
        - other fields as found
    """
    header = {}
    channel_map = []  # (index, name) so we can sort by index

    with open(lay_path, 'r', encoding='utf-8', errors='replace') as f:
        current_section = None

        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue

            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                if current_section == 'FileInfo':
                    if key == 'SamplingRate':
                        header['SamplingRate'] = float(value)
                    elif key == 'WaveformCount':
                        header['WaveformCount'] = int(value)
                    elif key == 'DataType':
                        header['DataType'] = int(value)
                    elif key == 'Calibration':
                        header['Calibration'] = float(value)
                    else:
                        header[key] = value
                elif current_section == 'ChannelMap':
                    # .lay format is Name=Index (e.g. AL1-Ref=1)
                    try:
                        ch_index = int(value)
                        channel_map.append((ch_index, key))
                    except ValueError:
                        pass
                elif current_section == 'Patient':
                    header[f'Patient_{key}'] = value
                else:
                    header[key] = value

    channel_names = [name for _, name in sorted(channel_map, key=lambda x: x[0])]
    header['ChannelNames'] = channel_names
    return header


# Parse .lay for each run and store headers
run_headers = {}

for run in RUNS:
    lay_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_LAY_SUFFIX}"
    lay_path = os.path.join(CAR_INPUT_DIR, lay_name)
    
    print(f"\nParsing .lay for {run}: {lay_name}")
    header = parse_lay_header(lay_path)
    run_headers[run] = header
    
    # Print key info
    fs = header.get('SamplingRate', 'N/A')
    n_ch = header.get('WaveformCount', 'N/A')
    dtype = header.get('DataType', 'N/A')
    calib = header.get('Calibration', 'N/A')
    n_names = len(header.get('ChannelNames', []))
    
    print(f"  SamplingRate: {fs} Hz")
    print(f"  WaveformCount: {n_ch}")
    print(f"  DataType: {dtype}")
    print(f"  Calibration: {calib}")
    print(f"  ChannelNames parsed: {n_names}")

# Verify all runs have consistent sampling rate
sampling_rates = [run_headers[r].get('SamplingRate') for r in RUNS]
assert all(sr == sampling_rates[0] for sr in sampling_rates), (
    f"Inconsistent sampling rates across runs: {sampling_rates}"
)

FS = sampling_rates[0]
print(f"\nStep 2a OK: All runs have consistent sampling rate: {FS} Hz")


# Step 2b: quick header summary plot
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    # Just the table, no bar chart
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.axis('off')

    def ch_names_cell(h):
        names = h.get('ChannelNames') or []
        if not names:
            return 'N/A'
        return ', '.join(names)

    cols = ['Run', 'Fs', 'WaveformCount', 'DataType', 'Calibration', 'ChNames']
    rows = [[r, str(run_headers[r].get('SamplingRate', 'N/A')), str(run_headers[r].get('WaveformCount', 'N/A')),
             str(run_headers[r].get('DataType', 'N/A')), str(run_headers[r].get('Calibration', 'N/A')),
             ch_names_cell(run_headers[r])] for r in RUNS]
             
    t = ax.table(cellText=rows, colLabels=cols, loc='center', cellLoc='center')
    t.auto_set_font_size(False)
    t.set_fontsize(13)
    
    # Auto-adjust column widths so text doesn't overlap
    t.auto_set_column_width(col=list(range(len(cols))))
    
    t.scale(1.0, 2.5) # stretch rows vertically
    
    fig.suptitle(f'Step 2a: LAY Header Parsing\n{SUBJECT}_{SESSION}', fontweight='bold', fontsize=14)
    fig.tight_layout()
    fig_path = r"C:\Users\aakhtari\Documents\MATLAB\plots\step2a_header_parsing_plot.png"
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  Plot saved: {fig_path}')
except Exception as e:
    print(f'  Plot skipped: {e}')
    fig_path = None




#Step 4: Check Filter Feasibility


import numpy as np
from scipy.signal import sosfreqz, ellip
import matplotlib.pyplot as plt


#%% Checks
nyquist = FS / 2
print(f"Filter: {LOW_HZ}-{HIGH_HZ} Hz, Order {FILTER_ORDER}, Fs={FS} Hz")
print(f"Nyquist: {HIGH_HZ} < {nyquist} Hz -> {'OK' if HIGH_HZ < nyquist else 'FAIL'}")
#use ellip filter for stability instead of butter
# Design filter
sos = ellip(FILTER_ORDER, 0.5, 65, [LOW_HZ, HIGH_HZ], btype='bandpass', fs=FS, output='sos')
print(f"SOS sections: {sos.shape[0]} -> OK")

# Plot frequency response
w, h = sosfreqz(sos, worN=2048, fs=FS)
h_db = 20 * np.log10(np.abs(h) + 1e-10)

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(w, h_db, 'b', linewidth=1.5)
ax.axvline(LOW_HZ, color='r', linestyle='--', label=f'Low cutoff ({LOW_HZ} Hz)')
ax.axvline(HIGH_HZ, color='r', linestyle='--', label=f'High cutoff ({HIGH_HZ} Hz)')
ax.axhline(-3, color='g', linestyle=':', label='-3 dB')
ax.set_xlim([0, FS / 2])
ax.set_ylim([-80, 5])
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('Gain (dB)')
ax.set_title(f'Step 4: Elliptic Bandpass Filter Response\n{LOW_HZ}-{HIGH_HZ} Hz, Order {FILTER_ORDER}', fontweight='bold')
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)

# save and open so you see the plot
filter_plot_dir = PLOTS_DIR
os.makedirs(filter_plot_dir, exist_ok=True)
filter_plot_path = os.path.join(filter_plot_dir, "step3_filter_feasibility.png")
fig.savefig(filter_plot_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print(f"\n  Filter feasibility plot saved: {filter_plot_path}")
print("\nFilter feasible - OK")


# ── Step 5: Load CAR .dat metadata (no filtering yet) ──

dtype_map = {
    0: np.int16,
    1: np.int32,
    7: np.int32,
}

CAR_RUN_INFO = {}

print("\nStep 5: scanning CAR .dat files (size and basic info)...")

for run in RUNS:
    lay_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_LAY_SUFFIX}"
    dat_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_DAT_SUFFIX}"
    lay_path = os.path.join(CAR_INPUT_DIR, lay_name)
    dat_path = os.path.join(CAR_INPUT_DIR, dat_name)

    header = run_headers[run]
    fs = float(header.get("SamplingRate", FS))
    n_ch = int(header.get("WaveformCount", 0))
    dt_code = int(header.get("DataType", 0))
    calib = float(header.get("Calibration", 1.0))
    header_len = int(header.get("HeaderLength", 0)) if "HeaderLength" in header else 0

    dtype = dtype_map.get(dt_code, np.int16)
    bytes_per_sample = np.dtype(dtype).itemsize
    file_size = os.path.getsize(dat_path)

    if n_ch <= 0 or bytes_per_sample <= 0:
        n_samp = 0
    else:
        n_samp = max(0, (file_size - header_len) // (n_ch * bytes_per_sample))

    CAR_RUN_INFO[run] = {
        "dat_path": dat_path,
        "fs": fs,
        "n_channels": n_ch,
        "dtype": dtype,
        "calibration": calib,
        "header_len": header_len,
        "n_samples": int(n_samp),
    }

    dur_sec = n_samp / fs if fs > 0 else 0.0
    print(
        f"  {run}: {n_ch} ch x {n_samp} samples "
        f"({dur_sec/3600:.2f} h), dtype={dtype}, calib={calib}"
    )

print("Step 5 OK: CAR metadata loaded for all runs. Ready for filtering in next step.")


# ── Step 6: Apply bandpass filter to CAR data ──
#
# IMPORTANT: The CAR .dat files contain CONCATENATED HFO segments, not continuous data.
# Filtering them as one block causes transient artifacts at segment boundaries.
# FIX: Load segment lengths from car_reref's seg_lengths.npy, filter each segment
# individually with reflection padding to avoid edge transients.

from scipy.signal import sosfiltfilt
import time

# Padding samples for filter transients (at 4096 Hz, 100 samples = ~24 ms)
FILTER_PAD_SAMPLES = 100

# output directory for filtered data
FILTERED_OUTPUT_DIR = os.path.join(SUBJECT_DIR, "step3_bandpass")
os.makedirs(FILTERED_OUTPUT_DIR, exist_ok=True)

# sos filter already designed in Step 4, reuse it

print(f"\nStep 6: Applying {LOW_HZ}-{HIGH_HZ} Hz bandpass filter...")
print(f"  Output dir: {FILTERED_OUTPUT_DIR}")
print(f"  Using segment-wise filtering with {FILTER_PAD_SAMPLES} sample padding")

total_t0 = time.perf_counter()

for run in RUNS:
    info = CAR_RUN_INFO[run]
    dat_path = info["dat_path"]
    n_ch = info["n_channels"]
    n_samp = info["n_samples"]
    dtype = info["dtype"]
    calib = info["calibration"]
    header_len = info["header_len"]
    fs = info["fs"]

    print(f"\n  {run}: {n_ch} ch x {n_samp} samples ({n_samp/fs/3600:.2f} h)")

    run_t0 = time.perf_counter()

    # Load segment lengths saved by car_reref.py
    seg_lengths_path = os.path.join(CAR_INPUT_DIR, f"{SUBJECT}_{SESSION}_task-all_{run}_seg_lengths.npy")
    if os.path.isfile(seg_lengths_path):
        seg_lengths = np.load(seg_lengths_path).astype(int)
        use_segmentwise = True
        print(f"    found seg_lengths.npy: {len(seg_lengths)} segments")
    else:
        # Fallback: treat as single segment (old behavior)
        seg_lengths = None
        use_segmentwise = False
        print(f"    warning: no seg_lengths.npy, filtering as single block (may have transients)")

    # read entire CAR .dat file
    with open(dat_path, 'rb') as f:
        if header_len > 0:
            f.seek(header_len)
        raw = np.fromfile(f, dtype=dtype)

    # reshape to (n_samples, n_channels)
    n_samp_actual = len(raw) // n_ch
    if n_samp_actual * n_ch != len(raw):
        print(f"    warning: truncating {len(raw) - n_samp_actual * n_ch} extra samples")
    data = raw[:n_samp_actual * n_ch].reshape(n_samp_actual, n_ch).astype(np.float64)

    # apply calibration to get microvolts
    data *= calib

    print(f"    loaded: {data.shape}, applying filter...")

    if use_segmentwise and seg_lengths is not None:
        # SEGMENT-WISE FILTERING with padding to avoid transients
        filtered_segments = []
        seg_start = 0
        for seg_len in seg_lengths:
            if seg_len <= 0:
                continue
            seg_end = seg_start + seg_len
            if seg_end > data.shape[0]:
                seg_end = data.shape[0]
                seg_len = seg_end - seg_start
            if seg_len <= 0:
                break

            segment = data[seg_start:seg_end, :]

            # Add reflection padding to avoid edge transients
            pad_len = min(FILTER_PAD_SAMPLES, seg_len - 1)  # can't pad more than segment length
            if pad_len > 0:
                # Reflect padding: mirror the edges
                pad_left = segment[1:pad_len+1, :][::-1, :]
                pad_right = segment[-(pad_len+1):-1, :][::-1, :]
                padded = np.vstack([pad_left, segment, pad_right])
            else:
                padded = segment

            # Filter the padded segment
            filtered_padded = np.zeros_like(padded)
            for ch_i in range(n_ch):
                filtered_padded[:, ch_i] = sosfiltfilt(sos, padded[:, ch_i])

            # Remove padding
            if pad_len > 0:
                filtered_seg = filtered_padded[pad_len:-pad_len, :]
            else:
                filtered_seg = filtered_padded

            filtered_segments.append(filtered_seg)
            seg_start = seg_end

        # Concatenate all filtered segments
        filtered = np.vstack(filtered_segments)
    else:
        # Fallback: filter entire file as one block (old behavior)
        filtered = np.zeros_like(data)
        for ch_i in range(n_ch):
            filtered[:, ch_i] = sosfiltfilt(sos, data[:, ch_i])

    # convert back to original dtype for storage
    filtered /= calib
    # Only clip if output dtype is integer (not float)
    if np.issubdtype(dtype, np.integer):
        np.clip(filtered, np.iinfo(dtype).min, np.iinfo(dtype).max, out=filtered)
    filtered_int = filtered.astype(dtype)

    # save filtered .dat
    out_dat_name = f"{SUBJECT}_{SESSION}_task-all_{run}_ieeg_CAR_bp.dat"
    out_dat_path = os.path.join(FILTERED_OUTPUT_DIR, out_dat_name)
    filtered_int.tofile(out_dat_path)

    # copy and modify .lay to point to new .dat
    lay_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_LAY_SUFFIX}"
    lay_path = os.path.join(CAR_INPUT_DIR, lay_name)
    with open(lay_path, 'r') as f:
        lay_text = f.read()
    old_dat_name = f"{SUBJECT}_{SESSION}_task-all_{run}{CAR_DAT_SUFFIX}"
    lay_text = lay_text.replace(old_dat_name, out_dat_name)
    out_lay_path = os.path.join(FILTERED_OUTPUT_DIR, out_dat_name.replace('.dat', '.lay'))
    with open(out_lay_path, 'w') as f:
        f.write(lay_text)

    run_dt = time.perf_counter() - run_t0
    out_size_mb = os.path.getsize(out_dat_path) / 1e6
    print(f"    done in {run_dt:.1f}s, output: {out_size_mb:.1f} MB")
    print(f"    {out_dat_path}")

total_dt = time.perf_counter() - total_t0
print(f"\nStep 6 OK: Bandpass filtering complete. Total time: {total_dt:.1f}s")
print(f"  Filtered files saved to: {FILTERED_OUTPUT_DIR}")


# ── Step 6b: Before/After bandpass visualization ──

print("\nStep 6b: Generating before/after bandpass plot...")

# pick first run for visualization
viz_run = RUNS[0]
viz_info = CAR_RUN_INFO[viz_run]

# load a short segment (5 seconds) from the middle of the recording
viz_fs = viz_info["fs"]
viz_n_ch = viz_info["n_channels"]
viz_dtype = viz_info["dtype"]
viz_calib = viz_info["calibration"]
viz_header_len = viz_info["header_len"]
viz_n_samp = viz_info["n_samples"]

# 5-second window from the middle
seg_dur_sec = 5
seg_samples = int(seg_dur_sec * viz_fs)
start_sample = viz_n_samp // 2  # middle of recording

# read CAR data (before bandpass)
car_dat_path = viz_info["dat_path"]
bytes_per_sample = np.dtype(viz_dtype).itemsize
sample_stride = viz_n_ch * bytes_per_sample

with open(car_dat_path, 'rb') as f:
    f.seek(viz_header_len + start_sample * sample_stride)
    raw_before = np.fromfile(f, dtype=viz_dtype, count=seg_samples * viz_n_ch)

n_read = len(raw_before) // viz_n_ch
raw_before = raw_before[:n_read * viz_n_ch].reshape(n_read, viz_n_ch).astype(np.float64)
raw_before *= viz_calib  # convert to microvolts

# read filtered data (after bandpass)
bp_dat_path = os.path.join(FILTERED_OUTPUT_DIR, f"{SUBJECT}_{SESSION}_task-all_{viz_run}_ieeg_CAR_bp.dat")
with open(bp_dat_path, 'rb') as f:
    f.seek(start_sample * sample_stride)  # no header in our output
    raw_after = np.fromfile(f, dtype=viz_dtype, count=seg_samples * viz_n_ch)

n_read_after = len(raw_after) // viz_n_ch
raw_after = raw_after[:n_read_after * viz_n_ch].reshape(n_read_after, viz_n_ch).astype(np.float64)
raw_after *= viz_calib

# use the shorter of the two
n_plot = min(n_read, n_read_after)
raw_before = raw_before[:n_plot, :]
raw_after = raw_after[:n_plot, :]

# time axis
t_sec = np.arange(n_plot) / viz_fs

# pick first 5 channels to plot (cleaner visualization)
n_ch_plot = min(5, viz_n_ch)

# get channel names from the .lay header
lay_name = f"{SUBJECT}_{SESSION}_task-all_{viz_run}{CAR_LAY_SUFFIX}"
lay_path = os.path.join(CAR_INPUT_DIR, lay_name)
header = run_headers[viz_run]
ch_names = header.get('ChannelNames', [f'Ch{i}' for i in range(viz_n_ch)])

# create figure with 3 rows: before, after, overlay of one channel
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# row 1: before bandpass (stacked traces)
ax1 = axes[0]
offsets = np.arange(n_ch_plot) * 200  # 200 µV spacing between channels
for i in range(n_ch_plot):
    ax1.plot(t_sec, raw_before[:, i] + offsets[i], linewidth=0.5, label=ch_names[i] if i < len(ch_names) else f'Ch{i}')
ax1.set_ylabel('Amplitude (µV, offset)')
ax1.set_title(f'BEFORE Bandpass (CAR only) - {viz_run}', fontweight='bold')
ax1.legend(loc='upper right', fontsize=8)
ax1.set_xlim([t_sec[0], t_sec[-1]])
ax1.grid(True, alpha=0.3)

# row 2: after bandpass (stacked traces)
ax2 = axes[1]
for i in range(n_ch_plot):
    ax2.plot(t_sec, raw_after[:, i] + offsets[i], linewidth=0.5, label=ch_names[i] if i < len(ch_names) else f'Ch{i}')
ax2.set_ylabel('Amplitude (µV, offset)')
ax2.set_title(f'AFTER Bandpass ({LOW_HZ}-{HIGH_HZ} Hz) - {viz_run}', fontweight='bold')
ax2.legend(loc='upper right', fontsize=8)
ax2.set_xlim([t_sec[0], t_sec[-1]])
ax2.grid(True, alpha=0.3)

# row 3: overlay comparison for one channel (zoomed to 0.5 sec)
ax3 = axes[2]
zoom_samples = int(0.5 * viz_fs)  # 0.5 second zoom
ch_overlay = 0  # first channel
ax3.plot(t_sec[:zoom_samples], raw_before[:zoom_samples, ch_overlay],
         linewidth=1, alpha=0.7, label='Before (CAR)', color='blue')
ax3.plot(t_sec[:zoom_samples], raw_after[:zoom_samples, ch_overlay],
         linewidth=1, alpha=0.9, label=f'After ({LOW_HZ}-{HIGH_HZ} Hz)', color='red')
ax3.set_xlabel('Time (s)')
ax3.set_ylabel('Amplitude (µV)')
ch_label = ch_names[ch_overlay] if ch_overlay < len(ch_names) else f'Ch{ch_overlay}'
ax3.set_title(f'Overlay: {ch_label} (0.5s zoom)', fontweight='bold')
ax3.legend(loc='upper right', fontsize=9)
ax3.grid(True, alpha=0.3)

fig.suptitle(f'Step 6: Bandpass Filter Effect - {SUBJECT}_{SESSION}', fontweight='bold', fontsize=14)
fig.tight_layout()

# save plot
bp_plot_path = os.path.join(filter_plot_dir, "step6_bandpass_before_after.png")
fig.savefig(bp_plot_path, dpi=150, bbox_inches='tight')
plt.close(fig)

print(f"  Plot saved: {bp_plot_path}")