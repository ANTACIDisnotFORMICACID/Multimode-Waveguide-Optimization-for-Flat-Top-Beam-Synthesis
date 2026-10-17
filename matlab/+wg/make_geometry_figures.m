function make_geometry_figures(cfg,paths,rows,selectedRow,~)
%MAKE_GEOMETRY_FIGURES Export the model schematic and aperture trade-off.

A = selectedRow.ApertureWidthMm;
B = selectedRow.ApertureHeightMm;
L = selectedRow.FlareLengthMm;
a = cfg.widthM*1e3;
b = cfg.heightM*1e3;
feedLength = cfg.geometry.feedStraightLengthM*1e3;

% Model and coordinate definition.  The left panel is a transparent
% perspective view; the right panel compares the throat and aperture.
fig = figure('Visible','off','Color','w','Position',[80 80 1500 650]);
tiledlayout(1,2,'TileSpacing','compact','Padding','compact');
nexttile; hold on;
zBack = -L-feedLength;
zThroat = -L;
zAperture = 0;
feedCorners = [-a/2 -b/2; a/2 -b/2; a/2 b/2; -a/2 b/2];
apertureCorners = [-A/2 -B/2; A/2 -B/2; A/2 B/2; -A/2 B/2];
wallColor = [0.20 0.48 0.72];

for edge = 1:4
    nextEdge = mod(edge,4)+1;
    patch([zThroat zThroat zAperture zAperture], ...
        [feedCorners(edge,1) feedCorners(nextEdge,1) ...
         apertureCorners(nextEdge,1) apertureCorners(edge,1)], ...
        [feedCorners(edge,2) feedCorners(nextEdge,2) ...
         apertureCorners(nextEdge,2) apertureCorners(edge,2)], ...
        wallColor,'FaceAlpha',0.10,'EdgeColor',wallColor,'LineWidth',1.2);
    patch([zBack zBack zThroat zThroat], ...
        [feedCorners(edge,1) feedCorners(nextEdge,1) ...
         feedCorners(nextEdge,1) feedCorners(edge,1)], ...
        [feedCorners(edge,2) feedCorners(nextEdge,2) ...
         feedCorners(nextEdge,2) feedCorners(edge,2)], ...
        [0.45 0.48 0.52],'FaceAlpha',0.08,'EdgeColor',[0.35 0.35 0.35], ...
        'LineWidth',1.0);
end
for edge = 1:4
    nextEdge = mod(edge,4)+1;
    plot3([zThroat zThroat],[feedCorners(edge,1) feedCorners(nextEdge,1)], ...
        [feedCorners(edge,2) feedCorners(nextEdge,2)],'k-','LineWidth',1.1);
    plot3([zAperture zAperture],[apertureCorners(edge,1) apertureCorners(nextEdge,1)], ...
        [apertureCorners(edge,2) apertureCorners(nextEdge,2)],'k-','LineWidth',1.5);
end

% Lightly show the two principal cut planes.
patch([zThroat zThroat zAperture zAperture],[-a/2 a/2 A/2 -A/2], ...
    [0 0 0 0],[0.13 0.52 0.78],'FaceAlpha',0.06,'EdgeColor','none');
patch([zThroat zThroat zAperture zAperture],[0 0 0 0], ...
    [-b/2 b/2 B/2 -B/2],[0.88 0.38 0.18], ...
    'FaceAlpha',0.06,'EdgeColor','none');

quiver3(zBack+0.15*feedLength,0,0,L+0.70*feedLength,0,0,0, ...
    'Color',[0.82 0.20 0.12],'LineWidth',2,'MaxHeadSize',0.25);
text(zBack+0.48*(L+feedLength),1.5,2.5,'+z propagation', ...
    'Color',[0.70 0.12 0.08],'FontWeight','bold');
text(zBack+5,-a/2-2,b/2+2,sprintf('feed %.0f x %.0f mm',a,b));
text(zAperture,A/2+2,B/2,sprintf('aperture %.0f x %.0f mm',A,B));
text(-L/2,-A/2-4,-B/2-2,sprintf('L = %.0f mm',L));
xlabel('z (mm)'); ylabel('x (mm)'); zlabel('y (mm)');
title('(a) Fixed-feed pyramidal horn');
axis equal; grid on; view(33,22);
xlim([zBack-5 12]); ylim([-A/2-8 A/2+15]); zlim([-B/2-6 B/2+6]);

nexttile; hold on;
rectangle('Position',[-A/2 -B/2 A B],'EdgeColor',[0.08 0.32 0.60], ...
    'LineWidth',2.2);
rectangle('Position',[-a/2 -b/2 a b],'EdgeColor',[0.25 0.25 0.25], ...
    'LineStyle','--','LineWidth',1.8);
plot([-A/2 A/2],[0 0],'-','Color',[0.13 0.52 0.78],'LineWidth',1.4);
plot([0 0],[-B/2 B/2],'-','Color',[0.88 0.38 0.18],'LineWidth',1.4);
quiver(0,-0.25*B,0,0.38*B,0,'Color',[0.82 0.20 0.12], ...
    'LineWidth',2,'MaxHeadSize',0.8);
