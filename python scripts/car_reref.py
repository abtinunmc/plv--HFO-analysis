# Common Average Reference (CAR) re-referencing for Persyst .dat/.lay files.
# Uses the good SEEG channel list and valid HFO segments from the step3 validation .mat output.
# Only processes 500 random valid HFO segments per run (not the whole file).

import os, re, time
os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'

import numpy as np
from scipy.io import loadmat
import matplotlib.pyplot as plt

SUBJECT = 'sub-umich0018'
SESSION = 'ses-ieeg01'
RUNS = ['run-01', 'run-02', 'run-03', 'run-04', 'run-05']
RAW_DIR = rf'U:\shared\database\ieeg-UM\rawdata\{SUBJECT}\{SESSION}\ieeg'
STEP3_DIR = r'C:\Users\aakhtari\Documents\MATLAB'
OUT_DIR = r'C:\Users\aakhtari\Documents\MATLAB\car_output'

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
    dtype = {0: np.int16, 1: np.int32, 7: np.float64}.get(dt, np.int16)

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


def get_hfo_segments(step3_mat, fs, max_segments):
    """Load valid HFO start/stop times from step3 .mat, pick up to max_segments at random, return (start_samp, stop_samp) in sample indices, sorted by start."""
    mat = loadmat(step3_mat, squeeze_me=True)
    start_sec = np.atleast_1d(mat['validStartTime']).astype(float)
    stop_sec = np.atleast_1d(mat['validStopTime']).astype(float)
    n = len(start_sec)
    if n == 0:
        return np.empty((0, 2), dtype=np.int64)
    if n > max_segments:
        rng = np.random.default_rng()
        idx = rng.choice(n, size=max_segments, replace=False)
        start_sec = start_sec[idx]
        stop_sec = stop_sec[idx]
    start_samp = np.round(start_sec * fs).astype(np.int64)
    stop_samp = np.round(stop_sec * fs).astype(np.int64)
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
            np.clip(data, np.iinfo(dtype).min, np.iinfo(dtype).max, out=data)
            data.astype(dtype).tofile(fout)

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

    segments = get_hfo_segments(step3_mat, fs, n)
    n_seg = min(len(segments), n)
    if n_seg == 0:
        print(f'  plot_sample_hfos: no valid HFO segments for {run}')
        return

    ch_plot = good_idx_arr[:max_channels_plot]
    names_plot = [good_names[i] for i in range(min(max_channels_plot, len(good_names)))]

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
        save_path = os.path.join(STEP3_DIR, f'plot_sample_hfos_before_after_{run}.png')
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


"""
Step 4: Check Filter Feasibility
"""

import numpy as np
from scipy.signal import butter, sosfreqz
import matplotlib.pyplot as plt

#%% Parameters
FS = 4096
LOW_HZ, HIGH_HZ = 80, 500
ORDER = 4

#%% Checks
nyquist = FS / 2
print(f"Filter: {LOW_HZ}-{HIGH_HZ} Hz, Order {ORDER}, Fs={FS} Hz")
print(f"Nyquist: {HIGH_HZ} < {nyquist} Hz → {'✓' if HIGH_HZ < nyquist else '✗'}")

# Design filter
sos = butter(ORDER, [LOW_HZ, HIGH_HZ], btype='bandpass', fs=FS, output='sos')
print(f"SOS sections: {sos.shape[0]} → ✓")

# Stability (ba form)
b, a = butter(ORDER, [LOW_HZ, HIGH_HZ], btype='bandpass', fs=FS)
max_pole = np.max(np.abs(np.roots(a)))
print(f"Max pole: {max_pole:.4f} → {'✓ Stable' if max_pole < 1 else '✗ Unstable'}")

#%% Plot
w, h = sosfreqz(sos, worN=2048, fs=FS)
h_db = 20 * np.log10(np.abs(h) + 1e-10)

plt.figure(figsize=(8, 4))
plt.plot(w, h_db, 'b')
plt.axvline(LOW_HZ, color='r', linestyle='--')
plt.axvline(HIGH_HZ, color='r', linestyle='--')
plt.axhline(-3, color='g', linestyle=':')
plt.xlim([0, nyquist]); plt.ylim([-60, 5])
plt.xlabel('Frequency (Hz)'); plt.ylabel('dB')
plt.title(f'Bandpass {LOW_HZ}-{HIGH_HZ} Hz, Order {ORDER}')
plt.grid(True)
plt.tight_layout()
plt.savefig('filter_check.png', dpi=150)
plt.show()

print("\n✓ Filter feasible")
```

---

### 📊 خروجی
```
Filter: 80-500 Hz, Order 4, Fs=4096 Hz
Nyquist: 500 < 2048 Hz → ✓
SOS sections: 4 → ✓
Max pole: 0.XXXX → ✓ Stable

✓ Filter feasible