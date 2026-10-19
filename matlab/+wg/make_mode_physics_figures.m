function summary = make_mode_physics_figures(cfg,modes,paths)
%MAKE_MODE_PHYSICS_FIGURES Visualize modal parity and vector far fields.

assert(all(modes.Status == "propagating"), ...
    'Mode-physics figures must use propagating modes only.');

% Full visible-hemisphere atlas.  A moderate padding factor is sufficient
% for the 2-degree display grid and avoids spending optimization-grade FFT
% memory on a qualitative angular map.
thetaAxis = 0:2:90;
phiAxis = -180:4:180;
[phiGrid,thetaGrid] = meshgrid(phiAxis,thetaAxis);
mapCfg = cfg;
mapCfg.grid.fftPadding = min(cfg.grid.fftPadding,4);

fig = figure('Visible','off','Color','w','Position',[80 80 1800 760]);
tiledlayout(2,5,'TileSpacing','compact','Padding','compact');
for modeIdx = 1:height(modes)
    field = wg.mode_fields(cfg,modes.Family(modeIdx),modes.m(modeIdx),modes.n(modeIdx));
    pattern = wg.farfield_fft(mapCfg,field,thetaGrid,phiGrid);
    normalizedPower = pattern.power/max(pattern.power(:)+eps);
    patternDb = 10*log10(max(normalizedPower,1e-4));

    nexttile;
    imagesc(phiAxis,thetaAxis,patternDb);
    axis xy tight;
    clim([-40 0]);
    xticks([-180 -90 0 90 180]);
    yticks([0 30 60 90]);
    if modeIdx > 5, xlabel('\phi (deg)'); end
    if modeIdx == 1 || modeIdx == 6, ylabel('\theta (deg)'); end
    title(sprintf('%s   f_c=%.2f GHz',modes.Name(modeIdx),modes.CutoffGHz(modeIdx)));
end
colormap(turbo);
cb = colorbar;
cb.Layout.Tile = 'east';
cb.Label.String = 'Normalized total power (dB)';
wg.export_paper_figure(fig,fullfile(paths.figures,'S2_propagating_mode_farfield_atlas'));
close(fig);

% TE_m0 is the cleanest family for exposing the connection between the
% signed aperture profile, parity at broadside, and off-axis radiation.
familyNames = ["TE10","TE20","TE30"];
colors = [0.00 0.35 0.70; 0.85 0.33 0.10; 0.93 0.69 0.13];
thetaCut = (-90:0.25:90).';
cutRows = table();
fig = figure('Visible','off','Color','w','Position',[100 100 1450 570]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');

nexttile; hold on;
for idx = 1:numel(familyNames)
    hit = find(modes.Name == familyNames(idx),1);
    assert(~isempty(hit),'Required mode is not propagating: %s',familyNames(idx));
    field = wg.mode_fields(cfg,modes.Family(hit),modes.m(hit),modes.n(hit));
    [~,centerY] = min(abs(field.y));
    signedProfile = real(1j*field.Ey(centerY,:));
    signedProfile = signedProfile/max(abs(signedProfile)+eps);
    plot(field.x*1e3,signedProfile,'LineWidth',2.0,'Color',colors(idx,:), ...
        'DisplayName',familyNames(idx));
end
yline(0,'Color',[0.35 0.35 0.35],'HandleVisibility','off');
xlabel('x (mm)'); ylabel('Signed E_y / max|E_y|');
xlim([cfg.widthM*-500 cfg.widthM*500]); ylim([-1.12 1.12]);
title('(a) Aperture profiles at y = 0');
grid on; legend('Location','southoutside','NumColumns',3);

nexttile; hold on;
for idx = 1:numel(familyNames)
    hit = find(modes.Name == familyNames(idx),1);
    field = wg.mode_fields(cfg,modes.Family(hit),modes.m(hit),modes.n(hit));
    pattern = wg.farfield_fft(cfg,field,thetaCut,zeros(size(thetaCut)));
    normalizedPower = pattern.power/max(pattern.power+eps);
    patternDb = 10*log10(max(normalizedPower,1e-4));
    plot(thetaCut,patternDb,'LineWidth',2.0,'Color',colors(idx,:), ...
        'DisplayName',familyNames(idx));
    block = table(repmat(familyNames(idx),numel(thetaCut),1),thetaCut,patternDb, ...
        'VariableNames',{'Mode','ThetaDeg','TotalPowerDb'});
    cutRows = [cutRows;block]; %#ok<AGROW>
end
xline(0,':','Broadside','Color',[0.30 0.30 0.30], ...
    'LabelVerticalAlignment','bottom','HandleVisibility','off');
xlabel('\theta (deg)'); ylabel('Normalized total power (dB)');
xlim([-90 90]); ylim([-40 0]);
title('(b) H-plane far-field cuts');
grid on; legend('Location','southoutside','NumColumns',3);

wg.export_paper_figure(fig,fullfile(paths.figures,'S1_mode_parity_and_farfield'));
close(fig);
writetable(cutRows,fullfile(paths.tables,'mode_family_cuts.csv'));

summary.atlasModes = modes.Name;
summary.cutModes = familyNames;
summary.cutTable = cutRows;
end
