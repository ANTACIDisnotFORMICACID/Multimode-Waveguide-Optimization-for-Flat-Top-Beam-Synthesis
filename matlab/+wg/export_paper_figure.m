function export_paper_figure(fig,basePath)
%EXPORT_PAPER_FIGURE Export a paper figure as 300 dpi PNG and vector PDF.

basePath = string(basePath);
wg.style_figure(fig);
exportgraphics(fig,basePath+".png",'Resolution',300);
exportgraphics(fig,basePath+".pdf",'ContentType','vector');
end
