function pattern = farfield_fft(cfg, field, thetaDeg, phiDeg)
%FARFIELD_FFT FFT aperture integration with physically correct k axes.

assert(isequal(size(thetaDeg), size(phiDeg)), 'thetaDeg and phiDeg must have equal size.');
ny = numel(field.y);
nx = numel(field.x);
dx = mean(diff(field.x));
dy = mean(diff(field.y));
nfftX = 2^nextpow2(cfg.grid.fftPadding*nx);
nfftY = 2^nextpow2(cfg.grid.fftPadding*ny);

% Match the reference trapz integral by applying the 2-D trapezoidal
% endpoint weights before the transform. FFT2 evaluates exp(-j k.r) on
% samples whose first point is treated as the coordinate origin, so the
% physical x/y origin is restored explicitly below.
wx = ones(1,nx); wx([1 end]) = 0.5;
wy = ones(ny,1); wy([1 end]) = 0.5;
quadratureWeights = wy*wx;
FxGrid = fftshift(fft2(field.Ex.*quadratureWeights, nfftY, nfftX))*dx*dy;
FyGrid = fftshift(fft2(field.Ey.*quadratureWeights, nfftY, nfftX))*dx*dy;
kx = (-floor(nfftX/2):ceil(nfftX/2)-1)*2*pi/(nfftX*dx);
ky = (-floor(nfftY/2):ceil(nfftY/2)-1)*2*pi/(nfftY*dy);
[KX, KY] = meshgrid(kx, ky);
originPhase = exp(-1j*(KX*field.x(1) + KY*field.y(1)));
FxGrid = FxGrid.*originPhase;
FyGrid = FyGrid.*originPhase;

k0 = 2*pi*cfg.frequencyHz/cfg.c0;
th = deg2rad(thetaDeg);
ph = deg2rad(phiDeg);
kxq = -k0*sin(th).*cos(ph);
kyq = -k0*sin(th).*sin(ph);
interpX = griddedInterpolant({ky, kx}, FxGrid, 'spline', 'none');
interpY = griddedInterpolant({ky, kx}, FyGrid, 'spline', 'none');
Fx = interpX(kyq, kxq);
Fy = interpY(kyq, kxq);
Fx(~isfinite(Fx)) = 0;
Fy(~isfinite(Fy)) = 0;

pattern = wg.spectral_to_spherical(Fx, Fy, thetaDeg, phiDeg);
pattern.method = "fft";
pattern.kxRadPerM = kx;
pattern.kyRadPerM = ky;
end

