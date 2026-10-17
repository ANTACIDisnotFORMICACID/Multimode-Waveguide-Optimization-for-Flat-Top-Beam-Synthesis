function outputs = run_geometry_scan(cfg)
%RUN_GEOMETRY_SCAN Select a sparse, fixed-feed pyramidal-horn aperture.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
modes = wg.propagating_modes(catalog);
theta = cfg.angles.cutDeg(:);
halfWidth = cfg.geometry.primaryHalfWidthDeg;

rows = table();
solutions = {};
geometryCounter = 0;
for apertureWidth = cfg.geometry.apertureWidthsM
    for apertureHeight = cfg.geometry.apertureHeightsM
        cachedBasis = [];
        coarseSolutionCache = cell(numel(cfg.geometry.transitionWidthsDeg),1);
        if ~cfg.geometry.includeAperturePhaseError
            cacheGeometry = struct('type',"pyramidal_horn", ...
                'apertureWidthM',apertureWidth, ...
                'apertureHeightM',apertureHeight, ...
                'flareLengthM',cfg.geometry.flareLengthsM(1));
            cachedBasis = wg.build_pattern_basis(cfg,modes,theta,[90 0],cacheGeometry);
        end
        for flareLength = cfg.geometry.flareLengthsM
            geometry = struct('type',"pyramidal_horn", ...
                'apertureWidthM',apertureWidth, ...
                'apertureHeightM',apertureHeight, ...
                'flareLengthM',flareLength);
            [angleX,angleY] = wg.horn_half_angles(cfg,geometry);
            if max(angleX,angleY) > cfg.geometry.maxHalfAngleDeg
                continue;
            end
            geometryCounter = geometryCounter+1;
            if mod(geometryCounter,10) == 0
                fprintf('Geometry scan: evaluated %d admissible geometries.\n',geometryCounter);
            end
            if isempty(cachedBasis)
                basis = wg.build_pattern_basis(cfg,modes,theta,[90 0],geometry);
            else
                basis = cachedBasis;
                basis.geometry = geometry;
            end
            nModes = height(modes);
            lb = [zeros(nModes,1);-pi*ones(nModes-1,1)];
            ub = [ones(nModes,1); pi*ones(nModes-1,1)];
            for transitionIdx = 1:numel(cfg.geometry.transitionWidthsDeg)
                transition = cfg.geometry.transitionWidthsDeg(transitionIdx);
                if ~cfg.geometry.includeAperturePhaseError && ...
                        ~isempty(coarseSolutionCache{transitionIdx})
                    cached = coarseSolutionCache{transitionIdx};
                    initialWeights = cached.weights;
                    metrics = cached.metrics;
                    finalObjective = cached.objective;
                    totalEvaluations = cached.functionEvaluations;
                else
                    localCfg = cfg;
                    localCfg.optimization.maxFunctionEvaluations = cfg.geometry.coarseFunctionEvaluations;
                    startWeights = wg.least_squares_start(basis,halfWidth,transition);
                    objective = @(x) wg.optimization_objective(x,basis,halfWidth,transition);
                    initial = wg.run_fmincon_solver(objective,wg.encode_weights(startWeights),lb,ub,localCfg);
                    initialWeights = wg.decode_variables(initial.x,nModes);
                    metrics = wg.solution_metrics(basis,initialWeights,halfWidth,transition);
                    finalObjective = objective(wg.encode_weights(initialWeights));
                    totalEvaluations = initial.funcCount;
                    if ~cfg.geometry.includeAperturePhaseError
                        coarseSolutionCache{transitionIdx} = struct( ...
                            'weights',initialWeights,'metrics',metrics, ...
                            'objective',finalObjective,'functionEvaluations',totalEvaluations);
                    end
                end
                activeCount = nnz(abs(initialWeights) >= 1e-3);
                row = table(apertureWidth*1e3,apertureHeight*1e3,flareLength*1e3, ...
                    angleX,angleY,halfWidth,transition,height(modes),activeCount, ...
                    finalObjective,totalEvaluations,metrics.MainRippleDb,metrics.MaxSidelobeDb, ...
                    metrics.MainCrossPolDb,metrics.Passed, ...
                    'VariableNames',{'ApertureWidthMm','ApertureHeightMm','FlareLengthMm', ...
                    'HalfAngleXDeg','HalfAngleYDeg','HalfWidthDeg','TransitionDeg', ...
                    'FeedModeCount','ActiveModeCount','Objective','FunctionEvaluations', ...
                    'MainRippleDb','MaxOutsideDb','MainCrossPolDb','PatternGatesPassed'});
                rows = [rows;row]; %#ok<AGROW>
                solutions{end+1,1} = struct('geometry',geometry,'basis',basis, ...
                    'weights',initialWeights,'metrics',metrics,'objective',finalObjective, ...
                    'transitionDeg',transition); %#ok<AGROW>
            end
        end
    end
end
assert(~isempty(rows),'No horn candidates satisfied the half-angle constraint.');

% Refine only the best coarse candidates.  This preserves the declared
% geometry grid while keeping run_all practical for reproducible use.
coarseViolation = max(rows.MainRippleDb-cfg.optimization.mainRippleLimitDb,0).^2 + ...
    max(rows.MaxOutsideDb-cfg.optimization.sidelobeLimitDb,0).^2 + ...
    max(rows.MainCrossPolDb-cfg.optimization.crossPolLimitDb,0).^2;
if cfg.geometry.includeAperturePhaseError
    candidateIndices = (1:height(rows)).';
