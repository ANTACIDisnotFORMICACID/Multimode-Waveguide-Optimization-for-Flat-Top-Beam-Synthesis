function outputs = run_optimization(cfg,target)
%RUN_OPTIMIZATION Compare algorithms on the geometry selected by the scan.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1 || isempty(cfg), cfg = wg.default_config(root); end
if nargin < 2, target = struct(); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
modes = wg.propagating_modes(catalog);

geometryFile = fullfile(paths.data,'geometry_results.mat');
if isfield(target,'geometry')
    geometry = target.geometry;
elseif isfile(geometryFile)
    geometryData = load(geometryFile,'selected');
    geometry = geometryData.selected.geometry;
else
    geometry = [];
end
if isfield(target,'halfWidthsDeg')
    halfWidths = target.halfWidthsDeg;
else
    halfWidths = cfg.optimization.halfWidthsDeg;
end
if isfield(target,'transitionDeg')
    transition = target.transitionDeg;
elseif isfile(geometryFile)
    geometryData = load(geometryFile,'selected');
    transition = geometryData.selected.transitionDeg;
else
    transition = cfg.optimization.transitionDeg;
end

theta = cfg.angles.cutDeg(:);
basis = wg.build_pattern_basis(cfg,modes,theta,[90 0],geometry);
straightBasis = wg.build_pattern_basis(cfg,modes,theta,[90 0]);
nModes = height(modes);
lb = [zeros(nModes,1);-pi*ones(nModes-1,1)];
ub = [ones(nModes,1); pi*ones(nModes-1,1)];

runRows = table();
historyRows = table();
weightRows = table();
allSolutions = struct();
for widthIdx = 1:numel(halfWidths)
    halfWidth = halfWidths(widthIdx);
    objective = @(x) wg.optimization_objective(x,basis,halfWidth,transition);

    lsWeights = wg.least_squares_start(basis,halfWidth,transition);
    local = wg.run_fmincon_solver(objective,wg.encode_weights(lsWeights),lb,ub,cfg);
    localWeights = wg.decode_variables(local.x,nModes);
    localMetrics = wg.solution_metrics(basis,localWeights,halfWidth,transition);
    runRows = [runRows;makeRunRow(halfWidth,"LS+fmincon",-1,local,localMetrics)]; %#ok<AGROW>

    psoSolutions = cell(numel(cfg.optimization.seeds),1);
    hybridSolutions = cell(numel(cfg.optimization.seeds),1);
    for seedIdx = 1:numel(cfg.optimization.seeds)
        seed = cfg.optimization.seeds(seedIdx);
        pso = wg.run_pso_solver(objective,lb,ub,cfg,seed);
        psoWeights = wg.decode_variables(pso.x,nModes);
        psoMetrics = wg.solution_metrics(basis,psoWeights,halfWidth,transition);
        runRows = [runRows;makeRunRow(halfWidth,"particleswarm",seed,pso,psoMetrics)]; %#ok<AGROW>
        historyRows = [historyRows;makeHistoryRows(halfWidth,"particleswarm",seed,pso.history)]; %#ok<AGROW>
        psoSolutions{seedIdx} = pso;

        hybridCfg = cfg;
        hybridCfg.optimization.maxIterations = 20;
        globalStart = wg.run_pso_solver(objective,lb,ub,hybridCfg,seed);
        hybridCfg.optimization.maxFunctionEvaluations = max(50, ...
            cfg.optimization.maxFunctionEvaluations-globalStart.funcCount);
        refined = wg.run_fmincon_solver(objective,globalStart.x(:),lb,ub,hybridCfg);
        hybrid = refined;
        hybrid.funcCount = globalStart.funcCount+refined.funcCount;
        hybrid.elapsedSeconds = globalStart.elapsedSeconds+refined.elapsedSeconds;
        hybrid.history = [globalStart.history; ...
            [refined.history(:,1)+globalStart.funcCount,refined.history(:,2)]];
        if ~isempty(hybrid.history), hybrid.history(:,2) = cummin(hybrid.history(:,2)); end
        hybridWeights = wg.decode_variables(hybrid.x,nModes);
        hybridMetrics = wg.solution_metrics(basis,hybridWeights,halfWidth,transition);
        runRows = [runRows;makeRunRow(halfWidth,"PSO+fmincon",seed,hybrid,hybridMetrics)]; %#ok<AGROW>
        historyRows = [historyRows;makeHistoryRows(halfWidth,"PSO+fmincon",seed,hybrid.history)]; %#ok<AGROW>
        hybridSolutions{seedIdx} = hybrid;
    end

    hybridValues = cellfun(@(s)s.fval,hybridSolutions);
    [~,bestHybridIdx] = min(hybridValues);
    hybrid = hybridSolutions{bestHybridIdx};
    hybridWeights = wg.decode_variables(hybrid.x,nModes);
    candidates = {local,hybrid};
    candidateWeights = {localWeights,hybridWeights};
    [~,winner] = min([local.fval,hybrid.fval]);
    selectedSolver = candidates{winner};
    selectedWeights = candidateWeights{winner};

    refinementCfg = cfg;
    refinementCfg.optimization.maxFunctionEvaluations = min(1000,cfg.optimization.maxFunctionEvaluations);
    sparse = wg.prune_and_refine(refinementCfg,basis,selectedWeights,halfWidth,transition, ...
        cfg.optimization.maxActiveModes);
    selectedWeights = sparse.weights;
    selectedMetrics = sparse.metrics;
    selectedSolver.fval = objective(wg.encode_weights(selectedWeights));
    key = matlab.lang.makeValidName(sprintf('width_%g',halfWidth));
    allSolutions.(key).solver = selectedSolver;
    allSolutions.(key).weights = selectedWeights;
    allSolutions.(key).metrics = selectedMetrics;

    for modeIdx = 1:nModes
        weightRows = [weightRows;table(halfWidth,modes.Name(modeIdx),modes.Family(modeIdx), ...
            modes.m(modeIdx),modes.n(modeIdx),abs(selectedWeights(modeIdx)), ...
            rad2deg(angle(selectedWeights(modeIdx))),abs(selectedWeights(modeIdx)) >= 1e-3, ...
            'VariableNames',{'HalfWidthDeg','Mode','Family','m','n','Amplitude','PhaseDeg','Active'})]; %#ok<AGROW>
    end
