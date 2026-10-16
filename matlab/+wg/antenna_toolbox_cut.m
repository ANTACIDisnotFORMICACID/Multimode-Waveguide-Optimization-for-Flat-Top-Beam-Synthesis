function [thetaDeg, patternDb, status, message] = antenna_toolbox_cut(cfg, planePhiDeg)
%ANTENNA_TOOLBOX_CUT Independent open-ended waveguide TE10 comparison.

thetaDeg = cfg.angles.cutDeg(:);
patternDb = nan(size(thetaDeg));
status = "BLOCKED";
try
    wgObject = waveguide(Width=cfg.widthM, Height=cfg.heightM, Length=cfg.lengthM);
    % The Antenna Toolbox object is built along +x with width along y and
    % height along z. Rotate the cyclic axes to the project convention:
    % propagation +z, width x, height y.
    wgObject.Tilt = -120;
    wgObject.TiltAxis = [1 1 1];
    positive = thetaDeg >= 0;
    elevationDeg = 90-abs(thetaDeg);
    % Antenna Toolbox elevation is limited to [-90,90]. A signed negative
    % theta is represented by positive |theta| at azimuth phi+180 deg.
    patternDb(positive) = pattern(wgObject,cfg.frequencyHz,planePhiDeg, ...
        elevationDeg(positive),'Type','directivity');
    patternDb(~positive) = pattern(wgObject,cfg.frequencyHz,mod(planePhiDeg+180,360), ...
        elevationDeg(~positive),'Type','directivity');
    patternDb = patternDb(:)-max(patternDb(:));
    status = "PASS";
    message = "Antenna Toolbox open-ended waveguide solved successfully.";
catch exception
    message = string(exception.message);
end
end

