function solution = run_pso_solver(objective, lb, ub, cfg, seed)
%RUN_PSO_SOLVER Deterministic particleswarm wrapper with convergence trace.

rng(seed, 'twister');
history = zeros(0, 2);
options = optimoptions('particleswarm', 'Display','off', ...
    'SwarmSize',cfg.optimization.swarmSize, ...
    'MaxIterations',cfg.optimization.maxIterations, ...
    'MaxStallIterations',max(20,round(cfg.optimization.maxIterations/3)), ...
    'UseParallel',false, 'OutputFcn',@recordHistory);
tic;
[x, fval, exitflag, output] = particleswarm(objective, numel(lb), lb, ub, options);
elapsed = toc;
solution.x = x;
solution.fval = fval;
solution.exitflag = exitflag;
solution.funcCount = output.funccount;
solution.elapsedSeconds = elapsed;
solution.history = history;

    function stop = recordHistory(optimValues, state)
        stop = false;
        if state == "iter"
            history(end+1, :) = [optimValues.iteration, optimValues.bestfval]; %#ok<AGROW>
        end
    end
end

