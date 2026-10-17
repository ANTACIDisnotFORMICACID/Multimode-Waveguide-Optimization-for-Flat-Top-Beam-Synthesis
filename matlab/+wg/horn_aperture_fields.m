function field = horn_aperture_fields(cfg, family, m, n, geometry, nx, ny)
%HORN_APERTURE_FIELDS Adiabatically map a fixed-feed mode to a horn aperture.
%
% The input mode is always solved in the 20 mm x 10 mm feed.  Its
% normalized transverse shape is stretched to the requested aperture and
% re-normalized to 1 W.  This is an analytic upper-bound model, not a
% substitute for full-wave propagation through the flare.

if nargin < 6, nx = cfg.grid.nx; end
if nargin < 7, ny = cfg.grid.ny; end
feed = wg.mode_fields(cfg,family,m,n,nx,ny);

apertureWidth = geometry.apertureWidthM;
apertureHeight = geometry.apertureHeightM;
assert(apertureWidth >= cfg.widthM && apertureHeight >= cfg.heightM, ...
    'Horn aperture cannot be smaller than the fixed feed.');

scaleX = apertureWidth/cfg.widthM;
scaleY = apertureHeight/cfg.heightM;
field = feed;
field.x = feed.x*scaleX;
field.y = feed.y*scaleY;
[field.X,field.Y] = meshgrid(field.x,field.y);

% Stretching the coordinates increases the integrated power by scaleX*scaleY.
% Applying the inverse square-root keeps every mapped input mode at 1 W.
fieldScale = 1/sqrt(scaleX*scaleY);
names = {'Ex','Ey','Ez','Hx','Hy','Hz'};
for idx = 1:numel(names)
    field.(names{idx}) = feed.(names{idx})*fieldScale;
end

% The default fast model is an explicitly ideal, adiabatic upper bound.
% An optional first-order phase-error switch is retained for sensitivity
% studies, but is not treated as a substitute for full-wave validation.
radiusX = inf;
radiusY = inf;
if isfield(cfg.geometry,'includeAperturePhaseError') && ...
        cfg.geometry.includeAperturePhaseError
    k0 = 2*pi*cfg.frequencyHz/cfg.c0;
    if apertureWidth > cfg.widthM
        radiusX = geometry.flareLengthM*apertureWidth/(apertureWidth-cfg.widthM);
    end
    if apertureHeight > cfg.heightM
        radiusY = geometry.flareLengthM*apertureHeight/(apertureHeight-cfg.heightM);
    end
    pathError = field.X.^2/(2*radiusX)+field.Y.^2/(2*radiusY);
    phaseFactor = exp(-1j*k0*pathError);
    for idx = 1:numel(names)
        field.(names{idx}) = field.(names{idx}).*phaseFactor;
    end
end
sz = 0.5*real(field.Ex.*conj(field.Hy)-field.Ey.*conj(field.Hx));
field.powerW = trapz(field.y,trapz(field.x,sz,2));
field.geometryType = "adiabatic_horn_aperture";
field.apertureWidthM = apertureWidth;
field.apertureHeightM = apertureHeight;
field.flareLengthM = geometry.flareLengthM;
field.phaseRadiusXM = radiusX;
field.phaseRadiusYM = radiusY;
end
