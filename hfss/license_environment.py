"""Pass existing Windows Ansys environment settings to AEDT child processes.

Some automation shells omit the user/machine environment despite the settings
being configured in Windows. No license value is logged or persisted here.
"""

from __future__ import annotations

import os


def restore_ansys_environment() -> dict[str, str]:
    import winreg

    restored: dict[str, str] = {}
    names = ("ANSYSEM_ROOT252", "ANSYSLMD_LICENSE_FILE")
    sources = (
        ("machine", winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ("user", winreg.HKEY_CURRENT_USER, "Environment"),
    )
    for name in names:
        if os.environ.get(name):
            continue
        for label, hive, key_path in sources:
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, name)
            except OSError:
                continue
            if value:
                os.environ[name] = os.path.expandvars(str(value))
                restored[name] = label
                break
    return restored
