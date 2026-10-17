function cfg = default_config(projectRoot)
%DEFAULT_CONFIG Reproducible configuration for the waveguide study.

if nargin < 1 || strlength(string(projectRoot)) == 0
    packageDir = fileparts(mfilename('fullpath'));
    projectRoot = fileparts(fileparts(packageDir));
end

cfg.projectRoot = char(projectRoot);
cfg.resultsDir = fullfile(cfg.projectRoot, 'results');
cfg.c0 = 3.0e8;
cfg.mu0 = 4*pi*1e-7;
cfg.eps0 = 1/(cfg.mu0*cfg.c0^2);
cfg.frequencyHz = 30e9;
cfg.widthM = 20e-3;
cfg.heightM = 10e-3;
cfg.lengthM = 80e-3;
cfg.maxM = 6;
cfg.maxN = 4;
cfg.cutoffToleranceHz = 1e3;

cfg.grid.nx = 129;
cfg.grid.ny = 65;
cfg.grid.fftPadding = 8;
cfg.angles.cutDeg = linspace(-90, 90, 721);
cfg.angles.mapThetaDeg = linspace(0, 90, 91);
cfg.angles.mapPhiDeg = linspace(-180, 180, 181);

cfg.optimization.halfWidthsDeg = 5:2.5:25;
cfg.optimization.transitionDeg = 5;
cfg.optimization.seeds = 0:9;
cfg.optimization.maxFunctionEvaluations = 3000;
cfg.optimization.swarmSize = 30;
cfg.optimization.maxIterations = 80;
cfg.optimization.mainRippleLimitDb = 1;
cfg.optimization.sidelobeLimitDb = -12;
cfg.optimization.crossPolLimitDb = -15;
cfg.optimization.monteCarloTrials = 200;
cfg.optimization.amplitudeToleranceDb = 0.5;
cfg.optimization.phaseToleranceDeg = 5;
cfg.optimization.maxActiveModes = 6;
cfg.optimization.historyGrid = (0:50:3000).';

% Pyramidal-horn scan.  The modal set is always defined by the fixed
% 20 mm x 10 mm feed; the larger aperture is an adiabatic upper-bound
% model until the selected candidate is independently checked in HFSS.
cfg.geometry.type = "pyramidal_horn";
cfg.geometry.feedWidthM = cfg.widthM;
cfg.geometry.feedHeightM = cfg.heightM;
cfg.geometry.feedStraightLengthM = 40e-3;
cfg.geometry.apertureWidthsM = (40:10:80)*1e-3;
cfg.geometry.apertureHeightsM = (20:10:60)*1e-3;
cfg.geometry.flareLengthsM = (60:20:120)*1e-3;
cfg.geometry.maxHalfAngleDeg = 25;
cfg.geometry.includeAperturePhaseError = false;
cfg.geometry.primaryHalfWidthDeg = 20;
cfg.geometry.transitionWidthsDeg = [5 10 15 20];
cfg.geometry.coarseFunctionEvaluations = 120;
cfg.geometry.maxFunctionEvaluations = 1200;
cfg.geometry.pruneFunctionEvaluations = 800;
cfg.geometry.refineCandidateCount = 8;

cfg.validation.fftRmseLimit = 0.01;
cfg.validation.peakDirectionLimitDeg = 0.25;
cfg.validation.hfssPeakLimitDeg = 1;
cfg.validation.hfssHpbwRelativeLimit = 0.10;
cfg.validation.hfssRmseDbLimit = 2;
cfg.validation.runAntennaToolbox = true;
cfg.validation.runHfss = false;
end

