function result = prune_and_refine(cfg,basis,weights,halfWidthDeg,transitionDeg,maxActiveModes)
%PRUNE_AND_REFINE Keep the strongest modes and locally re-optimize them.

nModes = numel(weights);
maxActiveModes = min(maxActiveModes,nModes);
[~,order] = sort(abs(weights),'descend');
active = order(1:maxActiveModes);
if ~ismember(1,active)
    active(end) = 1; % TE10 remains the phase reference.
end
active = unique(active,'stable');
subBasis = basis;
subBasis.co = basis.co(:,:,active);
subBasis.cross = basis.cross(:,:,active);
subBasis.modeNames = basis.modeNames(active);
start = wg.normalize_weights(weights(active),find(active == 1,1));

% Put TE10 first so the existing encoder fixes its phase to zero.
referencePosition = find(active == 1,1);
permutation = [referencePosition,setdiff(1:numel(active),referencePosition,'stable')];
active = active(permutation);
subBasis.co = subBasis.co(:,:,permutation);
subBasis.cross = subBasis.cross(:,:,permutation);
subBasis.modeNames = subBasis.modeNames(permutation);
start = start(permutation);

nActive = numel(active);
lb = [zeros(nActive,1);-pi*ones(nActive-1,1)];
ub = [ones(nActive,1); pi*ones(nActive-1,1)];
objective = @(x) wg.optimization_objective(x,subBasis,halfWidthDeg,transitionDeg);
solver = wg.run_fmincon_solver(objective,wg.encode_weights(start),lb,ub,cfg);
subWeights = wg.decode_variables(solver.x,nActive);
expanded = complex(zeros(nModes,1));
expanded(active) = subWeights;
expanded = wg.normalize_weights(expanded,1);

result.weights = expanded;
result.activeIndices = active;
result.solver = solver;
result.metrics = wg.solution_metrics(basis,expanded,halfWidthDeg,transitionDeg);
end
