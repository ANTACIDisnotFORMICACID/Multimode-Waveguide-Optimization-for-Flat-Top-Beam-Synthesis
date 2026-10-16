function metrics = solution_metrics(basis, weights, halfWidthDeg, transitionDeg)
%SOLUTION_METRICS Summarize the worst E/H-plane metrics.

result = wg.evaluate_weights(basis, weights);
nPlanes = numel(basis.planePhiDeg);
ripple = zeros(nPlanes, 1);
sll = zeros(nPlanes, 1);
xpol = zeros(nPlanes, 1);
hpbw = zeros(nPlanes, 1);
peak = zeros(nPlanes, 1);
for idx = 1:nPlanes
    p.thetaDeg = result.thetaDeg;
    p.power = result.power(:, idx);
    p.Eco = result.co(:, idx);
    p.Ecross = result.cross(:, idx);
    m = wg.pattern_metrics(p, halfWidthDeg, transitionDeg);
    ripple(idx) = m.MainRippleDb;
    sll(idx) = m.MaxSidelobeDb;
    xpol(idx) = m.MainCrossPolDb;
    hpbw(idx) = m.HPBWDeg;
    peak(idx) = m.PeakDirectionDeg;
end
metrics.MainRippleDb = max(ripple);
metrics.MaxSidelobeDb = max(sll);
metrics.MainCrossPolDb = max(xpol);
metrics.MinCrossPolDb = min(xpol);
metrics.HPBWEDeg = hpbw(1);
metrics.HPBWHDeg = hpbw(min(2,nPlanes));
metrics.PeakEDeg = peak(1);
metrics.PeakHDeg = peak(min(2,nPlanes));
metrics.Passed = metrics.MainRippleDb <= 1 && metrics.MaxSidelobeDb <= -12 && metrics.MainCrossPolDb <= -15;
metrics.Result = result;
end

