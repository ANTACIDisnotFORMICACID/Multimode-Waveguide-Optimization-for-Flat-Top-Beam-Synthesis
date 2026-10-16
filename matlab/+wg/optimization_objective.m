function [objective, detail] = optimization_objective(x, basis, halfWidthDeg, transitionDeg)
%OPTIMIZATION_OBJECTIVE Multi-plane power, sidelobe, and cross-pol objective.

nModes = numel(basis.modeNames);
weights = wg.decode_variables(x, nModes);
result = wg.evaluate_weights(basis, weights);
targetAmplitude = wg.target_pattern(basis.thetaDeg, halfWidthDeg, transitionDeg);
targetPower = targetAmplitude.^2;
targetMatrix = repmat(targetPower, 1, numel(basis.planePhiDeg));
theta = basis.thetaDeg;
mainMask = abs(theta) <= halfWidthDeg;
transitionMask = abs(theta) > halfWidthDeg & abs(theta) < halfWidthDeg+transitionDeg;
sideMask = abs(theta) >= halfWidthDeg+transitionDeg;

mainError = mean((result.power(mainMask, :)-targetMatrix(mainMask, :)).^2, 'all');
if any(transitionMask)
    transitionError = mean((result.power(transitionMask, :)-targetMatrix(transitionMask, :)).^2, 'all');
else
    transitionError = 0;
end
sideError = mean(result.power(sideMask, :).^2, 'all');
crossPower = abs(result.cross).^2/max(max(abs(result.co(:)).^2), eps);
crossError = mean(crossPower(mainMask, :), 'all');

objective = 4*mainError + 2*transitionError + 4*sideError + 2*crossError;
if nargout > 1
    detail.MainError = mainError;
    detail.TransitionError = transitionError;
    detail.SidelobeError = sideError;
    detail.CrossPolError = crossError;
    detail.Result = result;
end
end

