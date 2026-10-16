function outputs = run_optimization(cfg)
%RUN_OPTIMIZATION Compare PSO, least-squares/fmincon, and hybrid synthesis.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
modes = wg.propagating_modes(catalog);
theta = cfg.angles.cutDeg(:);
basis = wg.build_pattern_basis(cfg, modes, theta, [90 0]); % E plane, H plane for TE10.
nModes = height(modes);
lb = [zeros(nModes,1); -pi*ones(nModes-1,1)];
ub = [ones(nModes,1); pi*ones(nModes-1,1)];

runRows = table();
weightRows = table();
allSolutions = struct();
for widthIdx = 1:numel(cfg.optimization.halfWidthsDeg)
    halfWidth = cfg.optimization.halfWidthsDeg(widthIdx);
    transition = cfg.optimization.transitionDeg;
    objective = @(x) wg.optimization_objective(x, basis, halfWidth, transition);

    lsWeights = wg.least_squares_start(basis, halfWidth, transition);
    x0 = wg.encode_weights(lsWeights);
    local = wg.run_fmincon_solver(objective, x0, lb, ub, cfg);
    localWeights = wg.decode_variables(local.x, nModes);
    localMetrics = wg.solution_metrics(basis, localWeights, halfWidth, transition);
    runRows = [runRows; makeRunRow(halfWidth,"LS+fmincon",-1,local,localMetrics)]; %#ok<AGROW>

    psoSolutions = cell(numel(cfg.optimization.seeds),1);
    hybridSolutions = cell(numel(cfg.optimization.seeds),1);
    for seedIdx = 1:numel(cfg.optimization.seeds)
        seed = cfg.optimization.seeds(seedIdx);
        pso = wg.run_pso_solver(objective, lb, ub, cfg, seed);
        psoWeights = wg.decode_variables(pso.x, nModes);
        psoMetrics = wg.solution_metrics(basis, psoWeights, halfWidth, transition);
        runRows = [runRows; makeRunRow(halfWidth,"particleswarm",seed,pso,psoMetrics)]; %#ok<AGROW>
        psoSolutions{seedIdx} = pso;

        % Give the hybrid a short global search, then spend only the
        % remaining common forward-evaluation budget on local refinement.
        hybridCfg = cfg;
        hybridCfg.optimization.maxIterations = 20;
        globalStart = wg.run_pso_solver(objective, lb, ub, hybridCfg, seed);
        hybridCfg.optimization.maxFunctionEvaluations = max(50, ...
            cfg.optimization.maxFunctionEvaluations-globalStart.funcCount);
        refined = wg.run_fmincon_solver(objective,globalStart.x(:),lb,ub,hybridCfg);
        hybrid = refined;
        hybrid.funcCount = globalStart.funcCount+refined.funcCount;
        hybrid.elapsedSeconds = globalStart.elapsedSeconds+refined.elapsedSeconds;
        hybrid.history = [globalStart.history; ...
            refined.history+[globalStart.history(end,1)+1,0]];
        hybridWeights = wg.decode_variables(hybrid.x,nModes);
        hybridMetrics = wg.solution_metrics(basis,hybridWeights,halfWidth,transition);
        runRows = [runRows; makeRunRow(halfWidth,"PSO+fmincon",seed,hybrid,hybridMetrics)]; %#ok<AGROW>
        hybridSolutions{seedIdx} = hybrid;
    end

    hybridValues = cellfun(@(s)s.fval,hybridSolutions);
    [~,bestHybridIdx] = min(hybridValues);
    hybrid = hybridSolutions{bestHybridIdx};
    hybridWeights = wg.decode_variables(hybrid.x,nModes);

    candidates = {local, hybrid};
    candidateWeights = {localWeights, hybridWeights};
    [~,winner] = min([local.fval,hybrid.fval]);
    selected = candidates{winner};
    selectedWeights = candidateWeights{winner};
    selectedMetrics = wg.solution_metrics(basis, selectedWeights, halfWidth, transition);
    key = matlab.lang.makeValidName(sprintf('width_%d',halfWidth));
    allSolutions.(key).solver = selected;
    allSolutions.(key).weights = selectedWeights;
    allSolutions.(key).metrics = selectedMetrics;
    allSolutions.(key).psoHistory = psoSolutions{bestHybridIdx}.history;

    for modeIdx = 1:nModes
        weightRows = [weightRows; table(halfWidth, modes.Name(modeIdx), modes.Family(modeIdx), ...
            modes.m(modeIdx), modes.n(modeIdx), abs(selectedWeights(modeIdx)), ...
            rad2deg(angle(selectedWeights(modeIdx))), ...
            'VariableNames',{'HalfWidthDeg','Mode','Family','m','n','Amplitude','PhaseDeg'})]; %#ok<AGROW>
    end
