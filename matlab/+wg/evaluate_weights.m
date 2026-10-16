function result = evaluate_weights(basis, weights)
%EVALUATE_WEIGHTS Synthesize all plane cuts from modal weights.

weights = wg.normalize_weights(weights);
co = sum(basis.co.*reshape(weights, 1, 1, []), 3);
cross = sum(basis.cross.*reshape(weights, 1, 1, []), 3);
power = abs(co).^2 + abs(cross).^2;
power = power/max(power(:)+eps);
result.weights = weights;
result.co = co;
result.cross = cross;
result.power = power;
result.powerDb = 10*log10(max(power, 1e-12));
result.thetaDeg = basis.thetaDeg;
result.planePhiDeg = basis.planePhiDeg;
end

