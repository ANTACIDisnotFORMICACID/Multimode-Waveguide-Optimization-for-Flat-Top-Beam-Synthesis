function outputs = run_baseline(cfg)
%RUN_BASELINE Generate the mode catalog, fields, patterns, and figures.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
writetable(catalog, fullfile(paths.tables, 'mode_catalog.csv'));
modes = wg.propagating_modes(catalog);

fig = figure('Visible','off','Color','w','Position',[100 100 1500 650]);
hold on;
colors = lines(3);
families = ["TE","TM"];
markers = {'o','s'};
for familyIdx = 1:numel(families)
    mask = catalog.Family == families(familyIdx) & catalog.CutoffGHz <= cfg.frequencyHz/1e9*1.25;
    scatter(categorical(catalog.Name(mask)), catalog.CutoffGHz(mask), 65, ...
        colors(familyIdx,:), markers{familyIdx}, 'filled', 'DisplayName', families(familyIdx));
end
yline(cfg.frequencyHz/1e9, 'k--', '30 GHz operating frequency', 'LineWidth', 1.5);
ylabel('Cutoff frequency (GHz)');
title('Rectangular-waveguide TE/TM mode catalog');
grid on; legend('Location','northwest');
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures, '01_mode_cutoff_catalog.png'), 'Resolution', 200);
close(fig);

representatives = ["TE10","TE11","TM11"];
fig = figure('Visible','off','Color','w','Position',[100 100 1700 1100]);
tiledlayout(numel(representatives), 4, 'TileSpacing','compact','Padding','compact');
for row = 1:numel(representatives)
    hit = find(modes.Name == representatives(row), 1);
    assert(~isempty(hit), 'Required representative mode is not propagating: %s', representatives(row));
    field = wg.mode_fields(cfg, modes.Family(hit), modes.m(hit), modes.n(hit));
    quantities = {abs(field.Ex), angle(field.Ex), abs(field.Ey), angle(field.Ey)};
    labels = {'|E_x|','phase(E_x)','|E_y|','phase(E_y)'};
    for col = 1:4
        nexttile;
        imagesc(field.x*1e3, field.y*1e3, quantities{col});
        axis xy equal tight; colorbar;
        xlabel('x (mm)'); ylabel('y (mm)');
        title(sprintf('%s %s', representatives(row), labels{col}));
    end
end
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures, '02_representative_aperture_fields.png'), 'Resolution', 200);
close(fig);

patternRows = table();
for modeIdx = 1:height(modes)
    field = wg.mode_fields(cfg, modes.Family(modeIdx), modes.m(modeIdx), modes.n(modeIdx));
    for planePhi = [0 90]
        theta = cfg.angles.cutDeg(:);
        phi = repmat(planePhi, size(theta));
        pattern = wg.farfield_fft(cfg, field, theta, phi);
        normalized = pattern.power/max(pattern.power(:)+eps);
        block = table(repmat(modes.Name(modeIdx),numel(theta),1), repmat("FFT",numel(theta),1), ...
            theta, phi, 20*log10(max(abs(pattern.Eco)/max(abs(pattern.Eco(:))),1e-12)), ...
            20*log10(max(abs(pattern.Ecross)/max(abs(pattern.Eco(:))),1e-12)), ...
            10*log10(max(normalized,1e-12)), ...
            'VariableNames', {'Mode','Solver','ThetaDeg','PhiDeg','CoDb','CrossDb','TotalDb'});
        patternRows = [patternRows; block]; %#ok<AGROW>
    end
end
writetable(patternRows, fullfile(paths.tables, 'patterns.csv'));

fig = figure('Visible','off','Color','w','Position',[100 100 1600 1050]);
tiledlayout(2, 2, 'TileSpacing','compact','Padding','compact');
mapModes = ["TE10","TE11","TM11","TE31"];
[phiGrid, thetaGrid] = meshgrid(cfg.angles.mapPhiDeg, cfg.angles.mapThetaDeg);
for idx = 1:numel(mapModes)
    hit = find(modes.Name == mapModes(idx), 1);
    field = wg.mode_fields(cfg, modes.Family(hit), modes.m(hit), modes.n(hit));
    pattern = wg.farfield_fft(cfg, field, thetaGrid, phiGrid);
    db = 10*log10(max(pattern.power/max(pattern.power(:)+eps), 1e-4));
    nexttile;
    imagesc(cfg.angles.mapPhiDeg, cfg.angles.mapThetaDeg, db);
    axis xy; clim([-40 0]); colorbar; colormap turbo;
    xlabel('\phi (deg)'); ylabel('\theta (deg)'); title(mapModes(idx) + " total pattern (dB)");
end
wg.style_figure(fig);
exportgraphics(fig, fullfile(paths.figures, '03_representative_theta_phi_patterns.png'), 'Resolution', 200);
close(fig);

outputs.catalog = catalog;
outputs.propagatingModes = modes;
outputs.paths = paths;
end