end

writetable(runRows, fullfile(paths.tables, 'optimization_runs.csv'));
writetable(weightRows, fullfile(paths.tables, 'modal_weights.csv'));

comparisonRows = table();
for halfWidth = cfg.optimization.halfWidthsDeg
    psoMask = runRows.HalfWidthDeg == halfWidth & runRows.Algorithm == "particleswarm";
    hybridMask = runRows.HalfWidthDeg == halfWidth & runRows.Algorithm == "PSO+fmincon";
    psoObjective = median(runRows.Objective(psoMask));
    hybridObjective = median(runRows.Objective(hybridMask));
    psoEvaluations = median(runRows.FunctionEvaluations(psoMask));
    hybridEvaluations = median(runRows.FunctionEvaluations(hybridMask));
    objectiveImprovement = (psoObjective-hybridObjective)/psoObjective;
    objectiveDifference = abs(hybridObjective-psoObjective)/psoObjective;
    evaluationReduction = (psoEvaluations-hybridEvaluations)/psoEvaluations;
    passed = objectiveImprovement >= 0.20 || ...
        (objectiveDifference <= 0.05 && evaluationReduction >= 0.50);
    comparisonRows = [comparisonRows; table(halfWidth,psoObjective,hybridObjective, ...
        psoEvaluations,hybridEvaluations,objectiveImprovement,evaluationReduction,passed, ...
        'VariableNames',{'HalfWidthDeg','PsoMedianObjective','HybridMedianObjective', ...
        'PsoMedianEvaluations','HybridMedianEvaluations','ObjectiveImprovementFraction', ...
        'EvaluationReductionFraction','AlgorithmGatePassed'})]; %#ok<AGROW>
end
writetable(comparisonRows,fullfile(paths.tables,'algorithm_comparison.csv'));

paretoMask = false(height(runRows),1);
for idx = 1:height(runRows)
    dominated = runRows.MainRippleDb <= runRows.MainRippleDb(idx) & ...
        runRows.MaxSidelobeDb <= runRows.MaxSidelobeDb(idx) & ...
        (runRows.MainRippleDb < runRows.MainRippleDb(idx) | ...
        runRows.MaxSidelobeDb < runRows.MaxSidelobeDb(idx));
    paretoMask(idx) = ~any(dominated);
end
paretoRows = sortrows(runRows(paretoMask,:),{'MainRippleDb','MaxSidelobeDb'});
writetable(paretoRows,fullfile(paths.tables,'pareto_front.csv'));

% Select the narrowest solution that passes all physical pattern gates.
selectedKey = "";
for halfWidth = cfg.optimization.halfWidthsDeg
    key = matlab.lang.makeValidName(sprintf('width_%d',halfWidth));
    if allSolutions.(key).metrics.Passed
        selectedKey = string(key);
        break;
    end
end
if selectedKey == ""
    objectiveValues = arrayfun(@(w) allSolutions.(matlab.lang.makeValidName(sprintf('width_%d',w))).solver.fval, ...
        cfg.optimization.halfWidthsDeg);
    [~,idx] = min(objectiveValues);
    selectedKey = string(matlab.lang.makeValidName(sprintf('width_%d',cfg.optimization.halfWidthsDeg(idx))));
    promotionStatus = "PARETO_ONLY_NO_TARGET_PASSED";
