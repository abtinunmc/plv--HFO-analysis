"""
Step 3: HFO Validation — Filter qHFOs Based on Good Signal Across All Channels
Keeps a qHFO only if ALL good SEEG channels have clean signal during its full time window.
"""

import os
os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'
import time
import numpy as np

# ── Paths ──
H5_FILE = r'U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\sub-umich0018_ses-ieeg01_task-all_run-01_glap-qHFO_v4.0_Staba.h5'
CHANNELS_TSV = r'U:\shared\database\ieeg-UM\rawdata\sub-umich0018\ses-ieeg01\ieeg\sub-umich0018_ses-ieeg01_task-all_run-01_channels.tsv'
OUTPUT_MAT = r'C:\Users\aakhtari\Documents\MATLAB\step3_validated_qHFO.mat'
OUTPUT_TXT = r'C:\Users\aakhtari\Documents\MATLAB\plvhfo1_output.txt'


def intersect_two_interval_sets(A, B):
    """Compute time intervals where BOTH A and B have coverage."""
    if len(A) == 0 or len(B) == 0:
        return np.empty((0, 2))

    events = []
    for s, e in A:
        events.append((s, 1, 0))   # A starts
        events.append((e, -1, 0))  # A ends
    for s, e in B:
        events.append((s, 0, 1))   # B starts
        events.append((e, 0, -1))  # B ends

    events.sort(key=lambda x: (x[0], -(x[1] + x[2])))

    cA = cB = 0
    in_both = False
    out = []
    for t, dA, dB in events:
        cA += dA
        cB += dB
        now_both = (cA > 0) and (cB > 0)
        if now_both and not in_both:
            out.append([t, None])
        elif not now_both and in_both:
            out[-1][1] = t
        in_both = now_both

    if len(out) == 0:
        return np.empty((0, 2))
    return np.array(out, dtype=float)


def load_real_data():
    """Load from actual H5 + TSV files on U: drive."""
    import h5py
    import csv

    print('[A] Reading channels.tsv...')
    good_idx = []
    good_names = []
    all_types = []
    with open(CHANNELS_TSV, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader, start=1):
            all_types.append(row.get('type', ''))
            if row.get('type') == 'SEEG' and row.get('status') == 'good':
                good_idx.append(i)
                good_names.append(row['name'])

    n_good = len(good_idx)
    n_seeg = sum(1 for t in all_types if t == 'SEEG')
    print(f'  Total channels: {len(all_types)}')
    print(f'  SEEG channels: {n_seeg}')
    print(f'  Good SEEG channels: {n_good}')
    print(f'  Channels: {", ".join(good_names)}')

    print('\n[B] Loading qHFO events from H5...')
    with h5py.File(H5_FILE, 'r') as hf:
        qhfo_chanIdx   = hf['/qHFO/chanIdx'][:].flatten()
        qhfo_startTime = hf['/qHFO/start_time'][:].flatten().astype(float)
        qhfo_stopTime  = hf['/qHFO/stop_time'][:].flatten().astype(float)

        print(f'  Total qHFOs: {len(qhfo_chanIdx)}')
        print(f'  Time range: {qhfo_startTime.min():.1f} – {qhfo_stopTime.max():.1f} sec '
              f'({(qhfo_stopTime.max()-qhfo_startTime.min())/3600:.1f} hours)')
        print(f'  Channels with HFOs: {len(np.unique(qhfo_chanIdx))} unique')

        print('\n[C] Loading validTimes from H5...')
        vt_chanIdx   = hf['/validTimes/chanIdx'][:].flatten()
        vt_startTime = hf['/validTimes/start_time'][:].flatten().astype(float)
        vt_stopTime  = hf['/validTimes/stop_time'][:].flatten().astype(float)

    print(f'  Total valid intervals: {len(vt_chanIdx)}')
    print(f'  Channels covered: {len(np.unique(vt_chanIdx))} unique')

    return (np.array(good_idx), good_names, n_good,
            qhfo_chanIdx, qhfo_startTime, qhfo_stopTime,
            vt_chanIdx, vt_startTime, vt_stopTime)


