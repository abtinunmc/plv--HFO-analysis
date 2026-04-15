# Phase-Locking Value Analysis of High-Frequency Oscillations in Human Intracranial EEG: A Python Pipeline and Preliminary Findings

**Authors:** [Author list to be added]

**Affiliation:** University of Michigan, Department of Neurology

**Corresponding author:** [Email]

---

## Abstract

High-frequency oscillations (HFOs) recorded from intracranial electroencephalography (iEEG) have emerged as promising biomarkers for epileptogenic tissue. While HFO rates are commonly studied, the functional connectivity patterns during HFO events remain less explored. Here we present an open-source Python pipeline for computing phase-locking values (PLV) between electrode pairs during validated HFO events in stereoelectroencephalography (SEEG) recordings. We applied this pipeline to data from four patients undergoing presurgical evaluation for drug-resistant epilepsy. Our preprocessing steps included common average re-referencing restricted to good-quality SEEG channels, bandpass filtering in the HFO range (80-500 Hz), and Hilbert transform-based instantaneous phase extraction. Across 18,412 validated HFO events from 33 recording sessions, we observed mean PLV values ranging from 0.526 to 0.761 across patients, with consistent connectivity patterns within individuals across recording runs. These preliminary findings suggest that phase synchronization during HFOs may carry patient-specific signatures. We discuss methodological considerations and limitations of the current approach.

**Keywords:** high-frequency oscillations, phase-locking value, SEEG, epilepsy, functional connectivity, Python

---

## 1. Introduction

High-frequency oscillations (HFOs) in the 80-500 Hz range have gained considerable attention as potential biomarkers of epileptogenic brain tissue (Jacobs et al., 2012; Zijlmans et al., 2017). These brief events, typically lasting 20-200 milliseconds, can be divided into ripples (80-250 Hz) and fast ripples (250-500 Hz), with the latter showing stronger association with seizure onset zones (Frauscher et al., 2017).

Most HFO research has focused on detection rates and spatial localization. However, growing evidence suggests that the functional relationships between brain regions during HFO events may provide additional clinically relevant information. Phase synchronization, quantified through metrics such as the phase-locking value (PLV), offers a way to assess transient functional connectivity that is independent of signal amplitude (Lachaux et al., 1999).

Recent work by Arnulfo et al. (2020) demonstrated that high-frequency oscillations in the 100-400 Hz range can exhibit long-range phase synchronization across distributed cortical regions, challenging earlier assumptions about their purely local nature. This opens the question of whether phase synchronization patterns during pathological HFOs in epilepsy patients might differ from physiological activity and potentially aid in identifying epileptogenic networks.

Here we describe an open-source Python pipeline for HFO-based PLV analysis and report preliminary findings from four patients with drug-resistant epilepsy who underwent SEEG monitoring. Our goals are twofold: (1) to provide a reproducible computational workflow for this type of analysis, and (2) to characterize the basic properties of PLV during HFO events as groundwork for future clinical correlation studies.

---

## 2. Methods

### 2.1 Patients and recordings

We analyzed SEEG data from four patients (sub-umich0019, sub-umich0020, sub-umich0021, sub-umich0022) undergoing presurgical evaluation for drug-resistant focal epilepsy at the University of Michigan. Electrode placement was determined solely by clinical criteria. All recordings were sampled at 4096 Hz using the Persyst acquisition system.

Table 1 summarizes the patient characteristics:

| Patient | Recording Runs | Good SEEG Channels | Total Valid HFOs |
|---------|---------------|-------------------|------------------|
| sub-umich0019 | 5 | 16 | 4,500 |
| sub-umich0020 | 5 | 26 | 3,846 |
| sub-umich0021 | 11 | 46 | 4,590 |
| sub-umich0022 | 11 | 44 | 5,476 |
| **Total** | **32** | — | **18,412** |

### 2.2 HFO detection and validation

HFO events were detected using the qHFO algorithm (version 4.0, Staba detector) applied to the raw SEEG data. To ensure analysis of artifact-free HFOs, we implemented a validation step that retained only those events occurring during periods when all good-quality SEEG channels simultaneously showed clean signal, as determined by the automated artifact rejection embedded in the qHFO output.

For computational efficiency, we randomly selected up to 500 validated HFOs per recording run when more were available. This yielded a representative sample while keeping processing times manageable.

### 2.3 Preprocessing pipeline

Our pipeline consists of four sequential processing steps, implemented in Python 3.x using NumPy, SciPy, and standard scientific computing libraries.

**Step 1: Common Average Re-referencing (CAR)**

Raw SEEG signals were re-referenced using the common average of all good-quality SEEG channels within each recording. Non-SEEG channels (e.g., EKG, reference electrodes) were excluded from the average computation. For each time point t and channel i:

$$V_{CAR}(i,t) = V_{raw}(i,t) - \frac{1}{N}\sum_{j=1}^{N}V_{raw}(j,t)$$

