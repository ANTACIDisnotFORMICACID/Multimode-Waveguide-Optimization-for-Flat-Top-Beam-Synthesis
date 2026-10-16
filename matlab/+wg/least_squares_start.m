function weights = least_squares_start(basis, halfWidthDeg, transitionDeg)
%LEAST_SQUARES_START Complex least-squares warm start.

target = wg.target_pattern(basis.thetaDeg, halfWidthDeg, transitionDeg);
target = repmat(target, 1, numel(basis.planePhiDeg));
A = reshape(basis.co, [], numel(basis.modeNames));
b = target(:);
weights = lsqminnorm(A,b,1e-10);
weights = wg.normalize_weights(weights, 1);
end

