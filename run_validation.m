function outputs = run_validation(cfg)
%RUN_VALIDATION Compare direct integration, FFT, grid convergence, and solvers.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
mode = catalog(catalog.Name == "TE10", :);
field = wg.mode_fields(cfg, mode.Family, mode.m, mode.n);
theta = cfg.angles.cutDeg(:);

comparison = table();
summary = table();
fig = figure('Visible','off','Color','w','Position',[100 100 1500 650]);
tiledlayout(1, 2, 'TileSpacing','compact','Padding','compact');
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

    [atTheta, atDb, atStatus, atMessage] = wg.antenna_toolbox_cut(cfg, phiValues(planeIdx));
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
    nexttile; hold on;
    plot(theta, 10*log10(max(directPower,1e-5)), 'k-', 'LineWidth',2, 'DisplayName','Direct aperture integral');
    plot(theta, 10*log10(max(fftPower,1e-5)), 'r--', 'LineWidth',1.6, 'DisplayName','FFT aperture integral');
    if atStatus == "PASS"
        plot(atTheta, atDb, 'b:', 'LineWidth',1.6, 'DisplayName','Antenna Toolbox MoM');
    end
    grid on; xlim([-90 90]); ylim([-50 2]);
    xlabel('\theta (deg)'); ylabel('Normalized total pattern (dB)');
    title(planeName(planeIdx) + "-plane validation"); legend('Location','southwest');

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
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures, '04_direct_fft_antenna_validation.png'), 'Resolution', 200);
close(fig);

gridSizes = [65 129 257];
gridSummary = table();
for n = gridSizes
    localCfg = cfg;
    localCfg.grid.nx = n;
    localCfg.grid.ny = floor((n-1)/2)+1;
    localField = wg.mode_fields(localCfg, "TE", 1, 0);
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
if isfile(hfssFile)
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

