%% Open .lay File with fileReader
% fileReader internally calls lay_hdr_read and lay_data_read

%% Setup
clc; clear;

% Path to tools
toolsDir = 'U:\shared\users\ckugel\Misc_Functions';
addpath(toolsDir);

% Data file path
filePath = 'U:\shared\database\ieeg-UM\rawdata\sub-umich0018\ses-ieeg01\ieeg\sub-umich0018_ses-ieeg01_task-all_run-01_ieeg.lay';

% Change to data directory (so .lay can find .dat)
[dataDir, ~, ~] = fileparts(filePath);
cd(dataDir);

%% Open File
reader = fileReader(filePath);

%% Display Info
fprintf('═══════════════════════════════════════════════════\n');
fprintf('  FILE INFO\n');
fprintf('═══════════════════════════════════════════════════\n');
fprintf('  Channels: %d\n', reader.nChan);
fprintf('  Samples: %d\n', reader.nSamples);
fprintf('  Sampling Rate: %.1f Hz\n', reader.fs);
fprintf('  Duration: %.1f min\n', reader.nSamples/reader.fs/60);
fprintf('═══════════════════════════════════════════════════\n');

%% Load Data (first 10 seconds)
nSeconds = 10;
data = reader.getData(1, reader.fs * nSeconds);

fprintf('\n✓ Data loaded: %d channels × %d samples\n', size(data,1), size(data,2));