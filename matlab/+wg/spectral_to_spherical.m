function pattern = spectral_to_spherical(Fx, Fy, thetaDeg, phiDeg)
%SPECTRAL_TO_SPHERICAL Convert aperture spectra to spherical components.

theta = deg2rad(thetaDeg);
phi = deg2rad(phiDeg);
Etheta = Fx.*cos(phi) + Fy.*sin(phi);
Ephi = cos(theta).*(-Fx.*sin(phi) + Fy.*cos(phi));

% Ludwig-3 definition referenced to the TE10 electric polarization.  For
% a > b with propagation along +z, TE10 has E along global y, so y is the
% co-polar reference and global x is the cross-polar reference.
Eco = Etheta.*sin(phi) + Ephi.*cos(phi);
Ecross = Etheta.*cos(phi) - Ephi.*sin(phi);
power = abs(Etheta).^2 + abs(Ephi).^2;

pattern.thetaDeg = thetaDeg;
pattern.phiDeg = phiDeg;
pattern.Etheta = Etheta;
pattern.Ephi = Ephi;
pattern.Eco = Eco;
pattern.Ecross = Ecross;
pattern.power = power;
end

