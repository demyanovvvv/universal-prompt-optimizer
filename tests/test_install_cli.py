import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install

ROOT = Path(__file__).resolve().parents[1]


class InstallCliTests(unittest.TestCase):
    def run_interactive(self, args, answers, home):
        output = io.StringIO()
        output.isatty = lambda: True
        with patch.object(sys, "argv", ["install.py", *args]), \
                patch.object(sys.stdin, "isatty", return_value=True), \
                patch.object(sys.stdout, "isatty", return_value=True), \
                patch("builtins.input", side_effect=answers), \
                patch.object(Path, "home", return_value=home), \
                contextlib.redirect_stdout(output):
            install.main()
        return output.getvalue()

    def test_install_and_uninstall_offer_global_scope_without_project_prompt(self):
        for action in ([], ["--uninstall"]):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as raw:
                home = Path(raw)
                output = self.run_interactive([*action, "--dry-run"], ["2"], home)
                self.assertIn("scope: global", output)
                self.assertFalse(any(home.iterdir()))

    def test_local_uninstall_accepts_project_path_and_cancel(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = self.run_interactive(["--uninstall", "--dry-run", "--lang", "ru"], ["1", str(root)], root)
            self.assertIn("область установки: проект", output)
            self.assertIn(str(root), output)
            self.assertFalse(any(root.iterdir()))
            self.run_interactive(["--uninstall"], ["q"], root)
            self.assertFalse(any(root.iterdir()))

    def test_yes_and_explicit_scope_do_not_read_input(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for options in (["--yes"], ["--scope", "project"]):
                with self.subTest(options=options):
                    self.run_interactive(["--project", str(root), "--dry-run", *options], [], root)
            self.assertFalse(any(root.iterdir()))

    def test_uninstall_entry_point_removes_installation_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            args = ["--scope", "project", "--project", str(root), "--yes"]
            subprocess.run([sys.executable, "-B", str(ROOT / "install.py"), *args,
                            "--agents", "all", "--auto"], capture_output=True, text=True, check=True)
            for _ in range(2):
                subprocess.run([sys.executable, "-B", str(ROOT / "uninstall.py"), *args],
                               capture_output=True, text=True, check=True)
            self.assertFalse(any(p.is_file() for p in root.rglob("*")))

    def test_update_keeps_settings_and_reports_previous_version(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            args = [sys.executable, "-B", str(ROOT / "install.py"), "--scope", "project", "--project", str(root)]
            subprocess.run([*args, "--agents", "all", "--auto", "--behavior", "preview",
                            "--prompt-scope", "first", "--quality-gate", "light", "--unsupported-model", "skip"],
                           capture_output=True, text=True, check=True)
            state_path = root / ".prompt-optimizer-install.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["version"] = "5.0.0"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            result = subprocess.run(args, capture_output=True, text=True, check=True)
            self.assertIn("5.0.0", result.stdout)
            config = json.loads((root / ".prompt-optimizer.json").read_text(encoding="utf-8"))
            self.assertEqual((config["behavior"], config["scope"], config["qualityGate"], config["unsupportedModel"]),
                             ("preview", "first", "light", "skip"))
            self.assertTrue((root / ".opencode/plugins/prompt-optimizer/index.ts").exists())

    def test_bash_update_preserves_settings_and_removal_does_not_run_install_wizard(self):
        bash = shutil.which("bash")
        if os.name == 'nt' and Path("C:/Program Files/Git/bin/bash.exe").exists():
            bash = "C:/Program Files/Git/bin/bash.exe"
        if not bash:
            self.skipTest("Bash is unavailable")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            args = [bash, str(ROOT / "install.sh"), "--scope", "project", "--project", str(root), "--yes"]
            env = {**os.environ, "PYTHON_BIN": sys.executable}
            subprocess.run([*args, "--agents", "all", "--auto", "--behavior", "preview", "--quality-gate", "light"],
                           capture_output=True, text=True, check=True, env=env)
            subprocess.run(args, capture_output=True, text=True, check=True, env=env)
            config = json.loads((root / ".prompt-optimizer.json").read_text(encoding="utf-8"))
            self.assertEqual((config["behavior"], config["qualityGate"]), ("preview", "light"))
            run = subprocess.run([bash, str(ROOT / "uninstall.sh"), "--interactive", "--scope", "project",
                                  "--project", str(root), "--yes"], capture_output=True, text=True, check=True, env=env)
            self.assertNotIn("Agent auto-detection", run.stdout)
            self.assertFalse(any(p.is_file() for p in root.rglob("*")))


if __name__ == "__main__":
    unittest.main()
