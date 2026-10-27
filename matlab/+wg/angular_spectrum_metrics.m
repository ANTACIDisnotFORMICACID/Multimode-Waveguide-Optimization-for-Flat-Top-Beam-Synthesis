function metrics = angular_spectrum_metrics(power,u,v,halfWidthDeg,transitionDeg)
%ANGULAR_SPECTRUM_METRICS Quantify a two-dimensional visible-angle pattern.

assert(isequal(size(power),size(u),size(v)), ...
    'Power and direction-cosine grids must have the same size.');
radius = hypot(u,v);
valid = isfinite(power) & power > 0 & radius <= 1;
assert(any(valid(:)), 'The angular spectrum has no finite positive samples.');
main = valid & radius <= sind(halfWidthDeg);
outside = valid & radius >= sind(halfWidthDeg+transitionDeg);
assert(any(main(:)) && any(outside(:)), ...
    'The angular grid must cover both the main and outside regions.');

workingPower = power;
workingPower(~valid) = -inf;
[peakPower,peakIndex] = max(workingPower(:));
[~,boresightIndex] = min(u(:).^2+v(:).^2);
assert(valid(boresightIndex), 'Boresight must be a valid angular sample.');

metrics.PeakThetaDeg = asind(radius(peakIndex));
metrics.PeakPhiDeg = atan2d(v(peakIndex),u(peakIndex));
metrics.BoresightRelativeDb = 10*log10(power(boresightIndex)/peakPower);
metrics.MainDiskRippleDb = 10*log10(max(power(main))/min(power(main)));
metrics.OutsideDiskDb = 10*log10(max(power(outside))/peakPower);
metrics.MaxSampledRadius = max(radius(valid));
end