end

writetable(runRows,fullfile(paths.tables,'optimization_runs.csv'));
writetable(historyRows,fullfile(paths.tables,'convergence_history.csv'));
writetable(weightRows,fullfile(paths.tables,'modal_weights.csv'));
paperMetrics = wg.make_paper_metrics(runRows,halfWidths);
writetable(paperMetrics,fullfile(paths.tables,'paper_metrics.csv'));

primaryHalfWidth = cfg.geometry.primaryHalfWidthDeg;
[~,primaryIndex] = min(abs(halfWidths-primaryHalfWidth));
primaryHalfWidth = halfWidths(primaryIndex);
selectedKey = string(matlab.lang.makeValidName(sprintf('width_%g',primaryHalfWidth)));
selectedWeights = allSolutions.(selectedKey).weights;
selectedMetrics = allSolutions.(selectedKey).metrics;
if selectedMetrics.Passed
    promotionStatus = "PASS";
else
    promotionStatus = "PARETO_ONLY_NO_TARGET_PASSED";
end
robustness = wg.monte_carlo_robustness(cfg,basis,selectedWeights,primaryHalfWidth,transition);

baselineWeights = zeros(height(modes),1); baselineWeights(1) = 1;
baselineMetrics = wg.solution_metrics(straightBasis,baselineWeights,primaryHalfWidth,transition);
rippleReductionPercent = 100*(baselineMetrics.MainRippleDb-selectedMetrics.MainRippleDb) ...
    /max(baselineMetrics.MainRippleDb,eps);
hpbwIncreasePercent = 100*(selectedMetrics.HPBWHDeg-baselineMetrics.HPBWHDeg) ...
    /max(baselineMetrics.HPBWHDeg,eps);
showcaseSummary = table(primaryHalfWidth,transition,baselineMetrics.MainRippleDb, ...
    selectedMetrics.MainRippleDb,rippleReductionPercent,baselineMetrics.HPBWHDeg, ...
    selectedMetrics.HPBWHDeg,hpbwIncreasePercent,selectedMetrics.MaxSidelobeDb, ...
    nnz(abs(selectedWeights)>=1e-3),string(promotionStatus), ...
    'VariableNames',{'HalfWidthDeg','TransitionDeg','BaselineWorstRippleDb', ...
    'ShapedWorstRippleDb','RippleReductionPercent','BaselineHPlaneHpbwDeg', ...
    'ShapedHPlaneHpbwDeg','HPlaneHpbwIncreasePercent','ShapedOutsideTransitionDb', ...
    'ActiveModeCount','HardTargetStatus'});
writetable(showcaseSummary,fullfile(paths.tables,'showcase_summary.csv'));

save(fullfile(paths.data,'optimization_results.mat'),'basis','straightBasis','geometry','modes', ...
    'allSolutions','selectedKey','selectedWeights','selectedMetrics','robustness','transition');
fid = fopen(fullfile(paths.tables,'optimization_status.txt'),'w');
fprintf(fid,'%s\nSelectedHalfWidthDeg=%g\nTransitionDeg=%g\nActiveModes=%d\nRobustnessPassed=%d\n', ...
    promotionStatus,primaryHalfWidth,transition,nnz(abs(selectedWeights)>=1e-3),robustness.Passed);
fclose(fid);

wg.make_optimization_figures(cfg,paths,basis,straightBasis,modes,allSolutions,selectedKey, ...
    transition,historyRows,paperMetrics);
wg.make_robustness_figure(cfg,paths,robustness,selectedMetrics);
outputs.runs = runRows;
outputs.convergenceHistory = historyRows;
outputs.paperMetrics = paperMetrics;
outputs.weights = weightRows;
outputs.selectedKey = selectedKey;
outputs.status = promotionStatus;
outputs.metrics = selectedMetrics;
outputs.robustness = robustness;
outputs.showcaseSummary = showcaseSummary;
outputs.geometry = geometry;
outputs.paths = paths;

    function row = makeRunRow(width,algorithm,seed,solver,metrics)
        row = table(width,string(algorithm),seed,solver.fval,solver.funcCount,solver.elapsedSeconds, ...
            solver.exitflag,metrics.MainRippleDb,metrics.MaxSidelobeDb,metrics.MainCrossPolDb,metrics.Passed, ...
            'VariableNames',{'HalfWidthDeg','Algorithm','Seed','Objective','FunctionEvaluations', ...
            'ElapsedSeconds','ExitFlag','MainRippleDb','MaxSidelobeDb','MainCrossPolDb','PatternGatesPassed'});
    end

    function rows = makeHistoryRows(width,algorithm,seed,history)
        if isempty(history)
            rows = table(); return;
        end
        [evaluations,uniqueIndex] = unique(history(:,1),'stable');
        values = cummin(history(uniqueIndex,2));
        rows = table(repmat(width,numel(evaluations),1),repmat(string(algorithm),numel(evaluations),1), ...
            repmat(seed,numel(evaluations),1),evaluations,values, ...
            'VariableNames',{'HalfWidthDeg','Algorithm','Seed','FunctionEvaluations','BestObjective'});
    end
end
