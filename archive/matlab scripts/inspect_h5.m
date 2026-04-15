%% Inspect H5 File Structure
clc; clear;

h5file = 'U:\shared\database\ieeg-UM\derivatives\glap-h5\qHFO_v4.0_Staba\sub-umich0018_ses-ieeg01_task-all_run-01_glap-qHFO_v4.0_Staba.h5';

fprintf('═══════════════════════════════════════════════════\n');
fprintf('  H5 FILE STRUCTURE\n');
fprintf('═══════════════════════════════════════════════════\n');
fprintf('File: %s\n\n', h5file);

info = h5info(h5file);

function explore(info, prefix)
    if isfield(info, 'Groups')
        for i = 1:length(info.Groups)
            g = info.Groups(i);
            fprintf('%s[GROUP] %s\n', prefix, g.Name);
            explore(g, [prefix '  ']);
        end
    end
    if isfield(info, 'Datasets')
        for i = 1:length(info.Datasets)
            d = info.Datasets(i);
            sizeStr = strjoin(string(d.Dataspace.Size), ' x ');
            fprintf('%s[DATASET] %s  size=[%s]  type=%s\n', prefix, d.Name, sizeStr, d.Datatype.Type);
        end
    end
end

explore(info, '');

%% Read and display sample data from each dataset
fprintf('\n═══════════════════════════════════════════════════\n');
fprintf('  SAMPLE DATA\n');
fprintf('═══════════════════════════════════════════════════\n\n');

function read_all_datasets(info, h5file)
    if isfield(info, 'Groups')
        for i = 1:length(info.Groups)
            read_all_datasets(info.Groups(i), h5file);
        end
    end
    if isfield(info, 'Datasets')
        for i = 1:length(info.Datasets)
            d = info.Datasets(i);
            fullpath = [info.Name '/' d.Name];
            if startsWith(fullpath, '//')
                fullpath = fullpath(2:end);
            end
            fprintf('--- %s ---\n', fullpath);
            try
                data = h5read(h5file, fullpath);
                if iscell(data)
                    fprintf('  Cell array, first 5 entries:\n');
                    for j = 1:min(5, numel(data))
                        fprintf('    [%d] %s\n', j, string(data{j}));
                    end
                    fprintf('  Total: %d entries\n', numel(data));
                elseif isnumeric(data)
                    fprintf('  Size: %s, Range: [%.6f, %.6f]\n', mat2str(size(data)), min(data(:)), max(data(:)));
                    fprintf('  First 5 values: %s\n', mat2str(data(1:min(5,numel(data)))));
                else
                    fprintf('  Type: %s\n', class(data));
                    disp(data(1:min(5,numel(data))));
                end
            catch e
                fprintf('  Error reading: %s\n', e.message);
            end
            fprintf('\n');
        end
    end
end

read_all_datasets(info, h5file);

fprintf('═══════════════════════════════════════════════════\n');
fprintf('  DONE\n');
fprintf('═══════════════════════════════════════════════════\n');
