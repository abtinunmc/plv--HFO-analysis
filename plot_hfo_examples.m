%% Plot qHFO examples across all 32 good SEEG channels
% This script visualizes complete HFO timeframes and confirms whether each
% channel has valid signal coverage across the entire HFO duration.

clc; close all;

fprintf('============================================================\n');
fprintf('  PLOT qHFO EXAMPLES (ALL 32 GOOD SEEG CHANNELS)\n');
fprintf('============================================================\n');

%% Paths
h5file = 'U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\sub-umich0018_ses-ieeg01_task-all_run-01_glap-qHFO_v4.0_Staba.h5';
layFile = 'U:\shared\database\ieeg-UM\rawdata\sub-umich0018\ses-ieeg01\ieeg\sub-umich0018_ses-ieeg01_task-all_run-01_ieeg.lay';
channelsTsv = 'U:\shared\database\ieeg-UM\rawdata\sub-umich0018\ses-ieeg01\ieeg\sub-umich0018_ses-ieeg01_task-all_run-01_channels.tsv';
validatedMat = 'C:\Users\aakhtari\Documents\MATLAB\step3_validated_qHFO.mat';
toolsDir = 'U:\shared\users\ckugel\Misc_Functions';
saveDir = 'C:\Users\aakhtari\Documents\MATLAB';

%% Load channel metadata
chTable = readtable(channelsTsv, 'FileType', 'text', 'Delimiter', '\t');
isSEEG = strcmp(chTable.type, 'SEEG');
isGood = strcmp(chTable.status, 'good');
goodSEEG_mask = isSEEG & isGood;
goodSEEG_idx = find(goodSEEG_mask);
goodSEEG_names = chTable.name(goodSEEG_mask);
nGoodCh = numel(goodSEEG_idx);

fprintf('Good SEEG channels: %d\n', nGoodCh);

%% Load qHFO and validTimes metadata
qhfo_start_time = h5read(h5file, '/qHFO/start_time');
qhfo_stop_time  = h5read(h5file, '/qHFO/stop_time');
qhfo_start_idx  = h5read(h5file, '/qHFO/startIdx');
qhfo_stop_idx   = h5read(h5file, '/qHFO/stopIdx');

vt_chan_idx   = h5read(h5file, '/validTimes/chanIdx');
vt_start_time = h5read(h5file, '/validTimes/start_time');
vt_stop_time  = h5read(h5file, '/validTimes/stop_time');

% Build valid interval lookup for the 32 good channels
goodIntervals = cell(nGoodCh, 1);
for i = 1:nGoodCh
    chIdx = goodSEEG_idx(i);
    m = (vt_chan_idx == chIdx);
    goodIntervals{i} = [vt_start_time(m), vt_stop_time(m)];
end

%% Load validated index list
S = load(validatedMat, 'validIdx', 'valid');
validIdx = S.validIdx;
validMask = S.valid;
rejectIdx = find(~validMask);

fprintf('Valid qHFO count: %d\n', numel(validIdx));
fprintf('Rejected qHFO count: %d\n', numel(rejectIdx));

%% Pick examples (3 valid + 1 rejected)
rng(7); % deterministic examples
nValidExamples = min(3, numel(validIdx));
pickValid = validIdx(randperm(numel(validIdx), nValidExamples));

if isempty(rejectIdx)
    pickReject = [];
else
    pickReject = rejectIdx(randperm(numel(rejectIdx), 1));
end

exampleIdx = [pickValid(:); pickReject(:)];
exampleType = [repmat({'VALID'}, numel(pickValid), 1); repmat({'REJECTED'}, numel(pickReject), 1)];

fprintf('Selected examples:\n');
for i = 1:numel(exampleIdx)
    fprintf('  %s qHFO #%d\n', exampleType{i}, exampleIdx(i));
end

%% Load iEEG reader
addpath(toolsDir);
reader = fileReader(layFile);
fs = reader.fs;