else
    promotionStatus = "PASS";
end
selectedHalfWidth = sscanf(selectedKey, 'width_%d');
selectedWeights = allSolutions.(selectedKey).weights;
selectedMetrics = allSolutions.(selectedKey).metrics;
robustness = wg.monte_carlo_robustness(cfg, basis, selectedWeights, selectedHalfWidth, cfg.optimization.transitionDeg);

save(fullfile(paths.data, 'optimization_results.mat'), 'basis','modes','allSolutions','selectedKey','selectedWeights','selectedMetrics','robustness');
fid = fopen(fullfile(paths.tables,'optimization_status.txt'),'w');
fprintf(fid, '%s\nSelectedHalfWidthDeg=%g\nRobustnessPassed=%d\n', promotionStatus, selectedHalfWidth, robustness.Passed);
fclose(fid);

makeOptimizationFigures(cfg, paths, basis, modes, allSolutions, selectedKey, robustness, comparisonRows,runRows,paretoRows);
outputs.runs = runRows;
outputs.weights = weightRows;
outputs.algorithmComparison = comparisonRows;
outputs.paretoFront = paretoRows;
outputs.selectedKey = selectedKey;
outputs.status = promotionStatus;
outputs.metrics = selectedMetrics;
outputs.robustness = robustness;
outputs.paths = paths;

    function row = makeRunRow(width, algorithm, seed, solver, metrics)
        row = table(width,string(algorithm),seed,solver.fval,solver.funcCount,solver.elapsedSeconds, ...
            solver.exitflag,metrics.MainRippleDb,metrics.MaxSidelobeDb,metrics.MainCrossPolDb,metrics.Passed, ...
            'VariableNames',{'HalfWidthDeg','Algorithm','Seed','Objective','FunctionEvaluations', ...
            'ElapsedSeconds','ExitFlag','MainRippleDb','MaxSidelobeDb','MainCrossPolDb','PatternGatesPassed'});
    end
end

function makeOptimizationFigures(cfg, paths, basis, modes, allSolutions, selectedKey, robustness, comparisonRows,runRows,paretoRows)
selected = allSolutions.(selectedKey);
halfWidth = sscanf(selectedKey, 'width_%d');
target = wg.target_pattern(basis.thetaDeg, halfWidth, cfg.optimization.transitionDeg);
baselineWeights = zeros(height(modes),1); baselineWeights(1) = 1;
baseline = wg.evaluate_weights(basis, baselineWeights);
optimized = selected.metrics.Result;

fig = figure('Visible','off','Color','w','Position',[100 100 1500 650]);
planeNames = ["E plane","H plane"];
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
for idx = 1:2
    nexttile; hold on;
    plot(basis.thetaDeg, 20*log10(max(target,1e-4)), 'k--','LineWidth',1.6,'DisplayName','Target');
    plot(basis.thetaDeg, baseline.powerDb(:,idx), 'Color',[0.5 0.5 0.5],'LineWidth',1.2,'DisplayName','TE10 baseline');
    plot(basis.thetaDeg, optimized.powerDb(:,idx), 'r-','LineWidth',2,'DisplayName','Optimized');
    xlim([-60 60]); ylim([-40 2]); grid on;
    xlabel('\theta (deg)'); ylabel('Normalized power (dB)'); title(planeNames(idx));
    legend('Location','southwest');
end
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures,'05_optimized_pattern.png'),'Resolution',200); close(fig);

fig = figure('Visible','off','Color','w','Position',[100 100 1450 650]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
fields = string(fieldnames(allSolutions));
for idx = 1:numel(fields)
    s = allSolutions.(fields(idx));
    if ~isempty(s.solver.history)
        semilogy(s.solver.history(:,1),s.solver.history(:,2),'LineWidth',1.5,'DisplayName',replace(fields(idx),'_',' '));
    end
end
grid on; xlabel('Iteration'); ylabel('Objective'); title('Selected solver convergence'); legend('Location','best');
nexttile;
modeAxis = categorical(modes.Name,modes.Name,'Ordinal',true);
stem(modeAxis,abs(selected.weights),'filled','LineWidth',1.3);
ylabel('Normalized modal amplitude'); title('Selected modal weights'); grid on;
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures,'06_convergence_and_weights.png'),'Resolution',200); close(fig);

