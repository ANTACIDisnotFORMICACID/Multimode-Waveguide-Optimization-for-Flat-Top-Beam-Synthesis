function outputFile = export_hfss_reference(cfg)
%EXPORT_HFSS_REFERENCE Export the ideal TE10 horn cut for HFSS comparison.
%
% This is the adiabatic aperture model, not a full-wave solution.  It uses
% the geometry selected by the MATLAB scan and retains complex Etheta/Ephi
% so a later comparison can distinguish shape error from phase convention.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end

selected = readtable(fullfile(cfg.resultsDir,'tables','selected_geometry.csv'));
assert(height(selected) == 1,'Expected one selected horn geometry.');
geometry.apertureWidthM = selected.ApertureWidthMm(1)*1e-3;
geometry.apertureHeightM = selected.ApertureHeightMm(1)*1e-3;
geometry.flareLengthM = selected.FlareLengthMm(1)*1e-3;

field = wg.horn_aperture_fields(cfg,"TE",1,0,geometry);
theta = (-90:0.5:90).';
rows = table();
for setting = ["E","H"]
    if setting == "E", phiDeg = 90; else, phiDeg = 0; end
    pattern = wg.farfield_direct(cfg,field,theta,repmat(phiDeg,size(theta)));
    block = table(repmat(setting,numel(theta),1),theta, ...
        real(pattern.Etheta(:)),imag(pattern.Etheta(:)), ...
        real(pattern.Ephi(:)),imag(pattern.Ephi(:)),pattern.power(:), ...
        'VariableNames',{'Plane','ThetaDeg','EThetaReal','EThetaImag', ...
        'EPhiReal','EPhiImag','TotalPower'});
    rows = [rows;block]; %#ok<AGROW>
end
outDir = fullfile(cfg.resultsDir,'hfss');
if ~isfolder(outDir), mkdir(outDir); end
if cfg.geometry.includeAperturePhaseError
    outputName = 'matlab_quadratic_phase_horn_te10.csv';
else
    outputName = 'matlab_ideal_horn_te10.csv';
end
outputFile = fullfile(outDir,outputName);
writetable(rows,outputFile);
end
