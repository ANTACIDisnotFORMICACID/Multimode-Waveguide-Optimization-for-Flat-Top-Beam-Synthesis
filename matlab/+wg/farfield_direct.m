function pattern = farfield_direct(cfg, field, thetaDeg, phiDeg)
%FARFIELD_DIRECT Reference aperture integration for arbitrary directions.

assert(isequal(size(thetaDeg), size(phiDeg)), 'thetaDeg and phiDeg must have equal size.');
k0 = 2*pi*cfg.frequencyHz/cfg.c0;
Fx = complex(zeros(size(thetaDeg)));
Fy = complex(zeros(size(thetaDeg)));
for idx = 1:numel(thetaDeg)
    th = deg2rad(thetaDeg(idx));
    ph = deg2rad(phiDeg(idx));
    kx = k0*sin(th)*cos(ph);
    ky = k0*sin(th)*sin(ph);
    kernel = exp(1j*(kx*field.X + ky*field.Y));
    Fx(idx) = trapz(field.y, trapz(field.x, field.Ex.*kernel, 2));
    Fy(idx) = trapz(field.y, trapz(field.x, field.Ey.*kernel, 2));
end
pattern = wg.spectral_to_spherical(Fx, Fy, thetaDeg, phiDeg);
pattern.method = "direct";
end

