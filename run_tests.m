function results = run_tests()
%RUN_TESTS Execute all numerical correctness gates.

root = fileparts(mfilename('fullpath'));
addpath(root, fullfile(root,'matlab'));
suite = testsuite(fullfile(root,'tests'),'IncludeSubfolders',true);
results = run(suite);
disp(table(results));
assert(all([results.Passed]), 'One or more numerical correctness gates failed.');
end
