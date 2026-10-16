function weights = decode_variables(x, nModes)
%DECODE_VARIABLES Convert bounded amplitudes/phases to modal weights.

x = x(:);
amplitude = x(1:nModes);
phase = [0; x(nModes+1:end)];
weights = amplitude(:).*exp(1j*phase(:));
weights = wg.normalize_weights(weights, 1);
end