else
    groupId = findgroups(rows(:,{'ApertureWidthMm','ApertureHeightMm','TransitionDeg'}));
    candidateIndices = splitapply(@(indices) indices(1),(1:height(rows)).',groupId);
end
coarseRanking = table(candidateIndices,coarseViolation(candidateIndices), ...
    rows.Objective(candidateIndices), ...
    rows.ApertureWidthMm(candidateIndices).*rows.ApertureHeightMm(candidateIndices), ...
    'VariableNames',{'SourceIndex','Violation','Objective','AreaMm2'});
coarseRanking = sortrows(coarseRanking,{'Violation','AreaMm2','Objective'});
refineCount = min(cfg.geometry.refineCandidateCount,height(coarseRanking));
refineIndices = coarseRanking.SourceIndex(1:refineCount);
primaryCandidates = candidateIndices(rows.TransitionDeg(candidateIndices) == ...
    max(cfg.geometry.transitionWidthsDeg));
refineIndices = unique([refineIndices;primaryCandidates],'stable');
for refineIndex = 1:numel(refineIndices)
    sourceIndex = refineIndices(refineIndex);
    if refineIndex == 1 || mod(refineIndex,5) == 0 || refineIndex == numel(refineIndices)
        fprintf('Geometry refinement: candidate %d of %d.\n',refineIndex,numel(refineIndices));
    end
    candidate = solutions{sourceIndex};
    objective = @(x) wg.optimization_objective(x,candidate.basis,halfWidth, ...
        candidate.transitionDeg);
    refineCfg = cfg;
    refineCfg.optimization.maxFunctionEvaluations = cfg.geometry.maxFunctionEvaluations;
    fullStart = wg.least_squares_start(candidate.basis,halfWidth,candidate.transitionDeg);
    nModes = numel(fullStart);
    fullLower = [zeros(nModes,1);-pi*ones(nModes-1,1)];
    fullUpper = [ones(nModes,1);pi*ones(nModes-1,1)];
    fullSolver = wg.run_fmincon_solver(objective,wg.encode_weights(fullStart), ...
        fullLower,fullUpper,refineCfg);
    fullWeights = wg.decode_variables(fullSolver.x,nModes);
    pruneCfg = cfg;
    pruneCfg.optimization.maxFunctionEvaluations = cfg.geometry.pruneFunctionEvaluations;
    refined = wg.prune_and_refine(pruneCfg,candidate.basis,fullWeights,halfWidth, ...
        candidate.transitionDeg,cfg.optimization.maxActiveModes);
    candidate.weights = refined.weights;
    candidate.metrics = refined.metrics;
    candidate.objective = objective(wg.encode_weights(refined.weights));
    if cfg.geometry.includeAperturePhaseError
        matchingIndices = sourceIndex;
    else
        matchingIndices = find(rows.ApertureWidthMm == rows.ApertureWidthMm(sourceIndex) & ...
            rows.ApertureHeightMm == rows.ApertureHeightMm(sourceIndex) & ...
            rows.TransitionDeg == rows.TransitionDeg(sourceIndex));
    end
    for matchingIndex = matchingIndices(:).'
        propagated = solutions{matchingIndex};
        propagated.weights = candidate.weights;
        propagated.metrics = candidate.metrics;
        propagated.objective = candidate.objective;
        solutions{matchingIndex} = propagated;
    end
    rows.ActiveModeCount(matchingIndices) = nnz(abs(refined.weights) >= 1e-3);
    rows.Objective(matchingIndices) = candidate.objective;
    rows.FunctionEvaluations(matchingIndices) = rows.FunctionEvaluations(matchingIndices)+ ...
        fullSolver.funcCount+refined.solver.funcCount;
    rows.MainRippleDb(matchingIndices) = refined.metrics.MainRippleDb;
    rows.MaxOutsideDb(matchingIndices) = refined.metrics.MaxSidelobeDb;
    rows.MainCrossPolDb(matchingIndices) = refined.metrics.MainCrossPolDb;
    rows.PatternGatesPassed(matchingIndices) = refined.metrics.Passed;
end
writetable(rows,fullfile(paths.tables,'geometry_scan.csv'));

passing = find(rows.PatternGatesPassed);
if ~isempty(passing)
    ranked = sortrows([rows(passing,:),table(passing,'VariableNames',{'SourceIndex'})], ...
        {'TransitionDeg','ApertureWidthMm','ApertureHeightMm','ActiveModeCount','Objective'});
    selectedIndex = ranked.SourceIndex(1);
    selectionStatus = "PASS";
else
    violation = max(rows.MainRippleDb-cfg.optimization.mainRippleLimitDb,0).^2 + ...
        max(rows.MaxOutsideDb-cfg.optimization.sidelobeLimitDb,0).^2 + ...
        max(rows.MainCrossPolDb-cfg.optimization.crossPolLimitDb,0).^2;
    ranking = table((1:height(rows)).',violation,rows.Objective, ...
        rows.ApertureWidthMm.*rows.ApertureHeightMm, ...
        'VariableNames',{'SourceIndex','Violation','Objective','AreaMm2'});
    ranking = sortrows(ranking,{'Violation','AreaMm2','Objective'});
    selectedIndex = ranking.SourceIndex(1);
    selectionStatus = "PARETO_ONLY_NO_GEOMETRY_PASSED";
end
selected = solutions{selectedIndex};
selectedRow = rows(selectedIndex,:);
selectedRow.SelectionStatus = selectionStatus;
writetable(selectedRow,fullfile(paths.tables,'selected_geometry.csv'));
save(fullfile(paths.data,'geometry_results.mat'),'rows','selected','selectedRow','selectionStatus','modes');
wg.make_geometry_figures(cfg,paths,rows,selectedRow,selectionStatus);

outputs.scan = rows;
outputs.selected = selected;
outputs.selectedRow = selectedRow;
outputs.status = selectionStatus;
outputs.paths = paths;
end
