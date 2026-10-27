# -*- coding: utf-8 -*-
"""Export 12-mode vector cuts from the solved 15-pass setup inside AEDT GUI."""

from __future__ import print_function

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_solved_in_gui as exporter

# AEDT injects oDesktop into the executed script's global namespace, not into
# imported modules. Pass the live GUI object explicitly to the exporter.
exporter.oDesktop = oDesktop
exporter.SETUP = "PowerCheck30GHz : LastAdaptive"
exporter.PORT_MODES = 12
exporter.INCLUDE_PORT_POST_PROCESSING = False
exporter.main()
