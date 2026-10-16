function style_figure(fig)
%STYLE_FIGURE Force portable light-theme exports independent of MATLAB UI theme.

set(fig,'Color','w');
axesHandles = findall(fig,'Type','axes');
set(axesHandles,'Color','w','XColor','k','YColor','k','GridColor',[0.72 0.72 0.72], ...
    'MinorGridColor',[0.82 0.82 0.82]);
set(findall(fig,'Type','text'),'Color','k');
legends = findall(fig,'Type','legend');
set(legends,'Color','w','TextColor','k','EdgeColor',[0.25 0.25 0.25]);
colorbars = findall(fig,'Type','colorbar');
set(colorbars,'Color','k');
end
