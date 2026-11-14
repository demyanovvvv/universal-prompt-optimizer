"""Registered desktop discovery without touching the user's registry or disk installs."""

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from installer.detection import _windows_harness_installation, detect_agents


class RegistryKey:
    def __init__(self, values):
        self.values = values

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class RegisteredHarnessTests(unittest.TestCase):
    def registry(self, entries, *, hive=2, view=32):
        def open_key(parent, name, reserved=0, access=0):
            if isinstance(parent, RegistryKey):
                return RegistryKey(parent.values[int(name)])
            if parent != hive or access != (1 | view):
                raise PermissionError("unavailable registry view")
            return RegistryKey(entries)

        def query_value(key, name):
            try:
                return key.values[name], 1
            except KeyError:
                raise FileNotFoundError(name)

        return types.SimpleNamespace(
            HKEY_CURRENT_USER=1, HKEY_LOCAL_MACHINE=2,
            KEY_WOW64_64KEY=64, KEY_WOW64_32KEY=32, KEY_READ=1,
            OpenKey=open_key,
            QueryInfoKey=lambda key: (len(key.values), 0, 0),
            EnumKey=lambda key, index: str(index),
            QueryValueEx=query_value,
        )

    def test_custom_installation_is_detected_and_selected_for_global_update(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            home = base / "home"
            app = base / "custom drive" / "DeepSeek Harness"
            app.mkdir(parents=True)
            executable = app / "DeepSeek Harness.exe"
            executable.touch()
            registry = self.registry([{
                "DisplayName": "DeepSeek Harness 0.2.0-rc.2",
                "InstallLocation": str(app),
            }])
            with patch.dict(sys.modules, {"winreg": registry}), \
                    patch("installer.detection.shutil.which", return_value=None), \
                    patch.dict(os.environ, {}, clear=True), \
                    patch.object(Path, "home", return_value=home), \
                    patch("builtins.print"):
                detected = detect_agents(home)
                args = types.SimpleNamespace(agents=None, detect_agents=False, scope="global")
                selected = install.requested_agents(
                    args, previous={"adapters": ["omp"]}, root=home, uninstall=False)
            self.assertEqual(detected, {"deepseek-harness": f"registered application: {app}"})
            self.assertEqual(selected, {"omp", "deepseek-harness"})
            self.assertFalse(home.exists())
            self.assertEqual(list(app.iterdir()), [executable])

    def test_display_icon_handles_quoted_paths_with_commas_and_icon_index(self):
        with tempfile.TemporaryDirectory() as raw:
            app = Path(raw) / "custom, application"
            app.mkdir()
            executable = app / "DeepSeek Harness.exe"
            executable.touch()
            registry = self.registry([{
                "DisplayName": "DeepSeek Harness",
                "DisplayIcon": f'"{executable}",-1',
            }], hive=1, view=64)
            with patch.dict(sys.modules, {"winreg": registry}):
                self.assertEqual(_windows_harness_installation(), executable)

    def test_stale_or_unrelated_registration_does_not_select_harness(self):
        with tempfile.TemporaryDirectory() as raw:
            app = Path(raw)
            (app / "Uninstall DeepSeek Harness.exe").touch()
            registry = self.registry([
                {"DisplayName": "DeepSeek Harness", "InstallLocation": str(app)},
                {"DisplayName": "DeepSeek Harness", "DisplayIcon": str(app / "Uninstall DeepSeek Harness.exe")},
                {"DisplayName": "Unrelated Harness", "InstallLocation": str(app)},
                {"DisplayName": None, "InstallLocation": str(app)},
            ])
            with patch.dict(sys.modules, {"winreg": registry}):
                self.assertIsNone(_windows_harness_installation())

    def test_missing_windows_registry_module_is_ignored(self):
        with patch.dict(sys.modules, {"winreg": None}):
            self.assertIsNone(_windows_harness_installation())


if __name__ == "__main__":
    unittest.main()
