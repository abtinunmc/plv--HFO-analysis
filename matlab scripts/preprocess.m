% Step 3 - HFO validation across all runs
% Keeps only HFOs where the full duration has clean signal on every good SEEG channel.

subject = 'sub-umich0018';
session = 'ses-ieeg01';
runs    = {'run-01', 'run-02', 'run-03', 'run-04', 'run-05'};
raw_dir = sprintf('U:\\shared\\database\\ieeg-UM\\rawdata\\%s\\%s\\ieeg', subject, session);
h5_dir  = 'U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba';
out_dir = 'C:\Users\aakhtari\Documents\MATLAB';

fprintf('Processing %s, %d runs\n\n', subject, numel(runs));
t_total = tic;
summaries = struct('run', {}, 'n_hfo', {}, 'n_valid', {});

for r = 1:numel(runs)
    run = runs{r};
    fprintf('-- %s --\n', run);

    h5f  = fullfile(h5_dir,  sprintf('%s_%s_task-all_%s_glap-qHFO_v4.0_Staba.h5', subject, session, run));
    tsvf = fullfile(raw_dir, sprintf('%s_%s_task-all_%s_channels.tsv',             subject, session, run));

    if ~isfile(h5f) || ~isfile(tsvf)
        fprintf('  skipped (missing files)\n\n');
        continue
    end

    % read channels.tsv - pull out SEEG channels marked as good
    tbl        = readtable(tsvf, 'FileType', 'text', 'Delimiter', '\t');
    good_mask  = strcmp(tbl.type, 'SEEG') & strcmp(tbl.status, 'good');
    good_idx   = find(good_mask);
    good_names = tbl.name(good_mask);
    fprintf('  channels: %d good SEEG\n', numel(good_idx));

    % load HFO events and per-channel valid-signal windows from h5
    hfo_ch    = double(h5read(h5f, '/qHFO/chanIdx'));
    hfo_start = double(h5read(h5f, '/qHFO/start_time'));
    hfo_stop  = double(h5read(h5f, '/qHFO/stop_time'));
    vt_ch     = double(h5read(h5f, '/validTimes/chanIdx'));
    vt_start  = double(h5read(h5f, '/validTimes/start_time'));
    vt_stop   = double(h5read(h5f, '/validTimes/stop_time'));
    n_hfo     = numel(hfo_ch);
    fprintf('  data: %d HFOs, %d valid intervals\n', n_hfo, numel(vt_ch));

    % sort valid-time arrays by channel once, then slice per channel via binary search
    % avoids scanning the whole vt_ch array for every channel
    [vt_ch, ord] = sort(vt_ch);
    vt_start = vt_start(ord);
    vt_stop  = vt_stop(ord);

    % intersect valid windows across channels one by one.
    % after the loop, all_good = time ranges where every channel is simultaneously clean.
    all_good = [];
    for k = 1:numel(good_idx)
        ch = good_idx(k);
        lo = searchsorted_left(vt_ch, ch);
        hi = searchsorted_right(vt_ch, ch);
        if lo > hi
            all_good = zeros(0, 2);
            break
        end
        iv = sortrows([vt_start(lo:hi), vt_stop(lo:hi)], 1);
        if isempty(all_good)
            all_good = iv;
        else
            all_good = intersect_intervals(all_good, iv);
        end
        if isempty(all_good)
            break
        end
    end

    % check each HFO against all_good intervals using binary search.
    % discretize finds which interval bin each hfo_start falls into,
    % then we just check if that interval's stop covers hfo_stop.
    if isempty(all_good)
        valid = false(n_hfo, 1);
    else
        ag_max_stop = cummax(all_good(:, 2));
        edges = [-inf; all_good(:, 1); inf];
        bin   = discretize(hfo_start, edges) - 1;  % 0 = before first interval
        valid = bin > 0 & ag_max_stop(max(1, bin)) >= hfo_stop;
    end

    n_valid = sum(valid);
    fprintf('  result: %d/%d valid (%.1f%%)\n', n_valid, n_hfo, 100*n_valid/max(n_hfo,1));

    % save .mat
    out_file       = fullfile(out_dir, sprintf('step3_validated_qHFO_%s.mat', run));
    validIdx       = find(valid);
    validChanIdx   = hfo_ch(valid);
    validStartTime = hfo_start(valid);
    validStopTime  = hfo_stop(valid);
    nGoodCh        = numel(good_idx);
    nHFO           = n_hfo;
    nValid         = n_valid;
    qhfo_chanIdx   = hfo_ch;
    qhfo_startTime = hfo_start;
    qhfo_stopTime  = hfo_stop;

    save(out_file, 'valid', 'validIdx', 'validChanIdx', 'validStartTime', 'validStopTime', ...
        'good_idx', 'good_names', 'nGoodCh', 'nHFO', 'nValid', ...
        'qhfo_chanIdx', 'qhfo_startTime', 'qhfo_stopTime');
    fprintf('  saved: %s\n\n', out_file);

    summaries(end+1).run     = run;
    summaries(end).n_hfo     = n_hfo;
    summaries(end).n_valid   = n_valid;
