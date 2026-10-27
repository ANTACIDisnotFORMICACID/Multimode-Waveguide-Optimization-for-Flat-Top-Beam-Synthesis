function outputs = run_validation(cfg)
%RUN_VALIDATION Compare direct integration, FFT, grid convergence, and solvers.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
mode = catalog(catalog.Name == "TE10", :);
geometryFile = fullfile(paths.data,'geometry_results.mat');
if isfile(geometryFile)
    geometryData = load(geometryFile,'selected');
    geometry = geometryData.selected.geometry;
    field = wg.horn_aperture_fields(cfg,mode.Family,mode.m,mode.n,geometry);
else
    geometry = [];
    field = wg.mode_fields(cfg,mode.Family,mode.m,mode.n);
end
theta = cfg.angles.cutDeg(:);

comparison = table();
summary = table();
fig = figure('Visible','off','Color','w','Position',[100 100 1500 850]);
tiledlayout(2, 2, 'TileSpacing','compact','Padding','compact');
phiValues = [90 0]; % TE10 E plane (yz), then H plane (xz).
for planeIdx = 1:2
    phi = repmat(phiValues(planeIdx), size(theta));
    direct = wg.farfield_direct(cfg, field, theta, phi);
    fftPattern = wg.farfield_fft(cfg, field, theta, phi);
    directPower = direct.power/max(direct.power(:)+eps);
    fftPower = fftPattern.power/max(fftPattern.power(:)+eps);
    rmse = sqrt(mean((directPower-fftPower).^2));
    md = wg.pattern_metrics(direct);
    mf = wg.pattern_metrics(fftPattern);
    peakDiff = abs(md.PeakDirectionDeg-mf.PeakDirectionDeg);

    if isempty(geometry)
        [~,atDb,atStatus,atMessage] = wg.antenna_toolbox_cut(cfg,phiValues(planeIdx));
    else
        atDb = nan(size(theta));
        atStatus = "REFERENCE_ONLY_NOT_COMPARABLE";
        atMessage = "Antenna Toolbox straight-waveguide model is not compared with the selected horn.";
    end
    antennaRmseDb = NaN;
    antennaPeakDifferenceDeg = NaN;
    if atStatus == "PASS"
        directDb = 10*log10(max(directPower,1e-12));
        comparisonMask = directDb > -20 & isfinite(atDb);
        antennaRmseDb = sqrt(mean((directDb(comparisonMask)-atDb(comparisonMask)).^2));
        [~,antennaPeakIndex] = max(atDb);
        antennaPeakDifferenceDeg = abs(theta(antennaPeakIndex)-md.PeakDirectionDeg);
    end
    planeName = ["E","H"];
    nexttile(planeIdx); hold on;
    plot(theta, 10*log10(max(directPower,1e-5)), 'k-', 'LineWidth',2, 'DisplayName','Direct aperture integral');
    plot(theta, 10*log10(max(fftPower,1e-5)), '--', 'Color',[0.00 0.55 0.72], ...
        'LineWidth',1.8, 'DisplayName','FFT aperture integral');
    grid on; xlim([-90 90]); ylim([-50 2]);
    xlabel('\theta (deg)'); ylabel('Normalized total pattern (dB)');
    title(planeName(planeIdx) + " plane: pattern overlay"); legend('Location','southwest');

    nexttile(planeIdx+2); hold on;
    difference = abs(directPower-fftPower);
    semilogy(theta,max(difference,1e-12),'Color',[0.84 0.24 0.16],'LineWidth',1.5);
    differenceUpper = max(1e-8,10^ceil(log10(max(difference))));
    set(gca,'YScale','log'); xlim([-90 90]); ylim([1e-12 10*differenceUpper]);
    grid on;
    xlabel('\theta (deg)'); ylabel('|P_{direct}-P_{FFT}|');
    title(sprintf('%s plane: RMSE = %.2e, peak error = %.2f deg', ...
        planeName(planeIdx),rmse,peakDiff));

    comparison = [comparison; table(repmat(planeName(planeIdx),numel(theta),1), theta, ...
        10*log10(max(directPower,1e-12)), 10*log10(max(fftPower,1e-12)), atDb, ...
        'VariableNames',{'Plane','ThetaDeg','DirectDb','FFTDb','AntennaToolboxDb'})]; %#ok<AGROW>
    numericalPass = rmse < cfg.validation.fftRmseLimit && ...
        peakDiff <= cfg.validation.peakDirectionLimitDeg;
    summary = [summary; table(planeName(planeIdx), rmse, peakDiff, numericalPass, ...
        atStatus,antennaRmseDb,antennaPeakDifferenceDeg,string(atMessage), ...
        'VariableNames',{'Plane','DirectFftPowerRmse','PeakDirectionDifferenceDeg', ...
        'DirectFftGatePassed','AntennaToolboxStatus','AntennaToolboxRmseDb', ...
        'AntennaToolboxPeakDifferenceDeg','Message'})]; %#ok<AGROW>
