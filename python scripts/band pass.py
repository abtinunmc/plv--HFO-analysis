"""
Bandpass 80–500 Hz on CAR data. Reads from car_output (.lay + .dat).
Step 1: set paths/params and check everything is there.
"""

import os

# where the CAR .lay and .dat files live
CAR_INPUT_DIR = r"C:\Users\aakhtari\Documents\MATLAB\car_output"

# 80–500 Hz HFO band (we'll use zero-phase later)
LOW_HZ = 80
HIGH_HZ = 500
# 4 = steep enough to cut junk outside the band, still stable and standard for HFO
FILTER_ORDER = 10

# has to match the CAR filenames
SUBJECT = "sub-umich0018"
SESSION = "ses-ieeg01"
RUNS = ["run-01", "run-02", "run-03", "run-04", "run-05"]

CAR_LAY_SUFFIX = "_ieeg_CAR.lay"
CAR_DAT_SUFFIX = "_ieeg_CAR.dat"

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
print(f"  Filter: {LOW_HZ}–{HIGH_HZ} Hz, order {FILTER_ORDER}")
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

# Open the plot and wait for user before continuing
plot_path = r"C:\Users\aakhtari\Documents\MATLAB\plots\step2a_header_parsing_plot.png"
if os.path.isfile(plot_path):
    try:
        os.startfile(plot_path)
    except Exception:
        import subprocess
        subprocess.run(['start', '', plot_path], shell=True)
    input('\nPress Enter to continue...')



#Step 4: Check Filter Feasibility


import numpy as np
from scipy.signal import sosfreqz, ellip
import matplotlib.pyplot as plt


#%% Checks
nyquist = FS / 2
print(f"Filter: {LOW_HZ}-{HIGH_HZ} Hz, Order {FILTER_ORDER}, Fs={FS} Hz")
print(f"Nyquist: {HIGH_HZ} < {nyquist} Hz → {'✓' if HIGH_HZ < nyquist else '✗'}")
#use ellip filter for stability instead of butter
# Design filter
sos = ellip(FILTER_ORDER, 0.5, 65, [LOW_HZ, HIGH_HZ], btype='bandpass', fs=FS, output='sos')
print(f"SOS sections: {sos.shape[0]} → ✓")

# save and open so you see the plot
filter_plot_dir = r"C:\Users\aakhtari\Documents\MATLAB\plots"
os.makedirs(filter_plot_dir, exist_ok=True)
filter_plot_path = os.path.join(filter_plot_dir, "step4_filter_feasibility.png")
plt.savefig(filter_plot_path, dpi=150)
plt.close()

print(f"\n  Filter feasibility plot saved: {filter_plot_path}")
try:
    os.startfile(filter_plot_path)
except Exception:
    import subprocess
    subprocess.run(['start', '', filter_plot_path], shell=True)
input("Press Enter to continue after viewing the plot...")

print("\n✓ Filter feasible")


# ── Step 5: Load CAR .dat metadata (no filtering yet) ──

import numpy as np

dtype_map = {
    0: np.int16,
    1: np.int32,
    7: np.float64,
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