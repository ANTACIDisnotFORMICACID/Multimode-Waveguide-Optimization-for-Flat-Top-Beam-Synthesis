function catalog = enumerate_modes(cfg)
%ENUMERATE_MODES Build the TE/TM mode catalog and propagation status.

rows = cell(0, 10);
omega = 2*pi*cfg.frequencyHz;
for family = ["TE", "TM"]
    for m = 0:cfg.maxM
        for n = 0:cfg.maxN
            if family == "TE"
                validIndex = ~(m == 0 && n == 0);
            else
                validIndex = m >= 1 && n >= 1;
            end
            if ~validIndex
                continue;
            end

            kc = sqrt((m*pi/cfg.widthM)^2 + (n*pi/cfg.heightM)^2);
            fc = cfg.c0*kc/(2*pi);
            delta = cfg.frequencyHz - fc;
            if abs(delta) <= cfg.cutoffToleranceHz
                status = "cutoff";
                beta = 0;
                impedance = Inf;
            elseif delta > cfg.cutoffToleranceHz
                status = "propagating";
                k0 = omega/cfg.c0;
                beta = sqrt(max(k0^2-kc^2, 0));
                if family == "TE"
                    impedance = omega*cfg.mu0/beta;
                else
                    impedance = beta/(omega*cfg.eps0);
                end
            else
                status = "evanescent";
                beta = NaN;
                impedance = NaN;
            end
            name = family + string(m) + string(n);
            rows(end+1, :) = {name, family, m, n, fc, fc/1e9, kc, beta, impedance, status}; %#ok<AGROW>
        end
    end
end

catalog = cell2table(rows, 'VariableNames', ...
    {'Name','Family','m','n','CutoffHz','CutoffGHz','kcRadPerM', ...
     'betaRadPerM','ImpedanceOhm','Status'});
catalog = sortrows(catalog, {'CutoffHz','Family','m','n'});
end

