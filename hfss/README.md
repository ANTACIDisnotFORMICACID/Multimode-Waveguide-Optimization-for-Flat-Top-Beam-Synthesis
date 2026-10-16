# HFSS automation

`preflight.py` checks the local AEDT/PyAEDT installation without claiming a
solver result. `build_and_solve.py` creates a 20 mm × 10 mm, 80 mm long PEC
waveguide, a ten-mode driven-modal port, a 30 GHz adaptive setup, a PML open
region, and an infinite-sphere far-field setup.

```powershell
D:\Miniconda3\python.exe hfss\preflight.py --project-root .
D:\Miniconda3\python.exe hfss\build_and_solve.py --project-root . --solve
```

The durable run state is `results/hfss/hfss_status.json`. A `BLOCKED` state is
not a validation pass. Port eigenmodes with degenerate cutoff frequencies are
exported with neutral `PortMode` labels; they must be matched to analytical
TE/TM fields before a multimode excitation is accepted.