end

% summary table
tot_h = sum([summaries.n_hfo]);
tot_v = sum([summaries.n_valid]);
fprintf('  %-8s %7s %7s %7s %6s\n', 'Run', 'Total', 'Valid', 'Rej', '%');
for s = summaries
    rej = s.n_hfo - s.n_valid;
    fprintf('  %-8s %7d %7d %7d %5.1f%%\n', s.run, s.n_hfo, s.n_valid, rej, 100*s.n_valid/max(s.n_hfo,1));
end
fprintf('  %-8s %7d %7d %7d %5.1f%%\n', 'total', tot_h, tot_v, tot_h-tot_v, 100*tot_v/max(tot_h,1));

% bar chart
if ~isempty(summaries)
    labels = {summaries.run};
    v    = [summaries.n_valid];
    rej  = [summaries.n_hfo] - v;
    pcts = 100 * v ./ max([summaries.n_hfo], 1);

    fig = figure('Visible', 'off');
    subplot(1, 2, 1)
    bar([v; rej]', 'stacked')
    xticklabels(labels); legend({'Valid', 'Rejected'}); ylabel('Count')
    title('Valid vs Rejected')

    subplot(1, 2, 2)
    bar(pcts)
    xticklabels(labels); ylabel('Valid %'); ylim([0 105])
    title('Validation Rate')

    sgtitle(sprintf('%s - qHFO validation', subject))
    saveas(fig, fullfile(out_dir, 'step3_all_runs_summary.png'))
    fprintf('\nplot saved\n');
end

fprintf('\ntotal runtime: %.2fs\n', toc(t_total));


% --- helpers ---

function out = intersect_intervals(A, B)
    % two-pointer merge - finds time ranges present in both A and B.
    % pre-allocates output to avoid growing on every iteration.
    n = size(A, 1) + size(B, 1);
    out = zeros(n, 2);
    cnt = 0;
    i = 1; j = 1;
    while i <= size(A, 1) && j <= size(B, 1)
        lo = max(A(i, 1), B(j, 1));
        hi = min(A(i, 2), B(j, 2));
        if lo < hi
            cnt = cnt + 1;
            out(cnt, :) = [lo, hi];
        end
        if A(i, 2) < B(j, 2)
            i = i + 1;
        else
            j = j + 1;
        end
    end
    out = out(1:cnt, :);
end

function idx = searchsorted_left(arr, val)
    % first index where arr >= val (arr must be sorted)
    lo = 1; hi = numel(arr) + 1;
    while lo < hi
        mid = floor((lo + hi) / 2);
        if arr(mid) < val, lo = mid + 1; else, hi = mid; end
    end
    idx = lo;
end

function idx = searchsorted_right(arr, val)
    % last index where arr <= val (arr must be sorted)
    lo = 0; hi = numel(arr);
    while lo < hi
        mid = ceil((lo + hi) / 2);
        if arr(mid) > val, hi = mid - 1; else, lo = mid; end
    end
    idx = lo;
end
