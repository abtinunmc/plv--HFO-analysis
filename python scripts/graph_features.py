# Step 5: Graph-theoretic feature extraction from PLV matrices.
# For each HFO, computes 4 centrality measures per channel from the PLV matrix.
# Aggregates across HFOs using median and 75th percentile.
# Output: [N_channels x 8] feature matrix per subject.
#
# Usage: python graph_features.py sub-umich0025

import os
import sys
import csv
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.io import loadmat, savemat
from glob import glob

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
assert len(sys.argv) == 2, "Usage: python graph_features.py sub-umichXXXX"
SUBJECT = sys.argv[1]
SESSION = 'ses-ieeg01'

SUBJECT_DIR = os.path.join(r'C:\Users\aakhtari\Documents\MATLAB\subjects', SUBJECT)
PLV_INPUT_DIR = os.path.join(SUBJECT_DIR, 'step4_plv')
OUTPUT_DIR    = os.path.join(SUBJECT_DIR, 'step5_features')
PLOTS_DIR     = os.path.join(SUBJECT_DIR, 'plots')

PERCENTILES = [50, 75]   # median and 75th percentile
CENTRALITY_NAMES = ['degree', 'betweenness', 'eigenvector', 'closeness']

# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------
assert os.path.isdir(SUBJECT_DIR),    f"Subject dir not found: {SUBJECT_DIR}"
assert os.path.isdir(PLV_INPUT_DIR),  f"Step4 PLV dir not found: {PLV_INPUT_DIR}"

plv_files = sorted(glob(os.path.join(PLV_INPUT_DIR, 'plv_run-*.mat')))
assert len(plv_files) > 0, f"No plv_run-*.mat files found in {PLV_INPUT_DIR}"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR,  exist_ok=True)

# ---------------------------------------------------------------------------
# Centrality computation for a single PLV matrix
# ---------------------------------------------------------------------------
def compute_centralities(plv_matrix):
    """
    Compute 4 centrality measures for one PLV matrix.

    Args:
        plv_matrix: (n_ch, n_ch) symmetric float array, values in [0,1],
                    diagonal = 1.0

    Returns:
        (n_ch, 4) array: [degree, betweenness, eigenvector, closeness]
    """
    n_ch = plv_matrix.shape[0]
    assert plv_matrix.shape == (n_ch, n_ch), \
        f"Expected square matrix, got {plv_matrix.shape}"
    assert np.allclose(plv_matrix, plv_matrix.T, atol=1e-6), \
        "PLV matrix is not symmetric"

    # Remove self-connections
    adj = plv_matrix.copy()
    np.fill_diagonal(adj, 0.0)

    # --- 1. Degree centrality (normalized weighted degree) ---
    degree = adj.sum(axis=1) / (n_ch - 1)

    # --- Build networkx graph ---
    # Edge weight = PLV (similarity). Distance = 1 - PLV for path-based measures.
    G = nx.Graph()
    G.add_nodes_from(range(n_ch))
    for i in range(n_ch):
        for j in range(i + 1, n_ch):
            w = float(adj[i, j])
            G.add_edge(i, j, weight=w, distance=max(1.0 - w, 1e-9))

    # --- 2. Betweenness centrality (distance-based) ---
    bc = nx.betweenness_centrality(G, weight='distance', normalized=True)
    betweenness = np.array([bc[i] for i in range(n_ch)])

    # --- 3. Eigenvector centrality (weight-based) ---
    try:
        ec = nx.eigenvector_centrality_numpy(G, weight='weight')
        eigenvector = np.array([ec[i] for i in range(n_ch)])
    except Exception:
        # Fallback: largest eigenvector of adjacency matrix
        _, vecs = np.linalg.eigh(adj)
        eigenvector = np.abs(vecs[:, -1])
        eigenvector = eigenvector / eigenvector.sum()

    # --- 4. Closeness centrality (distance-based) ---
    cc = nx.closeness_centrality(G, distance='distance')
    closeness = np.array([cc[i] for i in range(n_ch)])

    result = np.column_stack([degree, betweenness, eigenvector, closeness])
    assert result.shape == (n_ch, 4), \
        f"Expected ({n_ch}, 4) centrality array, got {result.shape}"
    return result

# ---------------------------------------------------------------------------
# Load all per-HFO PLV matrices across all runs
# ---------------------------------------------------------------------------
print(f"Step 5: Graph feature extraction for {SUBJECT}")
print(f"  Input: {PLV_INPUT_DIR}")
print(f"  Found {len(plv_files)} run files\n")

all_centralities = []   # list of (n_hfos, n_ch, 4) arrays
channel_names    = None
n_channels       = None