fig = figure('Visible','off','Color','w','Position',[100 100 900 600]);
histogram(robustness.SidelobeDb-selected.metrics.MaxSidelobeDb,25);
xline(3,'r--','3 dB gate','LineWidth',1.5); grid on;
xlabel('Sidelobe degradation (dB)'); ylabel('Trials');
title(sprintf('Monte Carlo robustness: amplitude +/-%.1f dB, phase +/-%.1f deg', ...
    cfg.optimization.amplitudeToleranceDb,cfg.optimization.phaseToleranceDeg));
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures,'07_monte_carlo_robustness.png'),'Resolution',200); close(fig);

fig = figure('Visible','off','Color','w','Position',[100 100 1450 900]);
tiledlayout(2,2,'TileSpacing','compact','Padding','compact');
nexttile;
bar(comparisonRows.HalfWidthDeg,[comparisonRows.PsoMedianObjective,comparisonRows.HybridMedianObjective]);
grid on; xlabel('Flat-top half-width (deg)'); ylabel('Median objective');
legend('particleswarm','PSO + fmincon','Location','best'); title('Ten-seed objective comparison');
nexttile;
bar(comparisonRows.HalfWidthDeg,[comparisonRows.PsoMedianEvaluations,comparisonRows.HybridMedianEvaluations]);
grid on; xlabel('Flat-top half-width (deg)'); ylabel('Forward evaluations');
legend('particleswarm','PSO + fmincon','Location','best'); title('Common-budget compute comparison');
nexttile;
modeAxis = categorical(modes.Name,modes.Name,'Ordinal',true);
stem(modeAxis,abs(selected.weights),'filled','LineWidth',1.3);
grid on; ylabel('Normalized amplitude'); title('Final modal amplitudes');
nexttile;
phaseDegrees = rad2deg(angle(selected.weights));
phaseDegrees(abs(selected.weights) < 1e-4) = NaN;
stem(modeAxis,phaseDegrees,'filled','LineWidth',1.3);
grid on; ylabel('Phase (deg)'); title('Final modal phases');
wg.style_figure(fig);
exportgraphics(fig,fullfile(paths.figures,'08_algorithm_cost_and_modal_weights.png'),'Resolution',200); close(fig);

fig = figure('Visible','off','Color','w','Position',[100 100 950 700]);
hold on;
algorithmNames = ["LS+fmincon","particleswarm","PSO+fmincon"];
markers = {'s','o','^'};
for idx = 1:numel(algorithmNames)
    mask = runRows.Algorithm == algorithmNames(idx);
    scatter(runRows.MainRippleDb(mask),runRows.MaxSidelobeDb(mask),45, ...
        runRows.HalfWidthDeg(mask),markers{idx},'filled','DisplayName',algorithmNames(idx));
end
plot(paretoRows.MainRippleDb,paretoRows.MaxSidelobeDb,'k-','LineWidth',2,'DisplayName','Non-dominated front');
xline(cfg.optimization.mainRippleLimitDb,'k--','1 dB ripple gate','HandleVisibility','off');
yline(cfg.optimization.sidelobeLimitDb,'r--','-12 dB sidelobe gate','HandleVisibility','off');
grid on; colorbar; colormap turbo;
xlabel('Worst-plane main-region ripple (dB)');
ylabel('Worst-plane maximum outside transition (dB)');
title('Fixed-aperture feasibility and Pareto front');
legend('Location','best');
wg.style_figure(fig);
exportgraphics(fig,fullfile(paths.figures,'09_feasibility_pareto.png'),'Resolution',200); close(fig);
end

