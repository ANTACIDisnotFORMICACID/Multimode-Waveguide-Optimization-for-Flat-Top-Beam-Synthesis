function make_robustness_figure(cfg,paths,robustness,nominalMetrics)
%MAKE_ROBUSTNESS_FIGURE Export Monte Carlo tolerance evidence.

degradation = robustness.SidelobeDb-robustness.NominalSidelobeDb;
sortedDegradation = sort(degradation);
probability = (1:numel(sortedDegradation))'/numel(sortedDegradation);
fig = figure('Visible','off','Color','w','Position',[100 100 1250 560]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
plot(sortedDegradation,probability,'Color',[0.08 0.38 0.68],'LineWidth',2);
medianDegradation = median(degradation);
xline(medianDegradation,'--','Color',[0.30 0.30 0.30], ...
    'Label',sprintf('median = %.2f dB',medianDegradation), ...
    'LabelHorizontalAlignment','left');
xline(robustness.SidelobeDegradation95Db,':','Color',[0.85 0.20 0.12], ...
    'Label',sprintf('95%% = %.2f dB',robustness.SidelobeDegradation95Db));
degradationSpan = max(max(degradation)-min(degradation),0.05);
xlim([min(degradation)-0.08*degradationSpan ...
    max(degradation)+0.12*degradationSpan]);
grid on; xlabel('Outside-level degradation (dB)'); ylabel('Empirical CDF');
title('(a) Distribution of outside-level change');
nexttile; hold on;
scatter(robustness.RippleDb,robustness.SidelobeDb,18,robustness.CrossPolDb, ...
    'filled','MarkerFaceAlpha',0.55);
scatter(nominalMetrics.MainRippleDb,nominalMetrics.MaxSidelobeDb,120,'p', ...
    'MarkerFaceColor',[0.85 0.20 0.12],'MarkerEdgeColor','k','LineWidth',1.2);
rippleValues = [robustness.RippleDb(:);nominalMetrics.MainRippleDb];
outsideValues = [robustness.SidelobeDb(:);nominalMetrics.MaxSidelobeDb];
rippleSpan = max(max(rippleValues)-min(rippleValues),0.1);
outsideSpan = max(max(outsideValues)-min(outsideValues),0.1);
xlim([min(rippleValues)-0.08*rippleSpan max(rippleValues)+0.08*rippleSpan]);
ylim([min(outsideValues)-0.08*outsideSpan max(outsideValues)+0.08*outsideSpan]);
grid on; xlabel('Main-region ripple (dB)'); ylabel('Maximum outside level (dB)');
title('(b) Joint variation of pattern metrics'); cb=colorbar;
cb.Label.String='Main-region cross-pol (dB)';
heading = sgtitle(sprintf('Sensitivity to modal amplitude (+/-%.1f dB) and phase (+/-%.0f^o) errors', ...
    cfg.optimization.amplitudeToleranceDb,cfg.optimization.phaseToleranceDeg));
heading.Color = 'k';
wg.export_paper_figure(fig,fullfile(paths.figures,'10_robustness')); close(fig);
end