for mat_path in plv_files:
    run = os.path.basename(mat_path).replace('plv_', '').replace('.mat', '')
    mat = loadmat(mat_path)

    plv_3d = mat['plv_per_hfo']   # (n_hfos, n_ch, n_ch)
    ch_raw = mat['channel_names'].flatten()
    n_hfos, n_ch, n_ch2 = plv_3d.shape

    assert n_ch == n_ch2, f"{run}: PLV matrix is not square: {plv_3d.shape}"
    assert not np.isnan(plv_3d).any(), f"{run}: NaN values in PLV matrices"

    # Parse channel names (stored as nested arrays by scipy loadmat)
    names = [str(ch_raw[i].flat[0]) if hasattr(ch_raw[i], 'flat')
             else str(ch_raw[i]) for i in range(len(ch_raw))]

    if channel_names is None:
        channel_names = names
        n_channels    = n_ch
    else:
        assert names == channel_names, \
            f"{run}: channel names differ from first run\n  first: {channel_names}\n  this:  {names}"
        assert n_ch == n_channels, \
            f"{run}: n_channels {n_ch} != expected {n_channels}"

    # Compute centrality for each HFO in this run
    run_centralities = np.zeros((n_hfos, n_ch, 4))
    for h in range(n_hfos):
        run_centralities[h] = compute_centralities(plv_3d[h])

    all_centralities.append(run_centralities)
    print(f"  {run}: {n_hfos} HFOs processed")

# Stack all runs: (total_hfos, n_ch, 4)
all_centralities = np.concatenate(all_centralities, axis=0)
total_hfos = all_centralities.shape[0]
print(f"\n  Total HFOs: {total_hfos}, Channels: {n_channels}")

assert all_centralities.shape == (total_hfos, n_channels, 4), \
    f"Unexpected shape: {all_centralities.shape}"

# ---------------------------------------------------------------------------
# Aggregate: median and 75th percentile across HFOs, per channel per measure
# ---------------------------------------------------------------------------
# Result shape: (n_channels, n_features)  — len(CENTRALITY_NAMES) x len(PERCENTILES)
n_features = len(CENTRALITY_NAMES) * len(PERCENTILES)
feature_matrix = np.zeros((n_channels, n_features))
feature_labels = []

col = 0
for c_idx, c_name in enumerate(CENTRALITY_NAMES):
    for pct in PERCENTILES:
        values = all_centralities[:, :, c_idx]   # (total_hfos, n_channels)
        feature_matrix[:, col] = np.percentile(values, pct, axis=0)
        label = f"{c_name}_p{pct}"
        feature_labels.append(label)
        col += 1

assert feature_matrix.shape == (n_channels, n_features), \
    f"Expected ({n_channels}, {n_features}) feature matrix, got {feature_matrix.shape}"
assert len(feature_labels) == n_features, \
    f"Expected {n_features} feature labels, got {len(feature_labels)}"

print(f"\n  Feature matrix shape: {feature_matrix.shape}")
print(f"  Features: {feature_labels}")

# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------
# .mat
mat_out = os.path.join(OUTPUT_DIR, 'graph_features.mat')
savemat(mat_out, {
    'feature_matrix':   feature_matrix,       # (n_ch, 8)
    'feature_labels':   np.array(feature_labels, dtype=object),
    'channel_names':    np.array(channel_names, dtype=object),
    'all_centralities': all_centralities,      # (total_hfos, n_ch, 4)
    'centrality_names': np.array(CENTRALITY_NAMES, dtype=object),
    'n_hfos':           total_hfos,
    'n_channels':       n_channels,
    'subject':          SUBJECT,
    'session':          SESSION,
}, do_compression=True)
print(f"\n  Saved: {mat_out}")

# .csv
csv_out = os.path.join(OUTPUT_DIR, 'graph_features.csv')
with open(csv_out, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['channel'] + feature_labels)
    for i, ch in enumerate(channel_names):
        writer.writerow([ch] + [f'{v:.6f}' for v in feature_matrix[i]])
print(f"  Saved: {csv_out}")

# ---------------------------------------------------------------------------
# Plot: heatmap of feature matrix
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 4, figsize=(18, 6))
fig.suptitle(f'{SUBJECT} — Graph Features ({total_hfos} HFOs, {n_channels} channels)',
             fontsize=13)

for c_idx, c_name in enumerate(CENTRALITY_NAMES):
    ax = axes[c_idx]
    # Two columns: median (p50) and p75
    cols = [c_idx * 2, c_idx * 2 + 1]
    data = feature_matrix[:, cols]
    im = ax.imshow(data, aspect='auto', cmap='hot')
    ax.set_title(c_name, fontsize=11)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['median', 'p75'], fontsize=9)
    ax.set_yticks(range(n_channels))
    ax.set_yticklabels(channel_names, fontsize=7)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

plt.tight_layout()
plot_out = os.path.join(PLOTS_DIR, 'step5_graph_features.png')
plt.savefig(plot_out, dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved: {plot_out}")

print(f"\nStep 5 complete.")
print(f"  Feature matrix: {n_channels} channels x 8 features")
print(f"  Features: {feature_labels}")