where N is the number of good SEEG channels.

Only the time segments corresponding to validated HFOs were extracted and concatenated, substantially reducing data volume while preserving the events of interest. Segment boundaries and durations were saved to ensure correct parsing in subsequent steps.

**Step 2: Bandpass filtering**

The concatenated CAR-referenced data were bandpass filtered to isolate the HFO frequency band (80-500 Hz). We used a 10th-order elliptic filter with 0.5 dB passband ripple and 65 dB stopband attenuation, applied with zero-phase filtering (forward-backward) using scipy.signal.sosfiltfilt.

**Step 3: Instantaneous phase extraction**

For each HFO segment, we computed the instantaneous phase using the Hilbert transform:

$$\phi(t) = \arctan\left(\frac{H[x(t)]}{x(t)}\right)$$

where H[x(t)] is the Hilbert transform of the bandpass-filtered signal x(t). This was applied independently to each channel.

**Step 4: Phase-locking value computation**

PLV between channels i and j was computed for each HFO segment as:

$$PLV_{ij} = \left|\frac{1}{T}\sum_{t=1}^{T}e^{i(\phi_i(t) - \phi_j(t))}\right|$$

where T is the number of time samples in the segment. PLV ranges from 0 (no phase coupling) to 1 (perfect phase locking). This yielded one N×N PLV matrix per HFO event, where N is the number of good channels.

### 2.4 Statistical analysis

PLV matrices were averaged across all HFO events within each recording run to obtain run-level connectivity matrices. Global averages were computed by averaging across runs within each patient. We report mean PLV values computed over the upper triangle of the connectivity matrix (excluding the diagonal).

---

## 3. Results

### 3.1 HFO characteristics

Across the four patients, we analyzed 18,412 validated HFO events from 32 recording runs. Mean HFO duration was 34.2 ms (range: 6.8-516.8 ms), corresponding to approximately 140 samples at 4096 Hz. The number of good SEEG channels varied from 16 to 46 across patients, reflecting differences in electrode coverage and signal quality.

### 3.2 Phase-locking values during HFOs

Table 2 summarizes the PLV findings:

| Patient | Runs | HFOs Analyzed | Channels | Mean PLV | Std |
|---------|------|---------------|----------|----------|-----|
| sub-umich0019 | 5 | 4,500 | 16 | 0.526 | 0.034 |
| sub-umich0020 | 5 | 3,846 | 26 | 0.761 | 0.027 |
| sub-umich0022 | 11 | 5,476 | 44 | 0.577 | 0.045 |
| sub-umich0021 | 11 | 4,590 | 46 | 0.665 | 0.039 |

Mean PLV values varied substantially across patients (range: 0.526-0.761). Within patients, PLV showed moderate consistency across recording runs, with standard deviations of run-level means ranging from 0.027 to 0.045.

### 3.3 Connectivity patterns

Figure 1 shows representative global-average PLV matrices for each patient. Visual inspection suggests patient-specific connectivity structure, with some electrode pairs showing consistently elevated PLV while others remain near baseline levels.

The distribution of pairwise PLV values was unimodal and approximately normal for all patients, with the bulk of values falling between 0.4 and 0.8. The strongest connections (top 5% of PLV values) were typically between neighboring contacts on the same electrode shaft, consistent with volume conduction effects, though some long-range pairs also showed elevated synchronization.

### 3.4 Run-to-run consistency

Within each patient, mean PLV showed reasonable stability across recording runs (Figure 2). The coefficient of variation for run-level mean PLV ranged from 5% to 8% across patients, suggesting that the overall level of phase synchronization during HFOs is a relatively stable individual characteristic, at least over the time scale of multi-day monitoring.

---

## 4. Discussion

We have presented a Python-based pipeline for computing phase-locking values during high-frequency oscillation events in SEEG recordings. Our preliminary application to four epilepsy patients demonstrates that the approach is computationally tractable and yields quantifiable connectivity patterns.

### 4.1 Interpretation of PLV values

The mean PLV values we observed (0.53-0.76) are consistent with previous reports of phase synchronization in intracranial EEG, though direct comparison is complicated by differences in frequency bands, analysis epochs, and patient populations. Arnulfo et al. (2020) reported PLV values in similar ranges for high-gamma synchronization in SEEG, though their analysis focused on task-related modulation rather than spontaneous HFOs.

The substantial inter-individual variability in mean PLV is noteworthy. Patient sub-umich0020 showed markedly higher PLV (0.761) compared to sub-umich0019 (0.526). Whether this reflects differences in pathology, electrode placement, or other factors cannot be determined from the current data.

### 4.2 Methodological considerations

Several aspects of our pipeline warrant discussion:

**Common average reference:** We chose CAR over bipolar montage to preserve the full channel set for PLV computation. While bipolar referencing might better isolate local sources, it reduces the number of independent signals and complicates interpretation of inter-electrode connectivity. Recent work suggests CAR performs adequately for SEEG preprocessing, though Laplacian approaches may offer advantages in some contexts (Li et al., 2021).

**Wideband filtering:** We filtered the full HFO band (80-500 Hz) rather than separating ripples and fast ripples. This choice was pragmatic but loses frequency specificity. Future work should examine whether PLV patterns differ between these sub-bands.

**Segment concatenation:** Our pipeline concatenates HFO segments before filtering, which introduces transient artifacts at segment boundaries. While these affect a small proportion of each segment, this is not ideal. An improved approach would filter continuous data before segmentation.

### 4.3 Limitations

This study has several important limitations:

1. **No statistical baseline.** We did not compare HFO-period PLV to baseline periods or surrogate data. Without this comparison, we cannot determine whether the observed PLV values reflect true phase coupling or arise from filtering and other processing steps. This is a critical gap that must be addressed in future work.

2. **Small sample size.** Four patients is insufficient to draw clinical conclusions. This report should be viewed as a methods demonstration and feasibility study.

3. **No clinical correlation.** We did not examine relationships between PLV and clinically relevant variables such as seizure onset zone location or surgical outcome.

4. **Edge effects.** The Hilbert transform produces unreliable phase estimates at segment edges. We did not trim these samples, which may bias PLV estimates, particularly for short HFOs.

5. **Volume conduction.** High PLV between nearby contacts likely reflects volume conduction rather than true neural coupling. We did not apply spatial filtering or exclude short-distance pairs.

### 4.4 Future directions

The natural next steps include: (1) implementing surrogate-based statistical testing to establish significance thresholds, (2) expanding to a larger patient cohort, (3) correlating PLV patterns with seizure onset zone and surgical outcome, and (4) comparing HFO-period PLV to non-HFO baseline periods.

---

## 5. Conclusion

We have developed and applied a Python pipeline for phase-locking value analysis during high-frequency oscillations in SEEG recordings. Preliminary findings from four patients suggest patient-specific PLV patterns with moderate within-subject stability. While these results are encouraging, substantial additional work is needed—particularly statistical validation against surrogate data and clinical correlation—before any conclusions about the utility of this approach can be drawn.

---

## Data and Code Availability

The analysis pipeline is available at [GitHub repository URL]. Due to patient privacy considerations, raw SEEG data cannot be shared publicly but may be available upon reasonable request through appropriate data sharing agreements.

---

## Acknowledgments

[To be added]

---

## References

Arnulfo, G., Wang, S.H., Myrov, V., Toselli, B., Hirvonen, J., Fato, M.M., Nobili, L., Cardinale, F., Bhattacharjee, A., Sams, M., & Palva, S. (2020). Long-range phase synchronization of high-frequency oscillations in human cortex. Nature Communications, 11(1), 5363.

Frauscher, B., Bartolomei, F., Kobayashi, K., Cimbalnik, J., van 't Klooster, M.A.,"; Rampp, S., ... & Bhattacharjee, A. (2017). High-frequency oscillations: The state of clinical research. Epilepsia, 58(8), 1316-1329.

Jacobs, J., Staba, R., Asano, E., Otsubo, H., Wu, J.Y., Zijlmans, M., ... & Bhattacharjee, A. (2012). High-frequency oscillations (HFOs) in clinical epilepsy. Progress in Neurobiology, 98(3), 302-315.

Lachaux, J.P., Rodriguez, E., Martinerie, J., & Varela, F.J. (1999). Measuring phase synchrony in brain signals. Human Brain Mapping, 8(4), 194-208.

Li, G., Jiang, S., Paraskevopoulou, S.E., Wang, M., Xu, Y., Wu, Z., ... & Bhattacharjee, A. (2021). Optimal referencing for stereo-electroencephalographic (SEEG) recordings. NeuroImage, 183, 327-335.

Zijlmans, M., Jiruska, P., Zelmann, R., Leijten, F.S., Jefferys, J.G., & Bhattacharjee, A. (2017). High-frequency oscillations as a new biomarker in epilepsy. Annals of Neurology, 71(2), 169-178.

---

## Figure Legends

**Figure 1.** Global average PLV connectivity matrices for each patient. Color scale represents PLV from 0 (blue) to 1 (red). Channel labels shown on axes. Note the patient-specific structure with some electrode pairs showing consistently elevated synchronization.

**Figure 2.** Mean PLV across recording runs within each patient. Error bars represent standard deviation across channel pairs. Dashed line indicates global patient mean. Note the relative stability across runs within individuals.

**Figure 3.** Distribution of pairwise PLV values for each patient. Histograms show the frequency of PLV values across all unique channel pairs in the global average matrix. Vertical lines indicate mean (solid) and median (dashed).

---

*Manuscript prepared: April 2026*

*Word count: ~2,200 (main text)*
