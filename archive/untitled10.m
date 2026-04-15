%% Step 2.2b: Detailed Bad Channel Inspection

%% Setup
clc; close all;
load('step2_1_workspace.mat');

fprintf('═══════════════════════════════════════════════════\n');
fprintf('  DETAILED CHANNEL INSPECTION\n');
fprintf('═══════════════════════════════════════════════════\n\n');

%% Compute Metrics
chan_var = var(data, 0, 2);
chan_std = std(data, 0, 2);
chan_range = range(data, 2);
chan_kurt = kurtosis(data')';
chan_mean = mean(data, 2);
C = corrcoef(data');
chan_corr = (sum(abs(C), 2) - 1) / (nChan - 1);  % mean corr excluding self

%% Display All Channels
T = table((1:nChan)', chan_mean, chan_std, chan_var, chan_range, chan_kurt, chan_corr, ...
    'VariableNames', {'Channel', 'Mean', 'Std', 'Variance', 'Range', 'Kurtosis', 'MeanCorr'});
disp(T);

%% Visual Inspection - All Channels
figure('Position', [100 100 1400 800]);

% Plot all channels (5 sec)
subplot(2,1,1);
t = (0:size(data,2)-1) / fs;
offset = 5 * median(chan_std);
for ch = 1:nChan
    plot(t(1:min(5*fs,end)), data(ch,1:min(5*fs,end)) + (nChan-ch)*offset, 'k');
    hold on;
end
xlabel('Time (sec)'); ylabel('Channel');
title('All Channels - 5 sec'); ylim([-offset, nChan*offset]);

% Metrics comparison
subplot(2,3,4);
bar(chan_std); xlabel('Channel'); ylabel('Std'); title('Standard Deviation');
yline(median(chan_std), 'r--', 'LineWidth', 2);

subplot(2,3,5);
bar(chan_kurt); xlabel('Channel'); ylabel('Kurtosis'); title('Kurtosis');
yline(3, 'r--', 'LineWidth', 2);  % normal = 3

subplot(2,3,6);
bar(chan_corr); xlabel('Channel'); ylabel('Mean Corr'); title('Mean Correlation');
yline(median(chan_corr), 'r--', 'LineWidth', 2);

sgtitle('Detailed Channel Inspection', 'FontWeight', 'bold');

%% Correlation Matrix
figure('Position', [100 100 800 700]);
imagesc(C); colorbar; axis square;
title('Channel Correlation Matrix');
xlabel('Channel'); ylabel('Channel');

%% Power Spectrum - All Channels
figure('Position', [100 100 1000 600]);
nfft = 2^nextpow2(fs);
[pxx, f] = pwelch(data', hanning(nfft), nfft/2, nfft, fs);
semilogy(f, pxx); xlim([0 500]);
xlabel('Frequency (Hz)'); ylabel('Power');
title('Power Spectrum - All Channels');
xline(60, 'r--', '60Hz'); xline(80, 'g--', 'HFO');

%% Flag Suspicious Channels
fprintf('\n═══════════════════════════════════════════════════\n');
fprintf('  SUSPICIOUS CHANNELS (manual review)\n');
fprintf('═══════════════════════════════════════════════════\n');

% More sensitive thresholds
thresh_std_low = prctile(chan_std, 5);
thresh_std_high = prctile(chan_std, 95);
thresh_kurt = prctile(abs(chan_kurt - 3), 95);
thresh_corr = prctile(chan_corr, 5);

suspicious_std_low = find(chan_std < thresh_std_low);
suspicious_std_high = find(chan_std > thresh_std_high);
suspicious_kurt = find(abs(chan_kurt - 3) > thresh_kurt);
suspicious_corr = find(chan_corr < thresh_corr);

fprintf('Low amplitude (bottom 5%%):  %s\n', mat2str(suspicious_std_low'));
fprintf('High amplitude (top 5%%):    %s\n', mat2str(suspicious_std_high'));
fprintf('Abnormal kurtosis (top 5%%): %s\n', mat2str(suspicious_kurt'));
fprintf('Low correlation (bottom 5%%): %s\n', mat2str(suspicious_corr'));

fprintf('\n→ Review these channels visually!\n');