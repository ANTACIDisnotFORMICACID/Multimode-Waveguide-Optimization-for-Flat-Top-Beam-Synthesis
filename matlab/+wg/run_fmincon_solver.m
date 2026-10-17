function solution = run_fmincon_solver(objective, x0, lb, ub, cfg)
%RUN_FMINCON_SOLVER Bounded local optimizer with convergence trace.

history = zeros(0, 2);
options = optimoptions('fmincon', 'Algorithm','sqp', 'Display','off', ...
    'MaxFunctionEvaluations',cfg.optimization.maxFunctionEvaluations, ...
    'MaxIterations',500, 'OptimalityTolerance',1e-8, ...
    'StepTolerance',1e-10, 'OutputFcn',@recordHistory);
tic;
[x, fval, exitflag, output] = fmincon(objective, x0, [],[],[],[],lb,ub,[],options);
elapsed = toc;
solution.x = x;
solution.fval = fval;
solution.exitflag = exitflag;
solution.funcCount = output.funcCount;
solution.elapsedSeconds = elapsed;
solution.history = history;

    function stop = recordHistory(~, optimValues, state)
        stop = false;
        if state == "iter"
            if isfield(optimValues,'funccount')
                evaluations = optimValues.funccount;
            else
                evaluations = optimValues.iteration+1;
            end
            history(end+1, :) = [evaluations, optimValues.fval]; %#ok<AGROW>
        end
    end
end

