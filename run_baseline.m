function outputs = run_baseline(cfg)
%RUN_BASELINE Generate the mode catalog, fields, patterns, and figures.

root = fileparts(mfilename('fullpath'));
addpath(root,fullfile(root,'matlab'));
if nargin < 1, cfg = wg.default_config(root); end
paths = wg.prepare_results(cfg);
catalog = wg.enumerate_modes(cfg);
writetable(catalog, fullfile(paths.tables, 'mode_catalog.csv'));
modes = wg.propagating_modes(catalog);

fig = figure('Visible','off','Color','w','Position',[100 100 1450 700]);
shown = catalog(catalog.CutoffGHz <= cfg.frequencyHz/1e9*1.25,:);
shown = sortrows(shown,{'CutoffGHz','Family','m','n'});
x = (1:height(shown)).';
hold on;
patch([0.5;height(shown)+0.5;height(shown)+0.5;0.5], ...
    [0;0;cfg.frequencyHz/1e9;cfg.frequencyHz/1e9], [0.91 0.97 0.94], ...
    'EdgeColor','none','HandleVisibility','off');
colors = [0.08 0.45 0.74; 0.91 0.38 0.12];
families = ["TE","TM"];
markers = {'o','s'};
for familyIdx = 1:numel(families)
    mask = shown.Family == families(familyIdx);
    scatter(x(mask), shown.CutoffGHz(mask), 75, colors(familyIdx,:), ...
        markers{familyIdx}, 'filled', 'DisplayName', families(familyIdx));
end
% With the exact vacuum speed of light, TE02 and TE40 lie just below 30 GHz.
nearCutoffMask = abs(shown.CutoffGHz-cfg.frequencyHz/1e9) < 0.1;
scatter(x(nearCutoffMask),shown.CutoffGHz(nearCutoffMask),130,'d', ...
    'MarkerEdgeColor',[0.1 0.1 0.1],'LineWidth',1.6, ...
    'DisplayName','Within 0.1 GHz of cutoff');
yline(cfg.frequencyHz/1e9, '--', '30 GHz', 'Color',[0.15 0.15 0.15], ...
    'LineWidth',1.5,'LabelHorizontalAlignment','right','HandleVisibility','off');
xlim([0.5 height(shown)+0.5]); ylim([0 40]);
ax = gca; ax.XTick = x; ax.XTickLabel = cellstr(shown.Name); ax.XTickLabelRotation = 35;
ylabel('Cutoff frequency (GHz)');
title('Mode availability at 30 GHz');
subtitle(sprintf('20 mm x 10 mm rectangular waveguide | %d propagating modes | %d near cutoff', ...
    height(modes),nnz(nearCutoffMask)));
grid on; legend('Location','northwest','NumColumns',3);
text(0.8,2.1,'PROPAGATING REGION','Color',[0.07 0.42 0.23], ...
    'FontWeight','bold','FontSize',11);
wg.export_paper_figure(fig,fullfile(paths.figures,'02_mode_cutoff_catalog'));
close(fig);

representatives = ["TE10","TE20","TE30"; ...
    "TE11","TE21","TE31"; ...
    "TM11","TM21","TM31"];
fig = figure('Visible','off','Color','w','Position',[100 80 1500 850]);
tiledlayout(3,3,'TileSpacing','compact','Padding','compact');
for panel = 1:numel(representatives)
    row = ceil(panel/3);
    col = mod(panel-1,3)+1;
    modeName = representatives(row,col);
    hit = find(modes.Name == modeName, 1);
    assert(~isempty(hit), 'Required representative mode is not propagating: %s', modeName);
    field = wg.mode_fields(cfg, modes.Family(hit), modes.m(hit), modes.n(hit));
    magnitude = sqrt(abs(field.Ex).^2+abs(field.Ey).^2);
    [~,peakIndex] = max(magnitude(:));
    reference = field.Ex(peakIndex);
    if abs(field.Ey(peakIndex)) > abs(reference), reference = field.Ey(peakIndex); end
    rotation = exp(-1j*angle(reference));
    ex = real(field.Ex*rotation)/max(magnitude(:));
    ey = real(field.Ey*rotation)/max(magnitude(:));
    nexttile; hold on;
    imagesc(field.x*1e3,field.y*1e3,magnitude/max(magnitude(:)));
    axis xy equal tight; clim([0 1]); colormap(parula);
    rowStep = 8; colStep = 12;
    quiver(field.X(1:rowStep:end,1:colStep:end)*1e3, ...
        field.Y(1:rowStep:end,1:colStep:end)*1e3, ...
        ex(1:rowStep:end,1:colStep:end),ey(1:rowStep:end,1:colStep:end), ...
        0.52,'w','LineWidth',0.75,'MaxHeadSize',0.75);
    if row == 3, xlabel('x (mm)'); end
    if col == 1, ylabel('y (mm)'); end
    title(sprintf('%s   f_c = %.2f GHz',modeName,modes.CutoffGHz(hit)));
end
cb = colorbar; cb.Layout.Tile = 'east'; cb.Label.String = 'Normalized |E_t|';
wg.export_paper_figure(fig,fullfile(paths.figures,'03_mode_field_atlas'));
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

modePhysics = wg.make_mode_physics_figures(cfg,modes,paths);

outputs.catalog = catalog;
outputs.propagatingModes = modes;
outputs.modePhysics = modePhysics;
outputs.paths = paths;
end

