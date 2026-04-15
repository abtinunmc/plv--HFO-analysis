% Runner: execute plvhfo1 and capture console output to file
diary('C:\Users\aakhtari\Documents\MATLAB\plvhfo1_output.txt');
diary on
try
    run('C:\Users\aakhtari\Documents\MATLAB\plvhfo1.m');
catch ME
    fprintf('ERROR: %s\n', ME.message);
    for k = 1:length(ME.stack)
        fprintf('  at %s (line %d)\n', ME.stack(k).name, ME.stack(k).line);
    end
end
diary off
