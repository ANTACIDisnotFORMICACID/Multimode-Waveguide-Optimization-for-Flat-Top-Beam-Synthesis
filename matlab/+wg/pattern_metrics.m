function metrics = pattern_metrics(pattern, mainHalfWidthDeg, transitionDeg)
%PATTERN_METRICS Extract normalized cut-pattern metrics.

if nargin < 2 || isempty(mainHalfWidthDeg), mainHalfWidthDeg = NaN; end
if nargin < 3 || isempty(transitionDeg), transitionDeg = 0; end
theta = pattern.thetaDeg(:);
power = real(pattern.power(:));
power = max(power, 0);
[peakPower, peakIdx] = max(power);
pn = power/max(peakPower, eps);
pdb = 10*log10(max(pn, 1e-12));
peakTheta = theta(peakIdx);

left = find(pdb(1:peakIdx) <= -3, 1, 'last');
rightRelative = find(pdb(peakIdx:end) <= -3, 1, 'first');
if isempty(rightRelative)
    right = [];
else
    right = peakIdx + rightRelative - 1;
end
if isempty(left) || isempty(right)
    hpbw = NaN;
else
    leftCross = interp1(pdb(left:left+1), theta(left:left+1), -3, 'linear', 'extrap');
    rightCross = interp1(pdb(right-1:right), theta(right-1:right), -3, 'linear', 'extrap');
    hpbw = rightCross-leftCross;
end

if isnan(mainHalfWidthDeg)
    mainHalfWidthDeg = max(hpbw/2, 1);
end
mainMask = abs(theta) <= mainHalfWidthDeg;
sideMask = abs(theta) >= mainHalfWidthDeg+transitionDeg;
if any(mainMask)
    ripple = max(pdb(mainMask))-min(pdb(mainMask));
    crossPeak = max(abs(pattern.Ecross(mainMask)),[],'all');
    coReference = max(max(abs(pattern.Eco(:))),eps);
    crossDb = 20*log10(crossPeak/coReference+eps);
else
    ripple = NaN;
    crossDb = NaN;
end
if any(sideMask), sll = max(pdb(sideMask)); else, sll = NaN; end

metrics.PeakDirectionDeg = peakTheta;
metrics.HPBWDeg = hpbw;
metrics.MainRippleDb = ripple;
metrics.MaxSidelobeDb = sll;
metrics.MainCrossPolDb = crossDb;
metrics.NormalizedPower = pn;
metrics.PatternDb = pdb;
end

