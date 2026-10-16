function result = monte_carlo_robustness(cfg, basis, weights, halfWidthDeg, transitionDeg)
%MONTE_CARLO_ROBUSTNESS Test bounded amplitude/phase perturbations.

rng(90210, 'twister');
nTrials = cfg.optimization.monteCarloTrials;
nominal = wg.solution_metrics(basis, weights, halfWidthDeg, transitionDeg);
sll = zeros(nTrials, 1);
ripple = zeros(nTrials, 1);
xpol = zeros(nTrials, 1);
for idx = 1:nTrials
    amplitudeDb = (2*rand(size(weights))-1)*cfg.optimization.amplitudeToleranceDb;
    phaseDeg = (2*rand(size(weights))-1)*cfg.optimization.phaseToleranceDeg;
    perturbed = weights.*10.^(amplitudeDb/20).*exp(1j*deg2rad(phaseDeg));
    perturbed = wg.normalize_weights(perturbed, 1);
    metrics = wg.solution_metrics(basis, perturbed, halfWidthDeg, transitionDeg);
    sll(idx) = metrics.MaxSidelobeDb;
    ripple(idx) = metrics.MainRippleDb;
    xpol(idx) = metrics.MainCrossPolDb;
end
result.NominalSidelobeDb = nominal.MaxSidelobeDb;
result.SidelobeDb = sll;
result.RippleDb = ripple;
result.CrossPolDb = xpol;
result.SidelobeDegradation95Db = prctile(sll-nominal.MaxSidelobeDb, 95);
result.Passed = result.SidelobeDegradation95Db <= 3;
end

