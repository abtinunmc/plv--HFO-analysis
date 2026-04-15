# Common Average Reference (CAR) re-referencing for Persyst .dat/.lay files.
# Uses the good SEEG channel list and valid HFO segments from the step3 validation .mat output.
# Only processes 500 random valid HFO segments per run (not the whole file).
#
# Usage: python car_reref.py [subject]
#   e.g. python car_reref.py sub-umich0019

import os, sys, re, time, glob
os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'

import numpy as np
from scipy.io import loadmat
import matplotlib.pyplot as plt

# Default subject (can be overridden via command line)
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else 'sub-umich0018'
SESSION = 'ses-ieeg01'

# Base paths
RAW_BASE = r'U:\shared\database\ieeg-UM\rawdata'
BASE_OUT_DIR = r'C:\Users\aakhtari\Documents\MATLAB'

# Per-subject directories (new organized structure)
SUBJECT_DIR = os.path.join(BASE_OUT_DIR, 'subjects', SUBJECT)
STEP3_DIR = os.path.join(SUBJECT_DIR, 'step1_hfo_validation')  # step3 .mat files
OUT_DIR = os.path.join(SUBJECT_DIR, 'step2_car')
PLOTS_DIR = os.path.join(SUBJECT_DIR, 'plots')
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

# Derived paths
RAW_DIR = os.path.join(RAW_BASE, SUBJECT, SESSION, 'ieeg')

# Auto-detect runs from step3 .mat files
def detect_runs():
    pattern = os.path.join(STEP3_DIR, 'step3_validated_qHFO_run-*.mat')
    files = glob.glob(pattern)
    runs = sorted(set(os.path.basename(f).replace('step3_validated_qHFO_', '').replace('.mat', '') for f in files))
    return runs if runs else ['run-01', 'run-02', 'run-03', 'run-04', 'run-05']

RUNS = detect_runs()

# only process this many random valid HFO segments per run (from preprocess step3 output)
MAX_HFO_SEGMENTS = 500


def _lay_get(text, section, key, default=None):
    """Get key=value from a [Section] block; section and key are case-insensitive."""
    sec_m = re.search(rf'\[{re.escape(section)}\](.*?)(?=\[|\Z)', text, re.I | re.S)
    if not sec_m:
        return default
    block = sec_m.group(1)
    m = re.search(rf'^{re.escape(key)}\s*=\s*(.+)$', block, re.M | re.I)
    if not m:
        return default
    return m.group(1).strip()


