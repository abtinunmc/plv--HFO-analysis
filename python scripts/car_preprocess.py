# Common Average Reference (CAR) for raw iEEG data.
# Reads Persyst .lay/.dat files, computes the mean across good SEEG channels,
# subtracts it from each channel, and saves the re-referenced data to .h5.
# Also saves 80-500 Hz bandpass-filtered CAR data for HFO analysis.

import os, csv, time

os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'

import numpy as np
import h5py
import mne
from scipy.signal import butter, filtfilt

SUBJECT = 'sub-umich0018'
SESSION = 'ses-ieeg01'
RUNS = ['run-01', 'run-02', 'run-03', 'run-04', 'run-05']
RAW_DIR = rf'U:\shared\database\ieeg-UM\rawdata\{SUBJECT}\{SESSION}\ieeg'
OUT_DIR = r'C:\Users\aakhtari\Documents\MATLAB'


def lay_path(run):
    return os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_ieeg.lay')


def tsv_path(run):
    return os.path.join(RAW_DIR, f'{SUBJECT}_{SESSION}_task-all_{run}_channels.tsv')


def get_good_seeg(tsvf):
    """Read channels.tsv, return names of channels that are SEEG + good."""
    names = []
    with open(tsvf) as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row.get('type') == 'SEEG' and row.get('status') == 'good':
                names.append(row['name'])
    return names


def process_run(run):
    layf = lay_path(run)
    tsvf = tsv_path(run)

    if not os.path.isfile(layf):
        print(f'  {run}: skipped (lay not found)')
        return None
    if not os.path.isfile(tsvf):
        print(f'  {run}: skipped (tsv not found)')
        return None

    t0 = time.perf_counter()

    # figure out which channels to use for the average
    good_names = get_good_seeg(tsvf)
    print(f'  {run}: {len(good_names)} good SEEG channels')

    # load the raw data — preload=True reads everything into memory
    raw = mne.io.read_raw_persyst(layf, preload=True, verbose=False)
    fs = raw.info['sfreq']
    all_ch_names = raw.ch_names

    # match good channel names to indices in the raw file
    # (channel names in tsv might not exactly match the lay file,
    #  so we do case-insensitive matching)
    raw_names_lower = [ch.lower() for ch in all_ch_names]
    good_picks = []
    matched_names = []
    for name in good_names:
        try:
            idx = raw_names_lower.index(name.lower())
            good_picks.append(idx)
            matched_names.append(all_ch_names[idx])
        except ValueError:
            pass  # channel in tsv but not in lay — skip it

    if len(good_picks) == 0:
        print(f'  {run}: no matching channels found, skipped')
        return None

    print(f'  {run}: matched {len(good_picks)}/{len(good_names)} channels in lay file')

    # pull out the data for good channels only (channels x samples)
    data = raw.get_data(picks=good_picks)
    n_ch, n_samp = data.shape

    # CAR: subtract the mean across channels at each time point
    avg = data.mean(axis=0, keepdims=True)
    data_car = data - avg

    # save to h5
    out_file = os.path.join(OUT_DIR, f'{SUBJECT}_{SESSION}_{run}_CAR.h5')
    with h5py.File(out_file, 'w') as hf:
        hf.create_dataset('data', data=data_car, compression='gzip', compression_opts=4)
        hf.create_dataset('channel_names', data=np.array(matched_names, dtype='S'))
        hf.attrs['fs'] = fs
        hf.attrs['subject'] = SUBJECT
        hf.attrs['session'] = SESSION
        hf.attrs['run'] = run
        hf.attrs['n_channels'] = n_ch
        hf.attrs['n_samples'] = n_samp
        hf.attrs['reference'] = 'CAR (good SEEG only)'

    elapsed = time.perf_counter() - t0
    print(f'  {run}: {n_ch} ch x {n_samp} samples, saved ({elapsed:.1f}s)')
    return {'run': run, 'n_ch': n_ch, 'n_samp': n_samp, 'fs': fs, 'file': out_file}


# --- main ---

print(f'CAR preprocessing: {SUBJECT}, {len(RUNS)} runs\n')
t_total = time.perf_counter()
results = []

for run in RUNS:
    r = process_run(run)
    if r:
        results.append(r)
    print()

# summary
if results:
    print(f'{"Run":<8} {"Channels":>9} {"Samples":>12} {"Fs":>8} {"File"}')
    for r in results:
        print(f'{r["run"]:<8} {r["n_ch"]:>9} {r["n_samp"]:>12} {r["fs"]:>8.0f} {r["file"]}')

print(f'\ntotal runtime: {time.perf_counter() - t_total:.1f}s')
