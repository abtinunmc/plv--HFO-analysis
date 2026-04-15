# HFO validation across all runs for a patient.
# Keeps only HFOs that sit entirely within clean-signal windows on ALL good SEEG channels.
# Optionally limits output to 500 random valid HFOs per run.
#
# Usage: python preprocesspython.py [subject]
#   e.g. python preprocesspython.py sub-umich0019

import os, sys, csv, time, glob
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'  # h5py chokes on network drives without this

import numpy as np

# set to None to keep all valid HFOs; set to e.g. 500 to keep only that many random valid per run
MAX_RANDOM_VALID_HFOS = 500
import h5py
from scipy.io import savemat

# Default subject (can be overridden via command line)
SUBJECT = sys.argv[1] if len(sys.argv) > 1 else 'sub-umich0018'
SESSION = 'ses-ieeg01'

# Base paths
RAW_BASE = r'U:\shared\database\ieeg-UM\rawdata'
H5_DIR = r'U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba'
BASE_OUT_DIR = r'C:\Users\aakhtari\Documents\MATLAB'

# Per-subject output directory (new organized structure)
SUBJECT_DIR = os.path.join(BASE_OUT_DIR, 'subjects', SUBJECT)
OUT_DIR = os.path.join(SUBJECT_DIR, 'step1_hfo_validation')
PLOTS_DIR = os.path.join(SUBJECT_DIR, 'plots')
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)

# Derived paths
RAW_DIR = os.path.join(RAW_BASE, SUBJECT, SESSION, 'ieeg')

# Auto-detect runs from H5 files
def detect_runs():
    pattern = os.path.join(H5_DIR, f'{SUBJECT}_{SESSION}_task-all_run-*_glap-qHFO_v4.0_Staba.h5')
    files = glob.glob(pattern)
    runs = sorted(set(os.path.basename(f).split('_')[3] for f in files))
    return runs if runs else ['run-01', 'run-02', 'run-03', 'run-04', 'run-05']

RUNS = detect_runs()


def intersect_intervals(A, B):
    """Two-pointer merge to find overlapping time between two sorted interval sets."""
    out, i, j = [], 0, 0
    while i < len(A) and j < len(B):
        lo, hi = max(A[i, 0], B[j, 0]), min(A[i, 1], B[j, 1])
        if lo < hi:
            out.append((lo, hi))
        if A[i, 1] < B[j, 1]:
            i += 1
        else:
            j += 1
    return np.array(out).reshape(-1, 2) if out else np.empty((0, 2))