% 80-500 Hz band for visualizing HFO activity
[b, a] = butter(4, [80 500] / (fs / 2), 'bandpass');

%% Plot each example
padSec = 0.15; % context before/after HFO

for ex = 1:numel(exampleIdx)
    idx = exampleIdx(ex);
    label = exampleType{ex};

    hStartT = qhfo_start_time(idx);
    hStopT = qhfo_stop_time(idx);
    hStartS = double(qhfo_start_idx(idx));
    hStopS = double(qhfo_stop_idx(idx));

    segStart = max(1, floor(hStartS - padSec * fs));
    segStop = min(reader.nSamples, ceil(hStopS + padSec * fs));
    nSeg = segStop - segStart + 1;

    raw = reader.getData(segStart, segStop);
    raw32 = raw(goodSEEG_idx, :);
    bp32 = filtfilt(b, a, double(raw32)')';

    tAbs = ((segStart:segStop) - 1) / fs;
    tRel = tAbs - hStartT;

    % Build coverage vector per channel for this HFO
    covered = false(nGoodCh, 1);
    for c = 1:nGoodCh
        iv = goodIntervals{c};
        covered(c) = any(iv(:,1) <= hStartT & iv(:,2) >= hStopT);
    end

    % Stacked trace with normalized amplitude for readability
    sig = bp32;
    scale = median(std(sig, 0, 2));
    if scale == 0
        scale = 1;
    end
    sig = sig / scale;
    offset = 4;

    figure('Name', sprintf('%s qHFO #%d', label, idx), 'Position', [120 80 1400 860]);

    % Top: all 32 channels waveforms
    subplot(2,1,1);
    hold on;
    for c = 1:nGoodCh
        y = sig(c, :) + (nGoodCh - c) * offset;
        plot(tRel, y, 'k', 'LineWidth', 0.7);
    end
    yl = ylim;
    patch([0, hStopT - hStartT, hStopT - hStartT, 0], ...
          [yl(1), yl(1), yl(2), yl(2)], ...
          [1 0.85 0.2], 'FaceAlpha', 0.18, 'EdgeColor', 'none');
    uistack(findobj(gca, 'Type', 'Line'), 'top');
    % Keep default y ticks here to avoid rendering issues with dense stacks.
    xlabel('Time relative to HFO start (s)');
    ylabel('Good SEEG channels');
    grid on;
    title(sprintf('%s qHFO #%d | HFO duration = %.1f ms', ...
        label, idx, 1000 * (hStopT - hStartT)));

    % Bottom: per-channel good coverage for this HFO
    subplot(2,1,2);
    barh(double(covered), 'FaceColor', [0.2 0.6 0.2], 'EdgeColor', 'none');
    hold on;
    badCh = find(~covered);
    if ~isempty(badCh)
        barh(badCh, zeros(size(badCh)), 'FaceColor', [0.85 0.2 0.2], 'EdgeColor', 'none');
        scatter(zeros(size(badCh)), badCh, 70, [0.85 0.2 0.2], 'filled');
    end
    xlim([0 1.05]);
    yticks(1:nGoodCh);
    yticklabels(goodSEEG_names);
    xlabel('Coverage (1 = full HFO covered)');
    ylabel('Channels');
    grid on;
    title(sprintf('Full-duration good-signal check across all 32 channels | Covered: %d/%d', sum(covered), nGoodCh));

    sgtitle(sprintf('%s example: qHFO #%d (%.3f - %.3f sec)', label, idx, hStartT, hStopT), 'FontWeight', 'bold');

    outPng = fullfile(saveDir, sprintf('hfo_example_%s_%d.png', lower(label), idx));
    exportgraphics(gcf, outPng, 'Resolution', 160);
    fprintf('Saved figure: %s\n', outPng);
end

fprintf('\nDone. Generated %d example figures.\n', numel(exampleIdx));
