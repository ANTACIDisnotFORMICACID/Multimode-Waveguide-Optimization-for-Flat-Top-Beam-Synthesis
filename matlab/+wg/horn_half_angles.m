function [angleXDeg,angleYDeg] = horn_half_angles(cfg, geometry)
%HORN_HALF_ANGLES Return E/H-plane pyramidal-horn half angles.

angleXDeg = rad2deg(atan((geometry.apertureWidthM-cfg.widthM)/(2*geometry.flareLengthM)));
angleYDeg = rad2deg(atan((geometry.apertureHeightM-cfg.heightM)/(2*geometry.flareLengthM)));
end
