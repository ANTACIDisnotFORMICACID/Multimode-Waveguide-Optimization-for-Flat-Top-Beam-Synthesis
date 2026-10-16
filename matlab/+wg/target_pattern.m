function target = target_pattern(thetaDeg, halfWidthDeg, transitionDeg)
%TARGET_PATTERN Smooth flat-top amplitude target.

u = abs(thetaDeg(:));
target = zeros(size(u));
target(u <= halfWidthDeg) = 1;
transition = u > halfWidthDeg & u < halfWidthDeg+transitionDeg;
target(transition) = 0.5*(1+cos(pi*(u(transition)-halfWidthDeg)/transitionDeg));
end

