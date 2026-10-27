# 12-mode analytical-model rerun (2026-10-25)

This directory preserves a complete, independently generated MATLAB run after
the 20 × 10 mm, 30 GHz feed catalog was corrected to include all **12** modes
with analytic cutoff frequencies below 30 GHz. It is a separate study, **not**
an HFSS-validated replacement for the repository's 10-mode paper figures.

The deterministic geometry scan selected a 60 × 20 mm aperture with a 60 mm
flare and a 20° transition. The subsequent 20°-half-width optimization used
six modes (TE10, TE20, TE30, TE31, TM31, TE40). Its worst E/H-plane main-region
ripple was 1.073 dB; the maximum radiation outside the transition was
−9.418 dB. The H-plane HPBW increased from 32.447° for the straight TE10
baseline to 44.338°. These values are analytical-model predictions, not
full-wave performance claims. The 12-mode MATLAB core tests passed 13/13
after adding the two-dimensional angular-metric check;
direct integration versus FFT power RMSE was 2.94e−7 (E) and 7.18e−8 (H).

**Two-dimensional angular check:** the E/H-plane objective does not control
intermediate azimuths. On the sampled direction-cosine grid
`|u|, |v| <= 0.8`, the six-mode solution peaks at approximately
`theta=21.85°`, `phi=−49.84°`; boresight is 7.52 dB below that peak. The
power ripple over the full `theta<=20°` disk is 16.81 dB, and the strongest
sample beyond `theta=40°` is only 6.69 dB below the global peak. Consequently,
the two attractive principal-plane curves do **not** establish a genuine
two-dimensional flat-top beam. The complete numerical result is in
`tables/aperture_spectrum_summary.csv` and `figures/07_modal_composition.*`.
The method needs a two-dimensional angular objective before its multimode
pattern can be promoted as a flat-top design.

The inclusion of near-cutoff TE40 is important: its optimized weight is only
about 0.063 in amplitude. An earlier HFSS report suggested almost complete
reflection at the corresponding candidate port, but that S parameter used a
50-ohm renormalized reference. The intrinsic modal AcceptedPower is different;
the two references cannot be interpreted as the same physical input. Geometry
and modal phase references therefore need to be resolved before a valid coherent
full-wave comparison. A separate 60 × 20 × 60 mm HFSS model has been built;
it had not been solved as of this MATLAB-only study snapshot. A later
2026-10-27 same-geometry HFSS solve and single-mode comparison are recorded
in `../../hfss/twelve_mode_60x20x60_native_import_20261027/` and
`../../hfss/twelve_mode_60x20x60_phase_sensitivity_20261027/`. The full-wave
H-plane result differs strongly from the ideal aperture assumption, so this
snapshot's six-mode optimum is not a validated full-wave design.

`tables/` contains the unfiltered scan, optimization, convergence, weights,
numerical validation and summary CSV files. `figures/` contains all 12
automatically generated PNG/PDF figure pairs, including negative tradeoffs;
they have not been substituted into the main README. The MATLAB-only run did
not attempt HFSS, so its empty HFSS status table was deliberately not copied.

Reproduction from the repository root in MATLAB:

```matlab
addpath(pwd, fullfile(pwd, 'matlab'));
cfg = wg.default_config(pwd);
cfg.resultsDir = fullfile(tempdir, 'waveguide_12mode_reproduction');
run_tests;
run_baseline(cfg);
run_geometry_scan(cfg);
run_optimization(cfg);
run_validation(cfg);
```