def make_demo_data():
    """Generate synthetic data when U: drive is unavailable."""
    print('  [DEMO MODE] Real files not found. Using synthetic data.\n')

    print('[A] DEMO: Building synthetic channels (32 good SEEG)...')
    n_good = 32
    good_idx = np.arange(1, n_good + 1)
    good_names = [f'Ch{i:02d}' for i in range(1, n_good + 1)]
    print(f'  Good SEEG channels: {n_good}')

    print('\n[B] DEMO: Generating synthetic qHFO events...')
    rng = np.random.default_rng(42)
    n_hfo = 15000
    t_max = 7200.0
    qhfo_chanIdx = rng.integers(1, n_good + 1, size=n_hfo)
    qhfo_startTime = rng.random(n_hfo) * (t_max - 1)
    qhfo_dur = 0.05 + 0.05 * rng.random(n_hfo)
    qhfo_stopTime = qhfo_startTime + qhfo_dur
    print(f'  Total qHFOs: {n_hfo}')
    print(f'  Time range: {qhfo_startTime.min():.1f} – {qhfo_stopTime.max():.1f} sec '
          f'({(qhfo_stopTime.max()-qhfo_startTime.min())/3600:.1f} hours)')

    print('\n[C] DEMO: Generating synthetic validTimes (good signal per channel)...')
    n_intervals_per_ch = 20
    vt_chanIdx_list, vt_start_list, vt_stop_list = [], [], []
    for ch in range(1, n_good + 1):
        st = np.sort(rng.random(n_intervals_per_ch) * t_max * 0.8)
        dur = 50 + rng.random(n_intervals_per_ch) * 100
        en = np.minimum(st + dur, t_max)
        vt_chanIdx_list.extend([ch] * n_intervals_per_ch)
        vt_start_list.extend(st)
        vt_stop_list.extend(en)
    vt_chanIdx = np.array(vt_chanIdx_list)
    vt_startTime = np.array(vt_start_list)
    vt_stopTime = np.array(vt_stop_list)
    print(f'  Total valid intervals: {len(vt_chanIdx)}')
    print(f'  Channels covered: {len(np.unique(vt_chanIdx))} unique')

    return (good_idx, good_names, n_good,
            qhfo_chanIdx, qhfo_startTime, qhfo_stopTime,
            vt_chanIdx, vt_startTime, vt_stopTime)


