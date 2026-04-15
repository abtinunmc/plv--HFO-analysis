%% Step 2.2: Bad Channel Detection

%% Setup
clc; close all;
load('step2_1_workspace.mat');

fprintf('═══════════════════════════════════════════════════\n');
fprintf('  STEP 2.2: BAD CHANNEL DETECTION\n');
fprintf('═══════════════════════════════════════════════════\n\n');

%% Compute Channel Metrics
chan_var = var(data, 0, 2);
chan_kurt = kurtosis(data')';
chan_corr = mean(abs(corrcoef(data')), 2);  % mean correlation with others

%% Detect Bad Channels
z_var = zscore(log(chan_var));
z_kurt = zscore(chan_kurt);
z_corr = zscore(chan_corr);

bad_flat = z_var < -3;              % too flat
bad_noisy = z_var > 3;              % too noisy
bad_kurt = abs(z_kurt) > 3;         % abnormal distribution
bad_uncorr = z_corr < -3;           % uncorrelated with others

bad_channels = bad_flat | bad_noisy | bad_kurt | bad_uncorr;
good_channels = ~bad_channels;

%% Report
fprintf('Total channels: %d\n', nChan);
fprintf('Bad channels:   %d (%.1f%%)\n', sum(bad_channels), 100*mean(bad_channels));
fprintf('  - Flat:        %d\n', sum(bad_flat));
fprintf('  - Noisy:       %d\n', sum(bad_noisy));
fprintf('  - Kurtosis:    %d\n', sum(bad_kurt));
fprintf('  - Uncorrelated:%d\n', sum(bad_uncorr));
fprintf('Good channels:  %d\n', sum(good_channels));

if any(bad_channels)
    fprintf('\nBad channel indices: %s\n', mat2str(find(bad_channels)'));
end

%% Visualize
figure('Position', [100 100 1200 600]);

subplot(2,3,1);
histogram(log(chan_var), 30);
xline(mean(log(chan_var)) + 3*std(log(chan_var)), 'r--', 'LineWidth', 2);
xline(mean(log(chan_var)) - 3*std(log(chan_var)), 'r--', 'LineWidth', 2);
xlabel('log(Variance)'); title('Variance Distribution');

subplot(2,3,2);
histogram(chan_kurt, 30);
xline(mean(chan_kurt) + 3*std(chan_kurt), 'r--', 'LineWidth', 2);
xline(mean(chan_kurt) - 3*std(chan_kurt), 'r--', 'LineWidth', 2);
xlabel('Kurtosis'); title('Kurtosis Distribution');

subplot(2,3,3);
histogram(chan_corr, 30);
xline(mean(chan_corr) - 3*std(chan_corr), 'r--', 'LineWidth', 2);
xlabel('Mean Correlation'); title('Correlation Distribution');

subplot(2,3,4);
bar([sum(bad_flat), sum(bad_noisy), sum(bad_kurt), sum(bad_uncorr)]);
xticklabels({'Flat', 'Noisy', 'Kurtosis', 'Uncorr'});
ylabel('Count'); title('Bad Channel Types');

subplot(2,3,[5 6]);
imagesc(bad_channels'); colormap([1 1 1; 1 0 0]);
xlabel('Channel'); title('Bad Channels (red)');
yticks([]); colorbar('Ticks', [0 1], 'TickLabels', {'Good', 'Bad'});

sgtitle('Step 2.2: Bad Channel Detection', 'FontWeight', 'bold');

%% Save
save('step2_2_workspace.mat', 'reader', 'fs', 'nChan', 'nSamples', 'data', ...
     'good_channels', 'bad_channels', 'chan_var', 'chan_kurt', 'chan_corr');
fprintf('\n✓ Saved: step2_2_workspace.mat\n');