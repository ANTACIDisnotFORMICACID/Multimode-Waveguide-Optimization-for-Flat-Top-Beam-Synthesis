function modes = propagating_modes(catalog)
%PROPAGATING_MODES Return only propagating modes in optimization order.

modes = catalog(catalog.Status == "propagating", :);
preferred = ["TE10","TE20","TE30","TE01","TE11","TE21","TE31", ...
             "TM11","TM21","TM31"];
rank = zeros(height(modes), 1) + numel(preferred) + 1;
for idx = 1:height(modes)
    hit = find(preferred == modes.Name(idx), 1);
    if ~isempty(hit), rank(idx) = hit; end
end
modes.Rank = rank;
modes = sortrows(modes, {'Rank','CutoffHz','Name'});
modes.Rank = [];
end

