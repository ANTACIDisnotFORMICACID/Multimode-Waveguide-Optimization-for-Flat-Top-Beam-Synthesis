function paths = prepare_results(cfg)
%PREPARE_RESULTS Create the reproducible output tree.

paths.root = cfg.resultsDir;
paths.figures = fullfile(paths.root, 'figures');
paths.tables = fullfile(paths.root, 'tables');
paths.hfss = fullfile(paths.root, 'hfss');
paths.data = fullfile(paths.root, 'data');
names = string(struct2cell(paths));
for idx = 1:numel(names)
    if ~isfolder(names(idx)), mkdir(names(idx)); end
end
end

