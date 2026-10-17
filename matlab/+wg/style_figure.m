function style_figure(fig)
%STYLE_FIGURE Force portable light-theme exports independent of MATLAB UI theme.

set(fig,'Color','w');
axesHandles = findall(fig,'Type','axes');
set(axesHandles,'Color','w','XColor','k','YColor','k','GridColor',[0.72 0.72 0.72], ...
    'MinorGridColor',[0.82 0.82 0.82],'FontName','Times New Roman', ...
    'FontSize',10,'LineWidth',0.8,'TickDir','out');
set(findall(fig,'Type','text'),'Color','k','FontName','Times New Roman');
legends = findall(fig,'Type','legend');
set(legends,'Color','w','TextColor','k','EdgeColor',[0.25 0.25 0.25], ...
    'FontName','Times New Roman','FontSize',9);
colorbars = findall(fig,'Type','colorbar');
set(colorbars,'Color','k','FontName','Times New Roman','FontSize',9);
end