text(1,0.18*B,'TE10 electric field','Color',[0.70 0.12 0.08]);
text(0.30*A,1.5,'H-plane direction','Color',[0.08 0.36 0.62], ...
    'HorizontalAlignment','center');
text(1,0.34*B,'E-plane direction','Color',[0.76 0.28 0.10]);
text(-A/2+1,B/2-2,'optimized aperture','Color',[0.08 0.32 0.60]);
text(-a/2+1,-b/2+2,'feed projection','Color',[0.25 0.25 0.25]);
xlabel('x (mm)'); ylabel('y (mm)');
title('(b) Aperture plane and principal cuts');
axis equal; grid on;
xlim([-A/2-5 A/2+5]); ylim([-B/2-5 B/2+5]);
wg.export_paper_figure(fig,fullfile(paths.figures,'01_model_geometry')); close(fig);

% Aperture-size scan at the selected transition.  When aperture phase
% error is disabled, L only filters candidates through the half-angle
% constraint, so each A/B cell is represented by its lowest-objective row.
widths = unique(rows.ApertureWidthMm);
heights = unique(rows.ApertureHeightMm);
rippleMatrix = nan(numel(heights),numel(widths));
outsideMatrix = nan(numel(heights),numel(widths));
bestRows = table();
for rowIdx = 1:numel(heights)
    for colIdx = 1:numel(widths)
        mask = rows.ApertureWidthMm == widths(colIdx) & ...
            rows.ApertureHeightMm == heights(rowIdx) & ...
            rows.TransitionDeg == selectedRow.TransitionDeg;
        candidates = rows(mask,:);
        if isempty(candidates), continue; end
        [~,bestIndex] = min(candidates.Objective);
        chosen = candidates(bestIndex,:);
        rippleMatrix(rowIdx,colIdx) = chosen.MainRippleDb;
        outsideMatrix(rowIdx,colIdx) = chosen.MaxOutsideDb;
        bestRows = [bestRows;chosen]; %#ok<AGROW>
    end
end

fig = figure('Visible','off','Color','w','Position',[40 100 1750 610]);
layout = tiledlayout(1,3,'TileSpacing','compact','Padding','compact');
ax1 = nexttile; hold on;
image1 = imagesc(widths,heights,rippleMatrix); axis xy;
image1.AlphaData = isfinite(rippleMatrix); colormap(ax1,parula);
scatter(selectedRow.ApertureWidthMm,selectedRow.ApertureHeightMm,120,'p', ...
    'MarkerFaceColor',[0.88 0.24 0.12],'MarkerEdgeColor','k','LineWidth',1.1);
cb1 = colorbar; cb1.Label.String = 'Ripple (dB)';
xlabel('Aperture width A (mm)'); ylabel('Aperture height B (mm)');
title('(a) Main-region ripple'); grid on;

ax2 = nexttile; hold on;
image2 = imagesc(widths,heights,outsideMatrix); axis xy;
image2.AlphaData = isfinite(outsideMatrix); colormap(ax2,parula);
scatter(selectedRow.ApertureWidthMm,selectedRow.ApertureHeightMm,120,'p', ...
    'MarkerFaceColor',[0.88 0.24 0.12],'MarkerEdgeColor','k','LineWidth',1.1);
cb2 = colorbar; cb2.Label.String = 'Maximum outside level (dB)';
xlabel('Aperture width A (mm)'); ylabel('Aperture height B (mm)');
title('(b) Outside-region radiation'); grid on;

nexttile; hold on;
areas = bestRows.ApertureWidthMm.*bestRows.ApertureHeightMm;
scatter(bestRows.MainRippleDb,bestRows.MaxOutsideDb,55,areas,'filled', ...
    'MarkerFaceAlpha',0.78,'MarkerEdgeColor',[0.25 0.25 0.25]);
scatter(selectedRow.MainRippleDb,selectedRow.MaxOutsideDb,170,'p', ...
    'MarkerFaceColor',[0.88 0.24 0.12],'MarkerEdgeColor','k','LineWidth',1.2);
text(selectedRow.MainRippleDb,selectedRow.MaxOutsideDb, ...
    sprintf('  %.0f x %.0f mm',A,B),'FontWeight','bold', ...
    'VerticalAlignment','bottom');
cb3 = colorbar; cb3.Label.String = 'Aperture area (mm^2)';
xlabel('Main-region ripple (dB)');
ylabel('Maximum outside level (dB)');
title('(c) Flatness--suppression trade-off'); grid on;
heading = title(layout,sprintf('Aperture-size scan for the 20^o flat-top target (%.0f^o transition)', ...
    selectedRow.TransitionDeg));
heading.Color = 'k';
wg.export_paper_figure(fig,fullfile(paths.figures,'05_geometry_tradeoff')); close(fig);
end
