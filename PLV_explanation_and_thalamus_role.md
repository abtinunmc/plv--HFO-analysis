# PLV (Phase Locking Value) in HFO/Epilepsy Research

## What is PLV and Why Do We Use It?

### The Big Picture

**PLV (Phase Locking Value) measures how consistently two brain regions "talk" to each other** during HFO events. It answers the question:

> "When an HFO happens, are these two brain regions oscillating together (synchronized) or independently?"

- PLV = 0: No synchronization (random phase relationship)
- PLV = 1: Perfect synchronization (identical phase relationship)

---

## Why PLV Matters for Epilepsy

### 1. Mapping the Epileptic Network

Epilepsy is not just one "bad spot" - it's a **network disease**. Seizures involve:
- **Seizure Onset Zone (SOZ)** - where seizures start
- **Propagation pathways** - how seizures spread
- **Remote nodes** - areas that get recruited

**PLV helps identify which regions are functionally connected during HFOs**, revealing the epileptic network structure.

### 2. Predicting Surgical Outcome

Research shows:
- **High PLV connectivity = important network hub**
- **Resecting highly connected hubs** (high PLV nodes) correlates with **good surgical outcome**
- If you leave a highly connected hub behind, seizures may persist

From the literature:
> "Resection of highly connected hubs computed from PLV for theta, alpha, and high-gamma bands was associated with good surgical outcome" - Scientific Reports

### 3. Distinguishing Pathological vs Normal HFOs

Not all HFOs are bad. PLV helps differentiate:
- **Pathological HFOs** - tend to be phase-locked to slow waves, highly synchronized
- **Physiological HFOs** - more random, less synchronized

> "Phase-locked HFOs during ictal EEG contribute to identification of epileptogenic brain tissues more accurately than HFOs alone" - Frontiers in Neurology

---

## The Role of the Thalamus in Epilepsy

### Thalamus as the "Relay Station"

The thalamus connects to almost every cortical region. In epilepsy:

- **86% of focal epilepsy patients** show thalamic involvement during seizures
- The **anterior nucleus of thalamus (ANT)** shows HFOs even interictally
- **High thalamic connectivity predicts POOR surgical outcome**

> "The ANT is a crucial node of the cortical–subcortical epileptic network during the interictal stage"

### Why Thalamus Matters for PLV Analysis

| Finding | Clinical Implication |
|---------|---------------------|
| High PLV between cortex and thalamus | Seizures may spread through thalamic relay |
| Thalamus synchronized with SOZ | May need neuromodulation (DBS) not just resection |
| Low thalamic PLV | Focal epilepsy, better surgical candidate |

> "Estimation of thalamic involvement in seizure propagation may be valuable before embarking on surgical resection and provide guidance for neuromodulation strategies"

### Thalamic Nuclei in Epilepsy

- **Anterior Nucleus (ANT)**: Target for DBS therapy, involved in temporal lobe epilepsy networks
- **Centromedian (CM)**: Role in generalized seizures
- **Pulvinar (PuM)**: Connects to multiple cortical areas, modulates cortico-cortical networks

---

## How PLV Helps Answer Clinical Questions

| Question | How PLV Answers It |
|----------|-------------------|
| Where is the epileptic network? | Regions with high mutual PLV form the network |
| Which node is most important? | Highest average PLV = network hub |
| Will surgery work? | Resecting high-PLV hubs → better outcome |
| Is thalamus involved? | High thalamo-cortical PLV = subcortical spread |
| Should we consider DBS? | If thalamus is highly connected, DBS may help |

---

## Application to Patient sub-umich0018

### Clinical Information
- **Pathology**: Cortical dysplasia (CD)
- **Resection location**: Left frontal cingulate
- **Outcome**: Engel Ib (seizure-free, good outcome)
- **Electrodes**: AL, BD, CD, DD (no thalamic electrodes)

### PLV Findings
- Strong connectivity within left hemisphere (AL ↔ DD): PLV ~0.98-0.99
- SOZ (BD) is moderately connected but not the most connected hub
- Cross-hemisphere (Left ↔ Right) connectivity is lower

### Interpretation
- Successful resection suggests the epileptic network was well-characterized
- High AL-DD PLV indicates these regions were part of the same functional network
- If thalamic electrodes had been placed, we could assess subcortical involvement

### What Thalamic Data Would Have Shown (Hypothetically)
- If thalamus was highly connected to SOZ → might indicate network spread beyond resectable area
- Low thalamic PLV → supports focal, resectable epilepsy (which matches the good outcome)

---

## PLV Computation Method

### Formula
```
PLV = |mean(exp(i * (phase1 - phase2)))|
```

### Steps in Our Pipeline
1. **Bandpass filter** (80-500 Hz) - isolate HFO band
2. **Hilbert transform** - extract instantaneous phase
3. **Phase difference** - compute for each channel pair
4. **PLV** - magnitude of mean unit vector

### Why Hilbert Transform?
- Converts real signal to complex "analytic signal"
- Allows extraction of instantaneous phase at every time point
- Requires narrowband (filtered) signal to be meaningful

---

## Considerations and Limitations

### Volume Conduction
- Neighboring electrodes on same shaft show artificially high PLV
- Solution: Use bipolar montage or imaginary PLV (iPLV)

### Sample Size
- 500 HFOs per run is adequate for stable PLV estimates
- More HFOs needed for detecting weak connections or temporal dynamics

### State Dependence
- PLV varies between interictal, pre-ictal, ictal, and post-ictal states
- State transitions may be most informative for outcome prediction

---

## References

1. [Assessing Epileptogenicity Using Phase-Locked HFOs](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2019.01132/full)
2. [Functional connectivity predicts surgical outcome](https://www.nature.com/articles/s41598-023-36551-0)
3. [The role of thalamus in focal epilepsy - SEEG insights](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2025.1608715/full)
4. [ANT plays a role in epileptic network](https://pmc.ncbi.nlm.nih.gov/articles/PMC9735375/)
5. [Thalamocortical circuits in epilepsy](https://pmc.ncbi.nlm.nih.gov/articles/PMC10192143/)
6. [Identifying SOZ using PLV and machine learning](https://www.sciencedirect.com/science/article/pii/S1059131117302923)
7. [Functional Connectivity from iEEG Predicts Surgical Outcome](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0077916)

---

*Document created: 2026-04-07*
*Project: HFO-GLISKE PLV Analysis*
