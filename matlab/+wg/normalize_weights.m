function weights = normalize_weights(weights, referenceIdx)
%NORMALIZE_WEIGHTS Enforce unit modal power and remove global phase.

if nargin < 2 || isempty(referenceIdx), referenceIdx = 1; end
weights = weights(:);
normValue = norm(weights);
if normValue < eps
    weights(referenceIdx) = 1;
else
    weights = weights/normValue;
end
if abs(weights(referenceIdx)) > eps
    weights = weights*exp(-1j*angle(weights(referenceIdx)));
end
end

