function outputs = run_all(varargin)
%RUN_ALL Rebuild all reproducible MATLAB results from an empty results tree.
%
%   RUN_ALL() runs tests, baseline generation, optimization, and numerical
%   validation. RUN_ALL('RunHfss',true) also invokes the PyAEDT workflow;
%   the HFSS script writes a BLOCKED status instead of fabricating results
%   when AEDT, PyAEDT, or a solver license is unavailable.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
parser = inputParser;
addParameter(parser,'RunHfss',true,@(x)islogical(x)&&isscalar(x));
addParameter(parser,'RunAntennaToolbox',true,@(x)islogical(x)&&isscalar(x));
parse(parser,varargin{:});

cfg = wg.default_config(root);
cfg.validation.runHfss = parser.Results.RunHfss;
cfg.validation.runAntennaToolbox = parser.Results.RunAntennaToolbox;
if isfolder(cfg.resultsDir)
    rmdir(cfg.resultsDir,'s');
end

outputs.tests = run_tests();
outputs.baseline = run_baseline(cfg);
outputs.geometry = run_geometry_scan(cfg);
outputs.optimization = run_optimization(cfg);

if cfg.validation.runHfss
    pythonExe = fullfile('D:','Miniconda3','python.exe');
    hfssScript = fullfile(root,'hfss','build_and_solve.py');
    command = sprintf('"%s" "%s" --project-root "%s" --solve', ...
        pythonExe,hfssScript,root);
    [outputs.hfssExitCode,outputs.hfssLog] = system(command);
else
    outputs.hfssExitCode = NaN;
    outputs.hfssLog = 'HFSS was not requested. Run run_all(''RunHfss'',true).';
end
outputs.validation = run_validation(cfg);
save(fullfile(cfg.resultsDir,'data','run_all_outputs.mat'),'outputs','cfg');
end