end
heading = sgtitle('Independent numerical agreement: direct integration vs FFT');
heading.Color = 'k';
wg.export_paper_figure(fig,fullfile(paths.figures,'04_numerical_validation'));
close(fig);

gridSizes = [65 129 257];
gridSummary = table();
for n = gridSizes
    localCfg = cfg;
    localCfg.grid.nx = n;
    localCfg.grid.ny = floor((n-1)/2)+1;
    if isempty(geometry)
        localField = wg.mode_fields(localCfg,"TE",1,0);
    else
        localField = wg.horn_aperture_fields(localCfg,"TE",1,0,geometry);
    end
    p = wg.farfield_fft(localCfg, localField, theta, zeros(size(theta)));
    metrics = wg.pattern_metrics(p);
    gridSummary = [gridSummary; table(localCfg.grid.nx, localCfg.grid.ny, metrics.HPBWDeg, metrics.MaxSidelobeDb, ...
        'VariableNames',{'Nx','Ny','HPBWDeg','MaxSidelobeDb'})]; %#ok<AGROW>
end
gridSummary.HPBWChangePercent = [NaN; abs(diff(gridSummary.HPBWDeg))./gridSummary.HPBWDeg(1:end-1)*100];
gridSummary.SidelobeChangeDb = [NaN; abs(diff(gridSummary.MaxSidelobeDb))];
gridSummary.GridGatePassed = [false; gridSummary.HPBWChangePercent(2:end) < 1 & ...
    gridSummary.SidelobeChangeDb(2:end) < 0.5];
writetable(comparison, fullfile(paths.tables, 'validation_patterns.csv'));
writetable(summary, fullfile(paths.tables, 'validation_summary.csv'));
writetable(gridSummary, fullfile(paths.tables, 'grid_convergence.csv'));

hfssFile = fullfile(paths.hfss, 'hfss_patterns.csv');
hfssStatusFile = fullfile(paths.hfss, 'hfss_status.json');
tenModeReceipt = fullfile(paths.hfss,'ten_mode_gui_import_20261022','validation_receipt.json');
twelveModeReceipt = fullfile(paths.hfss,'twelve_mode_native_import_20261025','validation_receipt.json');
twelveModeConvergence = fullfile(paths.hfss,'twelve_mode_gui_convergence_20261025', ...
    'mesh_convergence_receipt.json');
twelveModeTe10 = fullfile(paths.hfss,'twelve_mode_te10_comparison_20261025', ...
    'comparison_metrics.json');
twelveModeEvidence = false;
if isfile(twelveModeReceipt) && isfile(twelveModeConvergence) && isfile(twelveModeTe10)
    exportCheck = jsondecode(fileread(twelveModeReceipt));
    convergenceCheck = jsondecode(fileread(twelveModeConvergence));
    te10Check = jsondecode(fileread(twelveModeTe10));
    twelveModeEvidence = strcmp(exportCheck.status,'RAW_EXPORT_VALIDATED') && ...
        exportCheck.port_mode_count == 12 && ...
        convergenceCheck.target_reached_for_required_passes && ...
        te10Check.port_mode == 1 && numel(te10Check.metrics) == 2;
end
if twelveModeEvidence
    hfssStatus = "NATIVE_12MODE_SINGLE_MODE_ONLY";
    hfssMessage = ["The native 12-mode HFSS solve, complex-field export, and a " + ...
        "TE10-candidate comparison exist; port eigenfield identity and the final " + ...
        "optimized multimode comparison remain pending."];
elseif isfile(tenModeReceipt)
    hfssStatus = "PRELIMINARY_10MODE_EXPORT";
    hfssMessage = ["A native 10-mode HFSS complex-field export is validated; " + ...
        "the corrected 12-mode solution, port-field identity, and final multimode comparison remain pending."];
elseif isfile(hfssFile)
    hfssStatus = "PENDING_COMPARISON";
    hfssMessage = "HFSS patterns exist but have not yet passed the quantitative comparison.";
elseif isfile(hfssStatusFile)
    decoded = jsondecode(fileread(hfssStatusFile));
    hfssStatus = string(decoded.status);
    hfssMessage = string(decoded.message);
else
    hfssStatus = "BLOCKED_NOT_RUN";
    hfssMessage = "No HFSS status or pattern export was found.";
end
hfssComparison = table(hfssStatus,NaN,NaN,NaN,false,hfssMessage, ...
    'VariableNames',{'Status','PeakDirectionDifferenceDeg','HPBWRelativeDifference', ...
    'PatternRmseDb','GatePassed','Message'});
writetable(hfssComparison,fullfile(paths.tables,'hfss_comparison.csv'));
fid = fopen(fullfile(paths.tables, 'hfss_validation_status.txt'), 'w');
fprintf(fid, '%s\n%s\n', hfssStatus,hfssMessage); fclose(fid);

outputs.summary = summary;
outputs.gridConvergence = gridSummary;
outputs.hfssStatus = hfssStatus;
outputs.hfssComparison = hfssComparison;
outputs.paths = paths;
end