def process_run(run):
    h5f = os.path.join(H5_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_glap-qHFO_v4.0_Staba.h5')
    tsvf = os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_channels.tsv')
    if not os.path.isfile(h5f) or not os.path.isfile(tsvf):
        return None

    # grab the good SEEG channels from the tsv
    good_idx, good_names = [], []
    with open(tsvf) as f:
        for i, row in enumerate(csv.DictReader(f, delimiter='\t'), start=1):
            if row.get('type') == 'SEEG' and row.get('status') == 'good':
                good_idx.append(i)
                good_names.append(row['name'])

    # pull HFO events + per-channel valid-signal windows from h5
    with h5py.File(h5f, 'r') as hf:
        hfo_ch = hf['/qHFO/chanIdx'][:].ravel()
        hfo_start = hf['/qHFO/start_time'][:].ravel().astype(float)
        hfo_stop = hf['/qHFO/stop_time'][:].ravel().astype(float)
        vt_ch = hf['/validTimes/chanIdx'][:].ravel()
        vt_start = hf['/validTimes/start_time'][:].ravel().astype(float)
        vt_stop = hf['/validTimes/stop_time'][:].ravel().astype(float)

    # intersect valid windows across channels one by one.
    # after this, all_good = time ranges where every channel is clean.
    
    all_good = None
    for ch in good_idx:
        mask = vt_ch == ch
        iv = np.column_stack([vt_start[mask], vt_stop[mask]])
        iv = iv[iv[:, 0].argsort()]
        all_good = iv if all_good is None else intersect_intervals(all_good, iv)
        if len(all_good) == 0:
            break

    # check each HFO against all_good using binary search
    n_hfo = len(hfo_ch)
    if all_good is None or len(all_good) == 0:
        valid = np.zeros(n_hfo, dtype=bool)
    else:
        starts = all_good[:, 0]
        max_stop = np.maximum.accumulate(all_good[:, 1])
        idx = np.searchsorted(starts, hfo_start, side='right') - 1
        valid = (idx >= 0) & (max_stop[np.clip(idx, 0, len(starts) - 1)] >= hfo_stop)

    n_valid = int(valid.sum())

    # optionally keep only a random subset of valid HFOs (e.g. 500) for downstream use
    valid_idx = np.where(valid)[0]
    n_valid_full = len(valid_idx)
    if MAX_RANDOM_VALID_HFOS is not None and n_valid_full > MAX_RANDOM_VALID_HFOS:
        rng = np.random.default_rng()
        valid_idx = rng.choice(valid_idx, size=MAX_RANDOM_VALID_HFOS, replace=False)
        valid_idx.sort()
        valid = np.zeros(n_hfo, dtype=bool)
        valid[valid_idx] = True
        n_valid = len(valid_idx)

    savemat(os.path.join(OUT_DIR, f'step3_validated_qHFO_{run}.mat'), {
        'valid': valid.astype(np.uint8),
        'validIdx': np.where(valid)[0] + 1,
        'validChanIdx': hfo_ch[valid],
        'validStartTime': hfo_start[valid],
        'validStopTime': hfo_stop[valid],
        'goodSEEG_idx': np.array(good_idx),
        'goodSEEG_names': np.array(good_names, dtype=object),
        'nGoodCh': len(good_idx),
        'nHFO': n_hfo,
        'nValid': n_valid,
        'qhfo_chanIdx': hfo_ch,
        'qhfo_startTime': hfo_start,
        'qhfo_stopTime': hfo_stop,
    }, do_compression=True)

    return {'run': run, 'n_hfo': n_hfo, 'n_valid': n_valid, 'n_valid_full': n_valid_full}


# --- main ---

print(f'Processing {SUBJECT}, {len(RUNS)} runs\n')
t0 = time.perf_counter()

# runs are independent and bottlenecked by network reads, so run them in parallel
with ThreadPoolExecutor(max_workers=len(RUNS)) as pool:
    futures = {pool.submit(process_run, r): r for r in RUNS}
    results = []
    for fut in as_completed(futures):
        r = fut.result()
        if r is None:
            print(f'  {futures[fut]}: skipped (missing files)')
            continue
        pct = 100 * r['n_valid_full'] / max(r['n_hfo'], 1)
        if MAX_RANDOM_VALID_HFOS and r['n_valid_full'] > r['n_valid']:
            print(f"  {r['run']}: {r['n_valid']}/{r['n_hfo']} valid ({pct:.1f}%), kept {r['n_valid']} random")
        else:
            print(f"  {r['run']}: {r['n_valid']}/{r['n_hfo']} valid ({pct:.1f}%)")
        results.append(r)

results.sort(key=lambda x: x['run'])

# summary
tot_h = sum(r['n_hfo'] for r in results)
tot_v = sum(r['n_valid'] for r in results)
tot_v_full = sum(r['n_valid_full'] for r in results)
pct_denom = max(tot_h, 1)
print(f'\n  {"Run":<8} {"Total":>7} {"Valid":>7} {"Rej":>7} {"%":>6}')
for r in results:
    rej = r['n_hfo'] - r['n_valid']
    pct = 100 * r['n_valid_full'] / max(r['n_hfo'], 1)
    print(f'  {r["run"]:<8} {r["n_hfo"]:>7} {r["n_valid"]:>7} {rej:>7} {pct:>5.1f}%')
print(f'  {"total":<8} {tot_h:>7} {tot_v:>7} {tot_h-tot_v:>7} '
      f'{100*tot_v_full/pct_denom:>5.1f}%')

# bar chart
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    x = np.arange(len(results))
    names = [r['run'] for r in results]
    v = [r['n_valid'] for r in results]
    rej = [r['n_hfo'] - r['n_valid'] for r in results]

    ax1.bar(x, v, color='#33b35a', label='Valid')
    ax1.bar(x, rej, bottom=v, color='#e63333', label='Rejected')
    ax1.set_xticks(x)
    ax1.set_xticklabels(names)
    ax1.legend()
    ax1.set_ylabel('Count')

    ax2.bar(x, [100 * r['n_valid'] / max(r['n_hfo'], 1) for r in results], color='#4488cc')
    ax2.set_xticks(x)
    ax2.set_xticklabels(names)
    ax2.set_ylabel('Valid %')
    ax2.set_ylim(0, 105)

    fig.suptitle(f'{SUBJECT} - qHFO validation', fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS_DIR, 'step1_validation_summary.png'), dpi=150)
    print('\nplot saved')
except ImportError:
    pass

print(f'\ntotal runtime: {time.perf_counter() - t0:.2f}s')
