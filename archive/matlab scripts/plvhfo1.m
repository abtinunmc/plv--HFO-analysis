%% Step 3: HFO Validation — Filter qHFOs Based on Good Signal Across All Channels
% Keeps a qHFO only if ALL 32 good SEEG channels have clean signal
% during the entire HFO time window.

clc; clear; close all;

fprintf('═══════════════════════════════════════════════════════════\n');
fprintf('  STEP 3: qHFO VALIDATION (Good Signal Check)\n');
fprintf('═══════════════════════════════════════════════════════════\n\n');

%% ── Paths ──
h5file = 'U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\sub-umich0018_ses-ieeg01_task-all_run-01_glap-qHFO_v4.0_Staba.h5';
channelsTsv = 'U:\shared\database\ieeg-UM\rawdata\sub-umich0018\ses-ieeg01\ieeg\sub-umich0018_ses-ieeg01_task-all_run-01_channels.tsv';

useDemoData = false;
if exist(h5file, 'file') ~= 2 || exist(channelsTsv, 'file') ~= 2
    useDemoData = true;
    fprintf('  [DEMO MODE] Real files not found. Using synthetic data.\n\n');
end

if ~useDemoData
%% ── A: Identify 32 Good SEEG Channels ──
fprintf('[A] Reading channels.tsv...\n');
chTable = readtable(channelsTsv, 'FileType', 'text', 'Delimiter', '\t');

isSEEG = strcmp(chTable.type, 'SEEG');
isGood = strcmp(chTable.status, 'good');
goodSEEG_mask = isSEEG & isGood;
goodSEEG_idx = find(goodSEEG_mask);
goodSEEG_names = chTable.name(goodSEEG_mask);
nGoodCh = length(goodSEEG_idx);

