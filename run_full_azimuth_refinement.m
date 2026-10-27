function outputs = run_full_azimuth_refinement(cfg)
%RUN_FULL_AZIMUTH_REFINEMENT Test whether principal-plane shaping generalizes.
% This is an isolated numerical study, not an HFSS validation or a replacement
% for the predeclared geometry/algorithm scan.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1 || isempty(cfg), cfg = wg.default_config(root); end
if strcmp(char(cfg.resultsDir),fullfile(root,'results'))
    cfg.resultsDir = fullfile(root,'results','studies','full_azimuth_refinement');
end
paths = wg.prepare_results(cfg);
sourceDir = fullfile(root,'results','studies','twelve_mode_20261025','tables');
selected = readtable(fullfile(sourceDir,'selected_geometry.csv'));
assert(height(selected) == 1 && selected.FeedModeCount == 12, ...
    'Expected the archived 12-mode selected geometry.');
geometry = struct('apertureWidthM',selected.ApertureWidthMm*1e-3, ...
    'apertureHeightM',selected.ApertureHeightMm*1e-3, ...
    'flareLengthM',selected.FlareLengthMm*1e-3);
halfWidth = selected.HalfWidthDeg;
transition = selected.TransitionDeg;

modes = wg.propagating_modes(wg.enumerate_modes(cfg));
assert(height(modes) == 12, 'The feed must contain all 12 propagating modes.');
priorRows = readtable(fullfile(sourceDir,'modal_weights.csv'));
priorRows = priorRows(priorRows.HalfWidthDeg == halfWidth,:);
prior = complex(zeros(height(modes),1));
for idx = 1:height(modes)
    row = priorRows(string(priorRows.Mode) == string(modes.Name(idx)),:);
    assert(height(row) == 1, 'A selected modal weight is missing or duplicated.');
    prior(idx) = row.Amplitude*exp(1j*deg2rad(row.PhaseDeg));
end
prior = wg.normalize_weights(prior,1);

% Signed theta covers both halves of each meridian; 12 meridians sample
% azimuth every 15 degrees, including the original E and H planes.
theta = (-90:2:90).';
phi = [90,0,15:15:75,105:15:165];
basis = wg.build_pattern_basis(cfg,modes,theta,phi,geometry);
objective = @(x) wg.optimization_objective(x,basis,halfWidth,transition);
nModes = height(modes);
lb = [zeros(nModes,1);-pi*ones(nModes-1,1)];
ub = [ones(nModes,1); pi*ones(nModes-1,1)];
cfg.optimization.maxFunctionEvaluations = min(2000,cfg.optimization.maxFunctionEvaluations);
starts = {prior,wg.least_squares_start(basis,halfWidth,transition)};
solvers = cell(size(starts));
for idx = 1:numel(starts)
    solvers{idx} = wg.run_fmincon_solver(objective, ...
        wg.encode_weights(starts{idx}),lb,ub,cfg);
end
[~,winner] = min(cellfun(@(s)s.fval,solvers));
unpruned = wg.decode_variables(solvers{winner}.x,nModes);
pruneCfg = cfg;
pruneCfg.optimization.maxFunctionEvaluations = 1000;
pruned = wg.prune_and_refine(pruneCfg,basis,unpruned,halfWidth,transition,6);
refined = pruned.weights;
twoMode = refined;
twoMode(~ismember(string(modes.Name),["TE10","TE30"])) = 0;
twoMode = wg.normalize_weights(twoMode,1);

uvAxis = linspace(-0.8,0.8,181);
[u,v] = meshgrid(uvAxis,uvAxis);
radius = hypot(u,v);
thetaMap = asind(min(radius,1));
phiMap = atan2d(v,u);
thetaMap(radius > 1) = 0;
phiMap(radius > 1) = 0;
weights = {prior,refined,twoMode};
names = ["Previous E/H-plane solution","Azimuth-refined solution", ...
    "TE10+TE30 ablation"];
rows = table();
maps = cell(numel(weights),1);
for idx = 1:numel(weights)
    field = combinedField(cfg,modes,geometry,weights{idx});
    pattern = wg.farfield_fft(cfg,field,thetaMap,phiMap);
    maps{idx} = pattern.power;
    angular = wg.angular_spectrum_metrics(pattern.power,u,v,halfWidth,transition);
    cuts = wg.solution_metrics(basis,weights{idx},halfWidth,transition);
    objectiveValue = objective(wg.encode_weights(weights{idx}));
    rows = [rows;table(names(idx),objectiveValue,nnz(abs(weights{idx}) >= 1e-3), ...
        cuts.MainRippleDb,cuts.MaxSidelobeDb,angular.MainDiskRippleDb, ...
        angular.OutsideDiskDb,angular.BoresightRelativeDb, ...
        angular.PeakThetaDeg,angular.PeakPhiDeg, ...
        'VariableNames',{'Design','Objective','ActiveModes', ...
        'WorstMeridianRippleDb','WorstMeridianOutsideDb','MainDiskRippleDb', ...
        'OutsideDiskDb','BoresightRelativeDb','PeakThetaDeg','PeakPhiDeg'})]; %#ok<AGROW>
end
writetable(rows,fullfile(paths.tables,'azimuth_refinement_metrics.csv'));
weightsTable = table(string(modes.Name),abs(prior),rad2deg(angle(prior)), ...
    abs(refined),rad2deg(angle(refined)), ...
    'VariableNames',{'Mode','PriorAmplitude','PriorPhaseDeg', ...
    'RefinedAmplitude','RefinedPhaseDeg'});
writetable(weightsTable,fullfile(paths.tables,'azimuth_refinement_weights.csv'));
save(fullfile(paths.data,'azimuth_refinement.mat'),'geometry','modes','prior', ...
    'refined','twoMode','rows','solvers','pruned','theta','phi');

fig = figure('Visible','off','Color','w','Position',[100 100 1400 640]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
for idx = 1:2
    nexttile;
    power = maps{idx};
    power(radius > 1) = NaN;
    imageDb = 10*log10(max(power/max(power(:),[],'omitnan'),1e-4));
    imagesc(uvAxis,uvAxis,imageDb); axis xy equal tight;
    colormap(parula); clim([-40 0]); hold on;
    t = linspace(0,2*pi,361);
    plot(sind(halfWidth)*cos(t),sind(halfWidth)*sin(t),'w--','LineWidth',1.4);
    plot(sind(halfWidth+transition)*cos(t), ...
        sind(halfWidth+transition)*sin(t),'w:','LineWidth',1.2);
    xlabel('u = sin(theta) cos(phi)'); ylabel('v = sin(theta) sin(phi)');
    title(sprintf('(%c) %s',char('a'+idx-1),names(idx)));
end
cb = colorbar; cb.Layout.Tile = 'east'; cb.Label.String = 'Normalized power (dB)';
wg.export_paper_figure(fig,fullfile(paths.figures,'azimuth_refinement'));
close(fig);
outputs.metrics = rows;
outputs.weights = weightsTable;
outputs.resultsDir = paths.root;
end

function field = combinedField(cfg,modes,geometry,weights)
field = [];
for idx = find(abs(weights) >= 1e-3).'
    component = wg.horn_aperture_fields(cfg,modes.Family(idx), ...
        modes.m(idx),modes.n(idx),geometry);
    if isempty(field)
        field = component;
        field.Ex = complex(zeros(size(component.Ex)));
        field.Ey = complex(zeros(size(component.Ey)));
    end
    field.Ex = field.Ex+weights(idx)*component.Ex;
    field.Ey = field.Ey+weights(idx)*component.Ey;
end
end
