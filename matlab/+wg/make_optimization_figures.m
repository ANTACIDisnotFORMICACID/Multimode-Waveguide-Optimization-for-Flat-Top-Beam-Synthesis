function make_optimization_figures(cfg,paths,basis,straightBasis,modes,allSolutions,selectedKey,transition,historyRows,paperMetrics)
%MAKE_OPTIMIZATION_FIGURES Export paper-level pattern and algorithm plots.

selected = allSolutions.(selectedKey);
halfWidth = sscanf(selectedKey,'width_%f');
target = wg.target_pattern(basis.thetaDeg,halfWidth,transition);
baselineWeights = zeros(height(modes),1); baselineWeights(1) = 1;
baseline = wg.evaluate_weights(straightBasis,baselineWeights);
optimized = selected.metrics.Result;

fig = figure('Visible','off','Color','w','Position',[100 100 1500 650]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
planeNames = ["(a) E plane","(b) H plane"];
for planeIdx = 1:2
    nexttile; hold on;
    patch([-halfWidth halfWidth halfWidth -halfWidth],[-40 -40 1 1],[0.91 0.96 1.00], ...
        'EdgeColor','none','HandleVisibility','off');
    patch([-halfWidth-transition -halfWidth -halfWidth -halfWidth-transition], ...
        [-40 -40 1 1],[1.00 0.95 0.88],'EdgeColor','none','HandleVisibility','off');
    patch([halfWidth halfWidth+transition halfWidth+transition halfWidth], ...
        [-40 -40 1 1],[1.00 0.95 0.88],'EdgeColor','none','HandleVisibility','off');
    plot(basis.thetaDeg,20*log10(max(target,1e-4)),'k--','LineWidth',1.5,'DisplayName','Target');
    plot(basis.thetaDeg,baseline.powerDb(:,planeIdx),'Color',[0.45 0.45 0.45], ...
        'LineWidth',1.4,'DisplayName','Straight TE10');
    plot(basis.thetaDeg,optimized.powerDb(:,planeIdx),'Color',[0.88 0.18 0.12], ...
        'LineWidth',2.2,'DisplayName','Optimized horn');
    xline([-halfWidth halfWidth],'--','Color',[0.10 0.45 0.75],'HandleVisibility','off');
    xline([-halfWidth-transition halfWidth+transition],':','Color',[0.75 0.38 0.08], ...
        'HandleVisibility','off');
    xlim([-70 70]); ylim([-40 1]); grid on;
    xlabel('\theta (deg)'); ylabel('Normalized power (dB)'); title(planeNames(planeIdx));
    legend('Location','southwest');
end
wg.export_paper_figure(fig,fullfile(paths.figures,'06_pattern_synthesis')); close(fig);

evaluationGrid = cfg.optimization.historyGrid;
fig = figure('Visible','off','Color','w','Position',[100 100 1000 680]); hold on;
algorithms = ["particleswarm","PSO+fmincon"];
colors = [0.05 0.35 0.70;0.88 0.25 0.10];
labels = ["PSO","PSO + fmincon"];
for algorithmIdx = 1:2
    matrix = nan(numel(evaluationGrid),numel(cfg.optimization.seeds));
    for seedIdx = 1:numel(cfg.optimization.seeds)
        seed = cfg.optimization.seeds(seedIdx);
        mask = historyRows.HalfWidthDeg == halfWidth & ...
            historyRows.Algorithm == algorithms(algorithmIdx) & historyRows.Seed == seed;
        block = historyRows(mask,:);
        if isempty(block), continue; end
        evaluations = [0;block.FunctionEvaluations];
        values = [block.BestObjective(1);block.BestObjective];
        matrix(:,seedIdx) = interp1(evaluations,values,evaluationGrid,'previous','extrap');
    end
    medianCurve = median(matrix,2,'omitnan');
    lower = prctile(matrix,25,2);
    upper = prctile(matrix,75,2);
    fill([evaluationGrid;flipud(evaluationGrid)],[lower;flipud(upper)],colors(algorithmIdx,:), ...
        'FaceAlpha',0.16,'EdgeColor','none','HandleVisibility','off');
    plot(evaluationGrid,medianCurve,'Color',colors(algorithmIdx,:),'LineWidth',2.2, ...
        'DisplayName',labels(algorithmIdx));
end
set(gca,'YScale','log'); grid on; xlim([0 cfg.optimization.maxFunctionEvaluations]);
xlabel('Cumulative forward-field evaluations'); ylabel('Best-so-far objective');
title('20^o flat-top target: median and interquartile range (10 seeds)');
legend('Location','northeast');
wg.export_paper_figure(fig,fullfile(paths.figures,'08_algorithm_convergence')); close(fig);

fig = figure('Visible','off','Color','w','Position',[100 100 1450 610]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
objectiveRatio = 100-paperMetrics.ObjectiveImprovementMedianPct;
objectiveRatioQ25 = 100-paperMetrics.ObjectiveImprovementQ75Pct;
objectiveRatioQ75 = 100-paperMetrics.ObjectiveImprovementQ25Pct;
low = objectiveRatio-objectiveRatioQ25;
high = objectiveRatioQ75-objectiveRatio;
errorbar(paperMetrics.HalfWidthDeg,objectiveRatio,low,high, ...
    'o','Color',[0.10 0.35 0.70],'MarkerFaceColor',[0.10 0.35 0.70], ...
    'MarkerSize',6,'LineWidth',1.5,'LineStyle','none');
yline(100,':','Equal to PSO','Color',[0.40 0.40 0.40], ...
    'LabelHorizontalAlignment','left');
ylim([20 105]); grid on;
xlabel('Flat-top half-width (deg)'); ylabel('Hybrid / PSO objective (%)');
title('(a) Final objective ratio');
nexttile; hold on;
evaluationRatio = 100-paperMetrics.EvaluationReductionMedianPct;
evaluationRatioQ25 = 100-paperMetrics.EvaluationReductionQ75Pct;
evaluationRatioQ75 = 100-paperMetrics.EvaluationReductionQ25Pct;
low = evaluationRatio-evaluationRatioQ25;
high = evaluationRatioQ75-evaluationRatio;
errorbar(paperMetrics.HalfWidthDeg,evaluationRatio,low,high, ...
    'o','Color',[0.10 0.48 0.32],'MarkerFaceColor',[0.10 0.48 0.32], ...
    'MarkerSize',6,'LineWidth',1.5,'LineStyle','none');
yline(100,':','Equal to PSO','Color',[0.40 0.40 0.40], ...
    'LabelHorizontalAlignment','left');
grid on;
xlabel('Flat-top half-width (deg)'); ylabel('Hybrid / PSO evaluations (%)');
title('(b) Forward-model cost ratio');
for tileIndex = 1:2
    ax = nexttile(tileIndex);
    xline(ax,halfWidth,':','Color',[0.85 0.20 0.12],'LineWidth',1.3);
end
wg.export_paper_figure(fig,fullfile(paths.figures,'09_width_sweep')); close(fig);

weights = selected.weights;
active = abs(weights) >= 1e-3;
activeNames = string(modes.Name(active));
activeWeights = weights(active);
signedWeights = abs(activeWeights).*sign(cos(angle(activeWeights)));
fig = figure('Visible','off','Color','w','Position',[100 100 1450 610]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
bars = barh(1:numel(activeNames),signedWeights,'FaceColor','flat');
barColors = repmat([0.08 0.38 0.68],numel(activeNames),1);
barColors(signedWeights < 0,:) = repmat([0.88 0.25 0.10],nnz(signedWeights < 0),1);
bars.CData = barColors;
xline(0,'k-','LineWidth',0.9);
for modeIdx = 1:numel(activeNames)
    value = signedWeights(modeIdx);
    if value >= 0
        horizontalAlignment = 'left';
        offset = 0.02;
    else
        horizontalAlignment = 'right';
        offset = -0.02;
    end
    text(value+offset,modeIdx,sprintf('%.1f^o',rad2deg(angle(activeWeights(modeIdx)))), ...
        'HorizontalAlignment',horizontalAlignment,'VerticalAlignment','middle');
end
xlim([-0.72 0.72]); grid on;
yticks(1:numel(activeNames)); yticklabels(activeNames); ylim([0.4 numel(activeNames)+0.6]);
xlabel('Signed normalized coefficient');
title('(a) Modal amplitude and relative phase');

combinedEx = [];
combinedEy = [];
for modeIdx = find(active).'
    if isempty(basis.geometry)
        field = wg.mode_fields(cfg,modes.Family(modeIdx),modes.m(modeIdx),modes.n(modeIdx));
    else
        field = wg.horn_aperture_fields(cfg,modes.Family(modeIdx),modes.m(modeIdx), ...
            modes.n(modeIdx),basis.geometry);
    end
    if isempty(combinedEx)
        combinedEx = complex(zeros(size(field.Ex)));
        combinedEy = complex(zeros(size(field.Ey)));
    end
    combinedEx = combinedEx+weights(modeIdx)*field.Ex;
    combinedEy = combinedEy+weights(modeIdx)*field.Ey;
end
magnitude = sqrt(abs(combinedEx).^2+abs(combinedEy).^2);
[~,peakIndex] = max(magnitude(:));
reference = combinedEx(peakIndex);
if abs(combinedEy(peakIndex)) > abs(reference), reference = combinedEy(peakIndex); end
rotation = exp(-1j*angle(reference));
ex = real(combinedEx*rotation)/max(magnitude(:));
ey = real(combinedEy*rotation)/max(magnitude(:));
nexttile; hold on;
imagesc(field.x*1e3,field.y*1e3,magnitude/max(magnitude(:)));
axis xy equal tight; clim([0 1]); colormap(parula);
rowStep = 7; colStep = 11;
quiver(field.X(1:rowStep:end,1:colStep:end)*1e3, ...
    field.Y(1:rowStep:end,1:colStep:end)*1e3, ...
    ex(1:rowStep:end,1:colStep:end),ey(1:rowStep:end,1:colStep:end), ...
    0.52,'w','LineWidth',0.8,'MaxHeadSize',0.75);
xlabel('x (mm)'); ylabel('y (mm)');
title('(b) Synthesized transverse aperture field');
cb = colorbar; cb.Label.String = 'Normalized |E_t|';
wg.export_paper_figure(fig,fullfile(paths.figures,'07_modal_composition')); close(fig);
end