fprintf('  Total channels in file: %d\n', height(chTable));
fprintf('  SEEG channels: %d\n', sum(isSEEG));
fprintf('  Good SEEG channels: %d\n', nGoodCh);
fprintf('  Channels: %s\n', strjoin(cellstr(goodSEEG_names'), ', '));

%% ── B: Load qHFO Events ──
fprintf('\n[B] Loading qHFO events from H5...\n');
qhfo_chanIdx   = h5read(h5file, '/qHFO/chanIdx');
qhfo_startTime = h5read(h5file, '/qHFO/start_time');
qhfo_stopTime  = h5read(h5file, '/qHFO/stop_time');
nHFO = length(qhfo_chanIdx);

fprintf('  Total qHFOs: %d\n', nHFO);
fprintf('  Time range: %.1f – %.1f sec (%.1f hours)\n', ...
    min(qhfo_startTime), max(qhfo_stopTime), ...
    (max(qhfo_stopTime) - min(qhfo_startTime)) / 3600);
fprintf('  Channels with HFOs: %d unique\n', length(unique(qhfo_chanIdx)));

%% ── C: Load validTimes (Good Signal Intervals) ──
fprintf('\n[C] Loading validTimes from H5...\n');
vt_chanIdx   = h5read(h5file, '/validTimes/chanIdx');
vt_startTime = h5read(h5file, '/validTimes/start_time');
vt_stopTime  = h5read(h5file, '/validTimes/stop_time');
nIntervals = length(vt_chanIdx);

fprintf('  Total valid intervals: %d\n', nIntervals);
fprintf('  Channels covered: %d unique\n', length(unique(vt_chanIdx)));
else
%% ── DEMO: Synthetic data (32 good SEEG, qHFOs, validTimes) ──
fprintf('[A] DEMO: Building synthetic channels (32 good SEEG)...\n');
nGoodCh = 32;
goodSEEG_idx = (1:nGoodCh)';
goodSEEG_names = arrayfun(@(i) sprintf('Ch%02d', i), 1:nGoodCh, 'UniformOutput', false)';
fprintf('  Good SEEG channels: %d\n', nGoodCh);

fprintf('\n[B] DEMO: Generating synthetic qHFO events...\n');
rng(42);
nHFO = 15000;
qhfo_chanIdx   = randi(nGoodCh, nHFO, 1);
tMax = 7200;  % 2 hours in sec
qhfo_dur = 0.05 + 0.05*rand(nHFO, 1);
qhfo_startTime = rand(nHFO, 1) * (tMax - 1);
qhfo_stopTime  = qhfo_startTime + qhfo_dur;
fprintf('  Total qHFOs: %d\n', nHFO);
fprintf('  Time range: %.1f – %.1f sec (%.1f hours)\n', ...
    min(qhfo_startTime), max(qhfo_stopTime), (max(qhfo_stopTime)-min(qhfo_startTime))/3600);

fprintf('\n[C] DEMO: Generating synthetic validTimes (good signal per channel)...\n');
fs = 500;  % sample rate
nIntervalsPerCh = 20;
vt_chanIdx = []; vt_startTime = []; vt_stopTime = [];
for ch = 1:nGoodCh
    st = sort(rand(nIntervalsPerCh, 1) * tMax * 0.8);
    dur = 50 + rand(nIntervalsPerCh, 1) * 100;
    en = min(st + dur, tMax);
    vt_chanIdx   = [vt_chanIdx; repmat(ch, nIntervalsPerCh, 1)];
    vt_startTime = [vt_startTime; st];
    vt_stopTime  = [vt_stopTime; en];
end
nIntervals = length(vt_chanIdx);
fprintf('  Total valid intervals: %d\n', nIntervals);
fprintf('  Channels covered: %d unique\n', length(unique(vt_chanIdx)));
end

%% ── D: Group validTimes by Good SEEG Channel ──
fprintf('\n[D] Building good-signal lookup per channel...\n');
goodIntervals = cell(nGoodCh, 1);
for i = 1:nGoodCh
    chIdx = goodSEEG_idx(i);
    mask = (vt_chanIdx == chIdx);
    goodIntervals{i} = [vt_startTime(mask), vt_stopTime(mask)];
end

intervalsPerCh = cellfun(@(x) size(x,1), goodIntervals);
fprintf('  Intervals per channel: min=%d, max=%d, mean=%.1f\n', ...
    min(intervalsPerCh), max(intervalsPerCh), mean(intervalsPerCh));

%% ── E (FAST): Intersection of All-Channel Good Intervals, Then Vectorized Check ──
% Step 1: Compute intervals where ALL 32 channels have good signal (intersection).
% Step 2: Keep HFO only if its full window [start, stop] is inside one of these.
fprintf('\n[E] FAST: Computing intersection of good-signal intervals (all %d channels)...\n', nGoodCh);
tic;
allGoodIntervals = goodIntervals{1};
for c = 2:nGoodCh
    allGoodIntervals = intersectTwoIntervalSets(allGoodIntervals, goodIntervals{c});
    if isempty(allGoodIntervals)
        break;
    end
end
t_intersect = toc;
fprintf('  Intersection: %d intervals in %.3f sec\n', size(allGoodIntervals, 1), t_intersect);

if isempty(allGoodIntervals)
    valid = false(nHFO, 1);
    fprintf('  No time where all channels are good → all HFOs rejected.\n');
else
    % Sort by start, compute cumulative max of stop (best coverage up to each index)
    allGoodIntervals = sortrows(allGoodIntervals, 1);
    allGoodStart = allGoodIntervals(:, 1);
    allGoodStop  = allGoodIntervals(:, 2);
    maxStopUntil = cummax(allGoodStop);
    nAllGood = length(allGoodStart);

    % Validate: HFO valid iff [hStart, hStop] contained in some interval (a<=hStart, b>=hStop)
    % For sorted starts: last index with start<=hStart is idx; then need maxStopUntil(idx)>=hStop
    fprintf('  Validating %d qHFOs (vectorized chunks)...\n', nHFO);
    tic;
    chunkSize = 5000;
    valid = false(nHFO, 1);
    for chunkStart = 1:chunkSize:nHFO
        chunkEnd = min(chunkStart + chunkSize - 1, nHFO);
        hStart_chunk = qhfo_startTime(chunkStart:chunkEnd);
        hStop_chunk  = qhfo_stopTime(chunkStart:chunkEnd);
        % idx(i) = number of intervals with start <= hStart_chunk(i) = last valid index
        cmp = allGoodStart(:)' <= hStart_chunk(:);   % chunkLen x nAllGood
        idx_chunk = sum(cmp, 2);                      % chunkLen x 1 (can be 0)
        idx_safe = max(1, idx_chunk);                 % avoid index 0 in next line
        valid(chunkStart:chunkEnd) = (idx_chunk >= 1) & (maxStopUntil(idx_safe) >= hStop_chunk);
    end
    elapsed = toc;
    fprintf('  Validation completed in %.2f seconds\n', elapsed);
end

%% ── F: Results ──
nValid = sum(valid);
nRejected = sum(~valid);

fprintf('\n═══════════════════════════════════════════════════════════\n');
fprintf('  RESULTS\n');
fprintf('═══════════════════════════════════════════════════════════\n');
fprintf('  Total qHFOs:    %d\n', nHFO);
fprintf('  Valid qHFOs:    %d (%.1f%%)\n', nValid, 100*nValid/max(nHFO,1));
fprintf('  Rejected qHFOs: %d (%.1f%%)\n', nRejected, 100*nRejected/max(nHFO,1));

validIdx = find(valid);
validChanIdx   = qhfo_chanIdx(valid);
validStartTime = qhfo_startTime(valid);
validStopTime  = qhfo_stopTime(valid);

fprintf('\n  Valid HFOs per channel:\n');
for i = 1:nGoodCh
    chIdx = goodSEEG_idx(i);
    nChHFO = sum(validChanIdx == chIdx);
    if nChHFO > 0
        chName = goodSEEG_names{i};
        if isstring(chName), chName = char(chName); end
        fprintf('    %-4s (idx %2d): %d HFOs\n', chName, chIdx, nChHFO);
    end
end

%% ── G: Save Results ──
outputFile = fullfile(fileparts(h5file), '..', '..', '..', '..', ...
    'rawdata', 'sub-umich0018', 'ses-ieeg01', 'ieeg', 'step3_validated_qHFO.mat');
outputFile = 'C:\Users\aakhtari\Documents\MATLAB\step3_validated_qHFO.mat';

save(outputFile, 'validIdx', 'validChanIdx', 'validStartTime', 'validStopTime', ...
    'goodSEEG_idx', 'goodSEEG_names', 'nGoodCh', 'nHFO', 'nValid', ...
    'qhfo_chanIdx', 'qhfo_startTime', 'qhfo_stopTime', 'valid');

fprintf('\n  Saved: %s\n', outputFile);

%% ── H: Quick Visualization ──
figure('Name', 'Step 3: qHFO Validation', 'Position', [100 100 1200 500]);

subplot(1,3,1);
bar([nValid, nRejected], 'FaceColor', 'flat', 'CData', [0.2 0.7 0.3; 0.9 0.2 0.2]);
xticklabels({'Valid', 'Rejected'});
ylabel('Count');
title(sprintf('qHFO Validation\n%d / %d kept (%.0f%%)', nValid, nHFO, 100*nValid/max(nHFO,1)));

subplot(1,3,2);
chCounts = zeros(nGoodCh, 1);
for i = 1:nGoodCh
    chCounts(i) = sum(validChanIdx == goodSEEG_idx(i));
end
barh(chCounts);
yticks(1:nGoodCh);
yticklabels(cellstr(goodSEEG_names));
xlabel('Valid HFO Count');
title('Valid HFOs per Channel');
set(gca, 'FontSize', 7);

subplot(1,3,3);
if nValid > 0
    histogram(validStartTime / 3600, 50, 'FaceColor', [0.3 0.5 0.8]);
else
    bar(0, 0);
    set(gca, 'XLim', [0 1]);
end
xlabel('Time (hours)');
ylabel('HFO Count');
title('Valid HFO Distribution Over Time');

sgtitle('Step 3: qHFO Validation Results', 'FontWeight', 'bold');

%% ── I: Compare with filterByValidEpochs (optional, when H5 and external path exist) ──
runComparison = ~useDemoData && exist(h5file, 'file') == 2 && exist('U:\shared\users\ckugel\GC-HFOs\UMHS\Functions', 'dir') == 7;
if runComparison
% Run the same data through filterByValidEpochs.m and compare counts.
fprintf('\n═══════════════════════════════════════════════════════════\n');
fprintf('  COMPARISON: filterByValidEpochs (external)\n');
fprintf('═══════════════════════════════════════════════════════════\n');

vt_startIdx = h5read(h5file, '/validTimes/startIdx');
vt_stopIdx  = h5read(h5file, '/validTimes/stopIdx');
qhfo_startIdx = double(h5read(h5file, '/qHFO/startIdx'));
qhfo_stopIdx  = double(h5read(h5file, '/qHFO/stopIdx'));

epoch_startIdx = [];
for i = 1:nGoodCh
    chIdx = goodSEEG_idx(i);
    mask = (vt_chanIdx == chIdx);
    epoch_startIdx = [epoch_startIdx; vt_startIdx(mask)];
end
lenPerInterval = vt_stopIdx - vt_startIdx + 1;
epoch_nSamp = double(min(lenPerInterval));

addpath('U:\shared\users\ckugel\GC-HFOs\UMHS\Functions');
[filtStartIdx, filtStopIdx] = filterByValidEpochs(qhfo_startIdx, qhfo_stopIdx, epoch_startIdx, nGoodCh, epoch_nSamp);
nValid_filterBy = length(filtStartIdx);

fprintf('  Our validation (full HFO window):  %d kept, %d rejected\n', nValid, nRejected);
fprintf('  filterByValidEpochs (start only):  %d kept, %d rejected\n', nValid_filterBy, nHFO - nValid_filterBy);
if nValid == nValid_filterBy
    fprintf('  Same result? YES\n');
else
    fprintf('  Same result? NO\n');
end
ourValidStart = qhfo_startIdx(valid);
bothValid = ismember(filtStartIdx, ourValidStart);
onlyFilterBy = sum(~ismember(filtStartIdx, ourValidStart));
onlyOurs = sum(~ismember(ourValidStart, filtStartIdx));
fprintf('  In both: %d  |  Only filterByValidEpochs: %d  |  Only ours: %d\n', ...
    sum(bothValid), onlyFilterBy, onlyOurs);
else
fprintf('\n  [Section I skipped: demo mode or filterByValidEpochs path not available]\n');
end

fprintf('\n═══════════════════════════════════════════════════════════\n');
fprintf('  STEP 3 COMPLETE\n');
fprintf('═══════════════════════════════════════════════════════════\n');

%% ── Local: Intersect two interval sets ──
function out = intersectTwoIntervalSets(A, B)
% Intervals where both A and B have coverage. A, B are Nx2 [start, stop].
    if isempty(A) || isempty(B)
        out = zeros(0, 2);
        return;
    end
    % Events: (time, dA, dB). +1 = start, -1 = stop
    evA = [A(:,1), ones(size(A,1),1), zeros(size(A,1),1); ...
           A(:,2), -ones(size(A,1),1), zeros(size(A,1),1)];
    evB = [B(:,1), zeros(size(B,1),1), ones(size(B,1),1); ...
           B(:,2), zeros(size(B,1),1), -ones(size(B,1),1)];
    ev = [evA; evB];
    % Sort by time; for same time, process starts before ends (so "both" is correct)
    isEnd = (ev(:,2) + ev(:,3)) < 0;
    ev = sortrows([ev, isEnd], [1, 4]);
    ev = ev(:, 1:3);
    % Sweep
    countA = 0; countB = 0;
    inBoth = false;
    outStart = []; outStop = [];
    for k = 1:size(ev, 1)
        countA = countA + ev(k, 2);
        countB = countB + ev(k, 3);
        newInBoth = (countA > 0) && (countB > 0);
        if newInBoth && ~inBoth
            outStart = [outStart; ev(k, 1)];
        elseif ~newInBoth && inBoth
            outStop = [outStop; ev(k, 1)];
        end
        inBoth = newInBoth;
    end
    if isempty(outStart)
        out = zeros(0, 2);
    else
        out = [outStart, outStop];
    end
end
