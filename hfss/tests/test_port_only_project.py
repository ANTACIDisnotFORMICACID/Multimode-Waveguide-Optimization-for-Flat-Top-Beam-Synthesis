"""Ensure the saved AEDT setup type, not a Python property, is checked."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_port_only_gui_project import persisted_setup_section


class PortOnlyProjectTests(unittest.TestCase):
    def test_native_ports_only_serialization(self):
        project = ("$begin 'PortOnly30GHz'\n"
                   "SolveType='PortsOnly'\nSaveAnyFields=true\n"
                   "$end 'PortOnly30GHz'")
        section = persisted_setup_section(project, "PortOnly30GHz")
        self.assertIn("SolveType='PortsOnly'", section)
        self.assertIn("SaveAnyFields=true", section)

    def test_in_memory_flag_does_not_prove_saved_setup(self):
        project = ("$begin 'PortOnly30GHz'\n"
                   "SolveType='Single'\n$end 'PortOnly30GHz'")
        section = persisted_setup_section(project, "PortOnly30GHz")
        self.assertNotIn("SolveType='PortsOnly'", section)
        self.assertEqual(persisted_setup_section(project, "Missing"), "")


if __name__ == "__main__":
    unittest.main()
