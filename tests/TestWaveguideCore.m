classdef TestWaveguideCore < matlab.unittest.TestCase
    %TESTWAVEGUIDECORE Numerical correctness gates for the forward model.

    properties
        Config
    end

    methods (TestMethodSetup)
        function configure(testCase)
            root = fileparts(fileparts(mfilename('fullpath')));
            addpath(root, fullfile(root, 'matlab'));
            testCase.Config = wg.default_config(root);
        end
    end

    methods (Test)
        function cutoffCatalogMatchesAnalyticFormula(testCase)
            cfg = testCase.Config;
            catalog = wg.enumerate_modes(cfg);
            expected = cfg.c0/2*sqrt((catalog.m/cfg.widthM).^2 + ...
                (catalog.n/cfg.heightM).^2);
            relativeError = abs(catalog.CutoffHz-expected)./expected;
            testCase.verifyLessThan(max(relativeError), 1e-10);
            testCase.verifyEqual(cfg.c0,299792458);
            testCase.verifyEqual(catalog.Status(catalog.Name == "TE02"), "propagating");
            testCase.verifyEqual(catalog.Status(catalog.Name == "TE40"), "propagating");
            testCase.verifyEqual(sum(catalog.Status == "propagating"),12);
            testCase.verifyEqual(catalog.CutoffGHz(catalog.Name == "TE02"), ...
                29.9792458,'AbsTol',1e-9);
        end

        function representativeModesHaveUnitPowerAndBoundaryConditions(testCase)
            cfg = testCase.Config;
            modeDefinitions = {"TE",1,0; "TE",1,1; "TM",1,1};
            for idx = 1:size(modeDefinitions,1)
                field = wg.mode_fields(cfg, modeDefinitions{idx,1}, ...
                    modeDefinitions{idx,2}, modeDefinitions{idx,3});
                testCase.verifyLessThan(abs(field.powerW-1), 1e-10);
                eScale = max(abs([field.Ex(:);field.Ey(:);field.Ez(:)]));
                xWallResidual = max(abs([field.Ey(:,[1 end]),field.Ez(:,[1 end])]),[],'all')/eScale;
                yWallResidual = max(abs([field.Ex([1 end],:),field.Ez([1 end],:)]),[],'all')/eScale;
                testCase.verifyLessThan(max(xWallResidual,yWallResidual), 1e-8);
            end
        end

        function propagatingModesArePowerOrthogonal(testCase)
            cfg = testCase.Config;
            modes = wg.propagating_modes(wg.enumerate_modes(cfg));
            fields = cell(height(modes),1);
            for idx = 1:height(modes)
                fields{idx} = wg.mode_fields(cfg,modes.Family(idx),modes.m(idx),modes.n(idx));
            end
            maximumError = 0;
            for row = 1:numel(fields)
                for col = 1:numel(fields)
                    overlap = 0.5*trapz(fields{row}.y,trapz(fields{row}.x, ...
                        fields{row}.Ex.*conj(fields{col}.Hy) - ...
                        fields{row}.Ey.*conj(fields{col}.Hx),2));
                    expected = double(row == col);
                    maximumError = max(maximumError,abs(overlap-expected));
                end
            end
            testCase.verifyLessThan(maximumError, 1e-6);
        end

        function directAndFftSolversAgree(testCase)
            cfg = testCase.Config;
            field = wg.mode_fields(cfg,"TE",1,0);
            theta = cfg.angles.cutDeg(:);
            for phiDeg = [0 90]
                phi = repmat(phiDeg,size(theta));
                direct = wg.farfield_direct(cfg,field,theta,phi);
                fftPattern = wg.farfield_fft(cfg,field,theta,phi);
                directPower = direct.power/max(direct.power);
                fftPower = fftPattern.power/max(fftPattern.power);
                rmse = sqrt(mean((directPower-fftPower).^2));
                directMetrics = wg.pattern_metrics(direct);
                fftMetrics = wg.pattern_metrics(fftPattern);
                testCase.verifyLessThan(rmse,cfg.validation.fftRmseLimit);
                testCase.verifyLessThanOrEqual(abs(directMetrics.PeakDirectionDeg- ...
                    fftMetrics.PeakDirectionDeg),cfg.validation.peakDirectionLimitDeg);
            end
        end

        function te10DefinesTheCoPolarReference(testCase)
            cfg = testCase.Config;
            field = wg.mode_fields(cfg,"TE",1,0);
            theta = (-20:0.5:20).';
            for phiDeg = [0 90]
                pattern = wg.farfield_direct(cfg,field,theta,repmat(phiDeg,size(theta)));
                ratio = max(abs(pattern.Ecross))/max(abs(pattern.Eco));
                testCase.verifyLessThan(ratio,1e-10);
            end
        end

        function teM0BroadsideParityMatchesApertureIntegral(testCase)
            cfg = testCase.Config;
            broadsidePower = zeros(3,1);
            for m = 1:3
                field = wg.mode_fields(cfg,"TE",m,0);
                pattern = wg.farfield_direct(cfg,field,0,0);
                broadsidePower(m) = pattern.power;
            end
            testCase.verifyGreaterThan(broadsidePower(1),0);
            testCase.verifyGreaterThan(broadsidePower(3),0);
            testCase.verifyLessThan(broadsidePower(2)/max(broadsidePower([1 3])),1e-12);
        end

        function hornMappingDegeneratesToStraightGuide(testCase)
            cfg = testCase.Config;
            geometry = struct('apertureWidthM',cfg.widthM, ...
                'apertureHeightM',cfg.heightM,'flareLengthM',80e-3);
            straight = wg.mode_fields(cfg,"TE",1,0);
            mapped = wg.horn_aperture_fields(cfg,"TE",1,0,geometry);
            testCase.verifyEqual(mapped.x,straight.x,'AbsTol',1e-14);
            testCase.verifyEqual(mapped.y,straight.y,'AbsTol',1e-14);
            testCase.verifyEqual(mapped.Ex,straight.Ex,'AbsTol',1e-12);
            testCase.verifyEqual(mapped.Ey,straight.Ey,'AbsTol',1e-12);
        end

        function hornModesRemainUnitPower(testCase)
            cfg = testCase.Config;
            geometry = struct('apertureWidthM',60e-3, ...
                'apertureHeightM',40e-3,'flareLengthM',100e-3);
            for definition = {"TE",1,0;"TE",1,1;"TM",1,1}.'
                field = wg.horn_aperture_fields(cfg,definition{1},definition{2},definition{3},geometry);
                testCase.verifyLessThan(abs(field.powerW-1),1e-10);
            end
        end

        function geometryConfigurationHasNineWidthPoints(testCase)
            cfg = testCase.Config;
            testCase.verifyEqual(cfg.optimization.halfWidthsDeg,5:2.5:25);
            testCase.verifyEqual(numel(cfg.optimization.halfWidthsDeg),9);
            testCase.verifyEqual(cfg.optimization.maxActiveModes,6);
        end

        function hornHalfAnglesMatchAnalyticGeometry(testCase)
            cfg = testCase.Config;
            geometry = struct('apertureWidthM',60e-3, ...
                'apertureHeightM',40e-3,'flareLengthM',100e-3);
            [angleX,angleY] = wg.horn_half_angles(cfg,geometry);
            testCase.verifyEqual(angleX,rad2deg(atan(0.04/0.2)),'AbsTol',1e-12);
            testCase.verifyEqual(angleY,rad2deg(atan(0.03/0.2)),'AbsTol',1e-12);
        end

        function pruningHonorsActiveModeLimit(testCase)
            cfg = testCase.Config;
            cfg.optimization.maxFunctionEvaluations = 120;
            modes = wg.propagating_modes(wg.enumerate_modes(cfg));
            basis = wg.build_pattern_basis(cfg,modes,(-30:2:30).',[90 0]);
            initial = wg.normalize_weights(ones(height(modes),1));
            result = wg.prune_and_refine(cfg,basis,initial,20,10,6);
            testCase.verifyLessThanOrEqual(nnz(abs(result.weights)>=1e-3),6);
            testCase.verifyEqual(angle(result.weights(1)),0,'AbsTol',1e-10);
        end

        function psoHistoryUsesMonotonicEvaluationCounts(testCase)
            cfg = testCase.Config;
            cfg.optimization.swarmSize = 10;
            cfg.optimization.maxIterations = 3;
            solution = wg.run_pso_solver(@(x)sum(x.^2),-ones(3,1),ones(3,1),cfg,0);
            testCase.verifyGreaterThanOrEqual(min(diff(solution.history(:,1))),0);
            testCase.verifyGreaterThanOrEqual(min(-diff(solution.history(:,2))),-1e-12);
        end

        function angularSpectrumDetectsOffAxisPeak(testCase)
            [u,v] = meshgrid(-0.8:0.4:0.8);
            power = ones(size(u));
            power(3,3) = 0.1;
            power(3,5) = 2;
            metrics = wg.angular_spectrum_metrics(power,u,v,20,20);
            testCase.verifyEqual(metrics.PeakThetaDeg,asind(0.8),'AbsTol',1e-12);
            testCase.verifyEqual(metrics.BoresightRelativeDb,10*log10(0.05),'AbsTol',1e-12);
            testCase.verifyEqual(metrics.OutsideDiskDb,0,'AbsTol',1e-12);
            testCase.verifyEqual(metrics.MainDiskRippleDb,0,'AbsTol',1e-12);
        end
    end
end
