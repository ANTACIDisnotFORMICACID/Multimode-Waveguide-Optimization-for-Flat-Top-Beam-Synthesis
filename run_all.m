function outputs = run_all(varargin)
%RUN_ALL Rebuild reproducible MATLAB results without deleting HFSS evidence.
%
%   RUN_ALL() runs tests, baseline generation, optimization, and numerical
%   validation. HFSS is separate because an AEDT solution and its exported
%   evidence cannot be reconstructed by the MATLAB workflow alone.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
parser = inputParser;
addParameter(parser,'RunHfss',false,@(x)islogical(x)&&isscalar(x));
addParameter(parser,'RunAntennaToolbox',true,@(x)islogical(x)&&isscalar(x));
parse(parser,varargin{:});
if parser.Results.RunHfss
    error('run_all:HFSSSeparate', [ ...
        'HFSS solve is not launched from run_all. Use the documented HFSS ' ...
        'workflow and import only a verified native export.']);
end

cfg = wg.default_config(root);
cfg.validation.runHfss = parser.Results.RunHfss;
cfg.validation.runAntennaToolbox = parser.Results.RunAntennaToolbox;
for folder = ["figures","tables","data"]
    generated = fullfile(cfg.resultsDir,folder);
    if isfolder(generated)
        rmdir(generated,'s');
    end
end

outputs.tests = run_tests();
outputs.baseline = run_baseline(cfg);
outputs.geometry = run_geometry_scan(cfg);
outputs.optimization = run_optimization(cfg);

outputs.hfssExitCode = NaN;
outputs.hfssLog = 'HFSS is separate; existing solver evidence is preserved.';
outputs.validation = run_validation(cfg);
save(fullfile(cfg.resultsDir,'data','run_all_outputs.mat'),'outputs','cfg');
end