def parse_lay(lay_path):
    """Read a Persyst .lay header without ConfigParser (handles duplicate keys and non-INIs). Returns dict with fs, n_channels, calibration, dtype, channel names."""
    with open(lay_path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()

    n_ch = int(_lay_get(text, 'FileInfo', 'WaveformCount', '0'))
    dt = int(_lay_get(text, 'FileInfo', 'DataType', '0'))
    dtype = {0: np.int16, 1: np.int32, 7: np.int32}.get(dt, np.int16)

    ch_names = [''] * n_ch
    cm_match = re.search(r'\[ChannelMap\](.*?)(?=\[|\Z)', text, re.S)
    if cm_match:
        for line in cm_match.group(1).strip().splitlines():
            line = line.strip()
            if '=' in line:
                name, _, idx_str = line.partition('=')
                name, idx_str = name.strip(), idx_str.strip()
                try:
                    i = int(idx_str) - 1
                    if 0 <= i < n_ch:
                        ch_names[i] = name
                except ValueError:
                    pass

    return {
        'fs': int(_lay_get(text, 'FileInfo', 'SamplingRate', '0')),
        'n_channels': n_ch,
        'calibration': float(_lay_get(text, 'FileInfo', 'Calibration', '1.0')),
        'dtype': dtype,
        'header_len': int(_lay_get(text, 'FileInfo', 'HeaderLength', '0')),
        'ch_names': ch_names,
    }


def get_good_seeg_indices(step3_mat, lay_info):
    """Map good SEEG channel names from step3 output to 0-based indices in the .dat file."""
    mat = loadmat(step3_mat, squeeze_me=True)
    good_names = [str(n) for n in np.atleast_1d(mat['goodSEEG_names'])]

    # the .lay channel names have "-Ref" suffix, the tsv names don't
    lay_names_clean = [n.replace('-ref', '').replace('-Ref', '') for n in lay_info['ch_names']]

    indices = []
    for gn in good_names:
        try:
            indices.append(lay_names_clean.index(gn))
        except ValueError:
            print(f'  warning: channel "{gn}" not found in .lay, skipping')
    return indices, good_names


def get_hfo_segments(step3_mat, fs, max_segments, total_samples=None):
    """Load valid HFO start/stop times from step3 .mat, pick up to max_segments at random, return (start_samp, stop_samp) in sample indices, sorted by start.
    If total_samples is given, filter to only segments within file bounds."""
    mat = loadmat(step3_mat, squeeze_me=True)
    start_sec = np.atleast_1d(mat['validStartTime']).astype(float)
    stop_sec = np.atleast_1d(mat['validStopTime']).astype(float)
    start_samp = np.round(start_sec * fs).astype(np.int64)
    stop_samp = np.round(stop_sec * fs).astype(np.int64)
    # Filter to segments within file bounds
    if total_samples is not None:
        valid = (start_samp >= 0) & (stop_samp <= total_samples) & (stop_samp > start_samp)
        start_samp = start_samp[valid]
        stop_samp = stop_samp[valid]
    n = len(start_samp)
    if n == 0:
        return np.empty((0, 2), dtype=np.int64)
    if n > max_segments:
        rng = np.random.default_rng()
        idx = rng.choice(n, size=max_segments, replace=False)
        start_samp = start_samp[idx]
        stop_samp = stop_samp[idx]
    segs = np.column_stack([start_samp, stop_samp])
    segs = segs[segs[:, 0].argsort()]
    return segs


def process_run(run):
    lay_path = os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg.lay')
    dat_path = os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg.dat')
    step3_mat = os.path.join(STEP3_DIR, f'step3_validated_qHFO_{run}.mat')

    if not os.path.isfile(dat_path) or not os.path.isfile(lay_path):
        print(f'  {run}: skipped (missing .dat/.lay)')
        return
    if not os.path.isfile(step3_mat):
        print(f'  {run}: skipped (no step3 .mat — run preprocesspython.py first)')
        return

    t0 = time.perf_counter()

    lay = parse_lay(lay_path)
    good_idx, good_names = get_good_seeg_indices(step3_mat, lay)
    n_ch = lay['n_channels']
    fs = lay['fs']
    cal = lay['calibration']
    dtype = lay['dtype']
    bytes_per_sample = np.dtype(dtype).itemsize

    segments = get_hfo_segments(step3_mat, fs, MAX_HFO_SEGMENTS)
    n_seg = len(segments)
    if n_seg == 0:
        print(f'  {run}: no valid HFO segments in step3 .mat, skipped')
        return

    total_samples_out = int((segments[:, 1] - segments[:, 0]).sum())

    print(f'  {run}: {n_ch} channels, {len(good_idx)} good SEEG for CAR')
    print(f'         processing {n_seg} valid HFO segments ({total_samples_out} samples = {total_samples_out/fs:.1f} sec)')

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg_CAR.dat')
    out_lay = os.path.join(OUT_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg_CAR.lay')

    good_idx_arr = np.array(good_idx)
    sample_stride = n_ch * bytes_per_sample
    header_len = lay['header_len']

    seg_lengths_written = []
    with open(dat_path, 'rb') as fin, open(out_path, 'wb') as fout:
        for seg_idx, (start_samp, stop_samp) in enumerate(segments):
            seg_len = int(stop_samp - start_samp)
            if seg_len <= 0:
                continue
            byte_off = header_len + start_samp * sample_stride
            fin.seek(byte_off)
            raw = np.fromfile(fin, dtype=dtype, count=seg_len * n_ch)
            if len(raw) < seg_len * n_ch:
                seg_len = len(raw) // n_ch
                raw = raw[:seg_len * n_ch]
            if seg_len == 0:
                continue

            data = raw.reshape(seg_len, n_ch).astype(np.float32)
            data *= cal
            car_mean = data[:, good_idx_arr].mean(axis=1, keepdims=True)
            data[:, good_idx_arr] -= car_mean
            data /= cal
            # Only clip if output dtype is integer (not float)
            if np.issubdtype(dtype, np.integer):
                np.clip(data, np.iinfo(dtype).min, np.iinfo(dtype).max, out=data)
            data.astype(dtype).tofile(fout)
            seg_lengths_written.append(seg_len)

    # Save segment lengths in write order so PLV reads them correctly
    seg_lengths_path = os.path.join(OUT_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_seg_lengths.npy')
    np.save(seg_lengths_path, np.array(seg_lengths_written, dtype=np.int64))

    # write a matching .lay that points to the new .dat
    with open(lay_path, 'r') as f:
        lay_text = f.read()
    old_dat_name = os.path.basename(dat_path)
    new_dat_name = os.path.basename(out_path)
    lay_text = lay_text.replace(old_dat_name, new_dat_name)
    with open(out_lay, 'w') as f:
        f.write(lay_text)

    dt = time.perf_counter() - t0
    size_gb = os.path.getsize(out_path) / 1e9
    print(f'         done in {dt:.1f}s, output: {size_gb:.1f} GB')
    print(f'         {out_path}')
    return dt


def plot_sample_hfos_before_after(run='run-01', n=10, max_channels_plot=5, save_path=None):
    """Plot n sample HFO segments before and after CAR (read from raw .dat, apply CAR in memory)."""
    lay_path = os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg.lay')
    dat_path = os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg.dat')
    step3_mat = os.path.join(STEP3_DIR, f'step3_validated_qHFO_{run}.mat')

    if not os.path.isfile(dat_path) or not os.path.isfile(lay_path):
        print(f'  plot_sample_hfos: {run} missing .dat/.lay')
        return
    if not os.path.isfile(step3_mat):
        print(f'  plot_sample_hfos: no step3 .mat for {run}')
        return

    lay = parse_lay(lay_path)
    good_idx, good_names = get_good_seeg_indices(step3_mat, lay)
    n_ch = lay['n_channels']
    fs = lay['fs']
    cal = lay['calibration']
    dtype = lay['dtype']
    header_len = lay['header_len']
    bytes_per_sample = np.dtype(dtype).itemsize
    sample_stride = n_ch * bytes_per_sample
    good_idx_arr = np.array(good_idx)

    # Get total samples in file to filter out-of-bounds HFOs
    file_size = os.path.getsize(dat_path)
    total_samples = (file_size - header_len) // sample_stride

    segments = get_hfo_segments(step3_mat, fs, n, total_samples=total_samples)
    n_seg = min(len(segments), n)
    if n_seg == 0:
        print(f'  plot_sample_hfos: no valid HFO segments for {run}')
        return

    # Identify channels with extreme values (outliers) by reading first segment
    outlier_threshold = 500  # µV
    first_seg = segments[0]
    with open(dat_path, 'rb') as f:
        f.seek(header_len + int(first_seg[0]) * sample_stride)
        seg_len_check = int(first_seg[1] - first_seg[0])
        raw_check = np.fromfile(f, dtype=dtype, count=seg_len_check * n_ch)
        if len(raw_check) == seg_len_check * n_ch:
            data_check = raw_check.reshape(seg_len_check, n_ch).astype(np.float32) * cal
            max_abs = np.abs(data_check[:, good_idx_arr]).max(axis=0)
            good_mask = max_abs < outlier_threshold
            clean_idx = [good_idx_arr[i] for i in range(len(good_idx_arr)) if good_mask[i]]
            clean_names = [good_names[i] for i in range(len(good_names)) if good_mask[i]]
        else:
            clean_idx, clean_names = list(good_idx_arr), good_names

    ch_plot = np.array(clean_idx[:max_channels_plot])
    names_plot = clean_names[:max_channels_plot]

    if len(ch_plot) == 0:
        print(f'  plot_sample_hfos: all channels have outliers, skipping plot')
        return

    fig, axes = plt.subplots(n_seg, 2, figsize=(10, 1.8 * n_seg), sharex='col')
    if n_seg == 1:
        axes = axes.reshape(1, -1)

    with open(dat_path, 'rb') as fin:
        for row, (start_samp, stop_samp) in enumerate(segments[:n_seg]):
            seg_len = int(stop_samp - start_samp)
            if seg_len <= 0:
                continue
            byte_off = header_len + start_samp * sample_stride
            fin.seek(byte_off)
            raw = np.fromfile(fin, dtype=dtype, count=seg_len * n_ch)
            if len(raw) < seg_len * n_ch:
                seg_len = len(raw) // n_ch
                raw = raw[:seg_len * n_ch]
            if seg_len == 0:
                continue

            data = raw.reshape(seg_len, n_ch).astype(np.float32)
            data *= cal
            before = data[:, ch_plot].copy()
            car_mean = data[:, good_idx_arr].mean(axis=1, keepdims=True)
            data[:, good_idx_arr] -= car_mean
            after = data[:, ch_plot].copy()
            data /= cal

            t_sec = np.arange(seg_len, dtype=np.float64) / fs
            for col, (label, arr) in enumerate([('Before CAR', before), ('After CAR', after)]):
                ax = axes[row, col]
                for ch_i, (idx, name) in enumerate(zip(ch_plot, names_plot)):
                    offset = ch_i * 100  # μV offset to stack traces
                    ax.plot(t_sec, arr[:, ch_i] + offset, label=name, linewidth=0.6)
                ax.set_ylabel('μV (offset)')
                ax.set_title(label if row == 0 else '')
                ax.legend(loc='upper right', fontsize=6)
                ax.grid(True, alpha=0.3)

    axes[0, 0].set_title('Before CAR')
    axes[0, 1].set_title('After CAR')
    for row in range(n_seg):
        axes[row, 0].set_ylabel(f'HFO {row+1}\nμV (offset)')
    axes[-1, 0].set_xlabel('Time (s)')
    axes[-1, 1].set_xlabel('Time (s)')
    fig.suptitle(f'{SUBJECT} {run}: {n_seg} sample HFOs before vs after CAR', fontweight='bold')
    plt.tight_layout()

    if save_path is None:
        save_path = os.path.join(PLOTS_DIR, f'step2_car_before_after_{run}.png')
    plt.savefig(save_path, dpi=120)
    plt.close()
    print(f'  Saved: {save_path}')


# Main: run CAR for each run and print total time

print(f'CAR re-referencing: {SUBJECT}, {len(RUNS)} runs\n')
t_total = time.perf_counter()

for run in RUNS:
    print(f'-- {run} --')
    process_run(run)
    print()

print(f'total runtime: {time.perf_counter() - t_total:.1f}s')

# Plot 10 sample HFOs before vs after CAR for run-01
print('\n-- plot 10 sample HFOs before/after CAR (run-01) --')
plot_sample_hfos_before_after('run-01', n=10)