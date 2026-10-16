function x = encode_weights(weights)
%ENCODE_WEIGHTS Convert normalized modal weights to optimization variables.

weights = wg.normalize_weights(weights, 1);
amplitude = abs(weights);
phase = angle(weights);
x = [amplitude(:); phase(2:end)];
end

