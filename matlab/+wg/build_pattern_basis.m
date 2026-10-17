function basis = build_pattern_basis(cfg, modes, thetaDeg, planePhiDeg, geometry)
%BUILD_PATTERN_BASIS Precompute complex far-field basis for fast synthesis.

if nargin < 5, geometry = []; end

nModes = height(modes);
nTheta = numel(thetaDeg);
nPlanes = numel(planePhiDeg);
basis.co = complex(zeros(nTheta, nPlanes, nModes));
basis.cross = complex(zeros(nTheta, nPlanes, nModes));
basis.thetaDeg = thetaDeg(:);
basis.planePhiDeg = planePhiDeg(:).';
basis.modeNames = string(modes.Name);
for modeIdx = 1:nModes
    if isempty(geometry)
        field = wg.mode_fields(cfg,modes.Family(modeIdx),modes.m(modeIdx),modes.n(modeIdx));
    else
        field = wg.horn_aperture_fields(cfg,modes.Family(modeIdx),modes.m(modeIdx),modes.n(modeIdx),geometry);
    end
    for planeIdx = 1:nPlanes
        theta = thetaDeg(:);
        phi = repmat(planePhiDeg(planeIdx), size(theta));
        pattern = wg.farfield_fft(cfg, field, theta, phi);
        basis.co(:, planeIdx, modeIdx) = pattern.Eco;
        basis.cross(:, planeIdx, modeIdx) = pattern.Ecross;
    end
end
basis.geometry = geometry;
end