def main():
    sep = '=' * 59
    print(sep)
    print('  STEP 3: qHFO VALIDATION (Good Signal Check) — Python')
    print(sep + '\n')

    # ── Load data ──
    use_demo = not (os.path.isfile(H5_FILE) and os.path.isfile(CHANNELS_TSV))
    if use_demo:
        data = make_demo_data()
    else:
        data = load_real_data()

    (good_idx, good_names, n_good,
     qhfo_chanIdx, qhfo_startTime, qhfo_stopTime,
     vt_chanIdx, vt_startTime, vt_stopTime) = data
    n_hfo = len(qhfo_chanIdx)

    # ── D: Group validTimes by good SEEG channel ──
    print('\n[D] Building good-signal lookup per channel...')
    good_intervals = []
    for i, ch in enumerate(good_idx):
        mask = vt_chanIdx == ch
        intervals = np.column_stack([vt_startTime[mask], vt_stopTime[mask]]) if mask.any() else np.empty((0, 2))
        good_intervals.append(intervals)

    counts = [len(g) for g in good_intervals]
    print(f'  Intervals per channel: min={min(counts)}, max={max(counts)}, mean={np.mean(counts):.1f}')

    # ── E (FAST): Intersection + vectorized check ──
    print(f'\n[E] FAST: Computing intersection of good-signal intervals (all {n_good} channels)...')
    t0 = time.perf_counter()
    all_good = good_intervals[0].copy()
    for c in range(1, n_good):
        all_good = intersect_two_interval_sets(all_good, good_intervals[c])
        if len(all_good) == 0:
            break
    t_intersect = time.perf_counter() - t0
    print(f'  Intersection: {len(all_good)} intervals in {t_intersect:.3f} sec')

    if len(all_good) == 0:
        valid = np.zeros(n_hfo, dtype=bool)
        print('  No time where all channels are good -> all HFOs rejected.')
    else:
        order = np.argsort(all_good[:, 0])
        all_good = all_good[order]
        all_good_start = all_good[:, 0]
        all_good_stop  = all_good[:, 1]
        max_stop_until = np.maximum.accumulate(all_good_stop)

        print(f'  Validating {n_hfo} qHFOs (vectorized)...')
        t0 = time.perf_counter()
        idx = np.searchsorted(all_good_start, qhfo_startTime, side='right') - 1
        idx_safe = np.clip(idx, 0, len(all_good_start) - 1)
        valid = (idx >= 0) & (max_stop_until[idx_safe] >= qhfo_stopTime)
        elapsed = time.perf_counter() - t0
        print(f'  Validation completed in {elapsed:.4f} seconds')

    # ── F: Results ──
    n_valid = int(valid.sum())
    n_rejected = n_hfo - n_valid

    print(f'\n{sep}')
    print('  RESULTS')
    print(sep)
    print(f'  Total qHFOs:    {n_hfo}')
    print(f'  Valid qHFOs:    {n_valid} ({100*n_valid/max(n_hfo,1):.1f}%)')
    print(f'  Rejected qHFOs: {n_rejected} ({100*n_rejected/max(n_hfo,1):.1f}%)')

    valid_chan = qhfo_chanIdx[valid]
    valid_start = qhfo_startTime[valid]
    valid_stop = qhfo_stopTime[valid]
    valid_idx = np.where(valid)[0]

    print('\n  Valid HFOs per channel:')
    for i, ch in enumerate(good_idx):
        cnt = int((valid_chan == ch).sum())
        if cnt > 0:
            print(f'    {good_names[i]:<4s} (idx {ch:2d}): {cnt} HFOs')

    # ── G: Save results ──
    try:
        from scipy.io import savemat
        savemat(OUTPUT_MAT, {
            'validIdx': valid_idx + 1,
            'validChanIdx': valid_chan,
            'validStartTime': valid_start,
            'validStopTime': valid_stop,
            'goodSEEG_idx': good_idx,
            'goodSEEG_names': np.array(good_names, dtype=object),
            'nGoodCh': n_good,
            'nHFO': n_hfo,
            'nValid': n_valid,
            'qhfo_chanIdx': qhfo_chanIdx,
            'qhfo_startTime': qhfo_startTime,
            'qhfo_stopTime': qhfo_stopTime,
            'valid': valid.astype(np.uint8),
        })
        print(f'\n  Saved: {OUTPUT_MAT}')
    except ImportError:
        npz_path = OUTPUT_MAT.replace('.mat', '.npz')
        np.savez(npz_path,
                 validIdx=valid_idx, validChanIdx=valid_chan,
                 validStartTime=valid_start, validStopTime=valid_stop,
                 goodSEEG_idx=good_idx, valid=valid,
                 qhfo_chanIdx=qhfo_chanIdx,
                 qhfo_startTime=qhfo_startTime, qhfo_stopTime=qhfo_stopTime)
        print(f'\n  scipy not found, saved as NumPy: {npz_path}')

    # ── H: Visualization ──
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(16, 6))

        axes[0].bar(['Valid', 'Rejected'], [n_valid, n_rejected],
                     color=['#33b35a', '#e63333'])
        axes[0].set_ylabel('Count')
        axes[0].set_title(f'qHFO Validation\n{n_valid}/{n_hfo} kept ({100*n_valid/max(n_hfo,1):.0f}%)')

        ch_counts = [int((valid_chan == ch).sum()) for ch in good_idx]
        axes[1].barh(range(n_good), ch_counts, color='#4488cc')
        axes[1].set_yticks(range(n_good))
        axes[1].set_yticklabels(good_names, fontsize=7)
        axes[1].set_xlabel('Valid HFO Count')
        axes[1].set_title('Valid HFOs per Channel')

        if n_valid > 0:
            axes[2].hist(valid_start / 3600, bins=50, color='#4d80cc')
        axes[2].set_xlabel('Time (hours)')
        axes[2].set_ylabel('HFO Count')
        axes[2].set_title('Valid HFO Distribution Over Time')

        fig.suptitle('Step 3: qHFO Validation Results (Python)', fontweight='bold')
        fig.tight_layout()
        fig_path = os.path.join(os.path.dirname(OUTPUT_MAT), 'step3_validation_plot.png')
        fig.savefig(fig_path, dpi=150)
        print(f'  Plot saved: {fig_path}')
        plt.close(fig)
    except ImportError:
        print('  matplotlib not available, skipping plot.')

    print(f'\n{sep}')
    print('  STEP 3 COMPLETE')
    print(sep)


if __name__ == '__main__':
    import sys

    class Tee:
        """Write to both stdout and a log file."""
        def __init__(self, path):
            self.file = open(path, 'w', encoding='utf-8')
            self.stdout = sys.stdout
        def write(self, data):
            self.stdout.write(data)
            self.file.write(data)
        def flush(self):
            self.stdout.flush()
            self.file.flush()
        def close(self):
            self.file.close()

    tee = Tee(OUTPUT_TXT)
    sys.stdout = tee
    try:
        main()
    finally:
        sys.stdout = tee.stdout
        tee.close()
    print(f'\nLog saved to: {OUTPUT_TXT}')
