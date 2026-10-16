function field = mode_fields(cfg, family, m, n, nx, ny)
%MODE_FIELDS Compute transverse TE/TM fields normalized to 1 W power.

if nargin < 5, nx = cfg.grid.nx; end
if nargin < 6, ny = cfg.grid.ny; end
family = upper(string(family));
if family == "TE"
    assert(~(m == 0 && n == 0), 'TE00 does not exist.');
elseif family == "TM"
    assert(m >= 1 && n >= 1, 'TM modes require m,n >= 1.');
else
    error('Unsupported mode family: %s', family);
end

a = cfg.widthM;
b = cfg.heightM;
x = linspace(-a/2, a/2, nx);
y = linspace(-b/2, b/2, ny);
[X, Y] = meshgrid(x, y);
Xs = X + a/2;
Ys = Y + b/2;
kx = m*pi/a;
ky = n*pi/b;
kc2 = kx^2 + ky^2;
k0 = 2*pi*cfg.frequencyHz/cfg.c0;
assert(kc2 < k0^2, '%s%d%d is not a propagating mode.', family, m, n);
beta = sqrt(k0^2-kc2);
omega = 2*pi*cfg.frequencyHz;

if family == "TE"
    Ex =  1j*omega*cfg.mu0*ky/kc2 .* cos(kx*Xs).*sin(ky*Ys);
    Ey = -1j*omega*cfg.mu0*kx/kc2 .* sin(kx*Xs).*cos(ky*Ys);
    Hx =  1j*beta*kx/kc2 .* sin(kx*Xs).*cos(ky*Ys);
    Hy =  1j*beta*ky/kc2 .* cos(kx*Xs).*sin(ky*Ys);
    Ez = zeros(size(X));
    Hz = cos(kx*Xs).*cos(ky*Ys);
    impedance = omega*cfg.mu0/beta;
else
    Ex =  1j*beta*kx/kc2 .* cos(kx*Xs).*sin(ky*Ys);
    Ey =  1j*beta*ky/kc2 .* sin(kx*Xs).*cos(ky*Ys);
    Hx = -1j*omega*cfg.eps0*ky/kc2 .* sin(kx*Xs).*cos(ky*Ys);
    Hy =  1j*omega*cfg.eps0*kx/kc2 .* cos(kx*Xs).*sin(ky*Ys);
    Ez = sin(kx*Xs).*sin(ky*Ys);
    Hz = zeros(size(X));
    impedance = beta/(omega*cfg.eps0);
end

sz = 0.5*real(Ex.*conj(Hy)-Ey.*conj(Hx));
powerW = trapz(y, trapz(x, sz, 2));
assert(isfinite(powerW) && powerW > 0, 'Mode power normalization failed.');
scale = 1/sqrt(powerW);

field.Name = family + string(m) + string(n);
field.Family = family;
field.m = m;
field.n = n;
field.x = x;
field.y = y;
field.X = X;
field.Y = Y;
field.Ex = Ex*scale;
field.Ey = Ey*scale;
field.Ez = Ez*scale;
field.Hx = Hx*scale;
field.Hy = Hy*scale;
field.Hz = Hz*scale;
field.betaRadPerM = beta;
field.impedanceOhm = impedance;
field.powerW = trapz(y, trapz(x, 0.5*real(field.Ex.*conj(field.Hy)-field.Ey.*conj(field.Hx)), 2));
end

