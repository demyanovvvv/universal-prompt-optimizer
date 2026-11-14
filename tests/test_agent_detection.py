"""Regression tests for read-only agent detection and its CLI wiring.

Contract under test (parent-owned installer behavior):

* One canonical detector in ``installer/detection`` exposes ``AGENT_NAMES`` and
  ``detect_agents(home, *, project=None)``. It performs local read-only
  detection via ``PATH`` commands and known home/app configuration directories
  and never launches or downloads agents.
* A global install without ``--agents`` selects the union of detected agents
  and previously recorded adapter IDs; project installs keep the saved
  selection (``all`` for a first install); explicit ``--agents`` stays exact.
* Zero detected and zero recorded agents on a global install fails before any
  write instead of falling back to install-all.
* ``--list-agents`` is read-only; uninstall/doctor never consult detection.
* The Bash front end delegates detection to the same Python detector.

Bash end-to-end cases run Git Bash with an isolated HOME/USERPROFILE and PATH;
Python CLI cases run subprocesses with a scrubbed environment or patch
``install.detect_agents`` for in-process ``main()`` coverage.
"""
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
from unittest.mock import MagicMock, call, patch

import install
from installer.detection import AGENT_NAMES, CONFIG_REASON, APP_REASON, detect_agents

ROOT = Path(__file__).resolve().parents[1]


def write_executable(directory: Path, name: str) -> None:
    """Create a command discoverable on PATH without ever executing it."""
    path = directory / (f"{name}.cmd" if os.name == "nt" else name)
    path.write_text("", encoding="utf-8")
    path.chmod(0o755)


def isolated_registry_path(directory: Path) -> str:
    """Disable the real user's Windows registry only in fixture subprocesses."""
    startup = directory / "sitecustomize.py"
    startup.write_text("import sys\nsys.modules['winreg'] = None\n", encoding="utf-8")
    return str(directory)


def cli_env(home: Path, bin_dir: Path) -> dict:
    """Environment for Python installer subprocesses with no ambient leakage."""
    return {
        "PATH": str(bin_dir),
        "PYTHONPATH": isolated_registry_path(bin_dir),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PATHEXT": os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD"),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
        "TEMP": os.environ.get("TEMP", tempfile.gettempdir()),
        "TMP": os.environ.get("TMP", tempfile.gettempdir()),
        "HOME": str(home),
        "USERPROFILE": str(home),
    }


def run_installer(args, env, cwd=None):
    return subprocess.run(
        [sys.executable, "-B", str(ROOT / "install.py"), *args],
        capture_output=True, text=True, env=env, cwd=cwd or ROOT, check=False,
    )


class DetectionBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        registry = patch("installer.detection._windows_harness_installation", return_value=None)
        registry.start()
        self.addCleanup(registry.stop)
        base = Path(self._tmp.name)
        self.home = base / "home"
        self.project = base / "project"
        self.empty_bin = base / "empty-bin"
        for directory in (self.home, self.project, self.empty_bin):
            directory.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def detect(self, home, project=None, **environment):
        """Run detect_agents with a scrubbed environment and launch guards."""
        values = {"PATH": str(self.empty_bin),
                  "PATHEXT": os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")}
        values.update({key: str(value) for key, value in environment.items()})
        launch = MagicMock(side_effect=AssertionError("detection must not launch processes"))
        with patch.dict(os.environ, values, clear=True), \
                patch.multiple(subprocess, Popen=launch, run=launch, call=launch,
                               check_call=launch, check_output=launch), \
                patch("os.system", launch), patch("os.posix_spawn", launch, create=True):
            return detect_agents(home, project=project)


class DetectAgentsContractTests(DetectionBase):
    def test_agent_names_match_adapter_manifest_order(self):
        manifest = json.loads((ROOT / "adapters" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(list(AGENT_NAMES), manifest["adapters"])
        self.assertEqual(AGENT_NAMES["deepseek-harness"], "DeepSeek Harness")
        self.assertEqual(AGENT_NAMES["copilot"], "GitHub Copilot CLI")

    def test_global_detection_ignores_project_directories(self):
        for name in (".opencode", ".codex", ".pi", ".omp", ".claude", ".gemini",
                     ".windsurf", ".cursor", ".copilot", ".dsh"):
            (self.project / name).mkdir()
        detected = self.detect(self.home)
        self.assertEqual(detected, {})
        # Read-only: nothing appeared in home during detection.
        self.assertEqual(list(self.home.iterdir()), [])

    def test_global_detection_reads_home_config_directories(self):
        (self.home / ".config" / "opencode").mkdir(parents=True)
        (self.home / ".codex").mkdir()
        detected = self.detect(self.home)
        self.assertEqual(detected, {"opencode": CONFIG_REASON, "codex": CONFIG_REASON})
        alt_home = self.home.parent / "home-alt"
        (alt_home / ".config" / "codex").mkdir(parents=True)
        self.assertEqual(self.detect(alt_home), {"codex": CONFIG_REASON})

    def test_project_detection_includes_project_directories(self):
        (self.home / ".config" / "opencode").mkdir(parents=True)
        for name in (".opencode", ".codex", ".pi", ".omp", ".claude", ".gemini"):
            (self.project / name).mkdir()
        for name in (".windsurf", ".cursor", ".copilot", ".dsh"):
            (self.project / name).mkdir()
        detected = self.detect(self.home, project=self.project)
        self.assertEqual(detected, {
            "opencode": CONFIG_REASON, "codex": CONFIG_REASON, "cursor": APP_REASON,
            "pi": CONFIG_REASON, "omp": CONFIG_REASON, "claude": CONFIG_REASON,
            "gemini": CONFIG_REASON, "copilot": CONFIG_REASON, "windsurf": APP_REASON,
            "deepseek-harness": CONFIG_REASON,
        })

    def test_path_commands_are_detected_for_every_agent(self):
        bin_dir = self.home.parent / "commands-bin"
        bin_dir.mkdir()
        for name in ("opencode", "codex", "cursor", "pi", "omp", "claude",
                     "gemini", "copilot", "windsurf", "dsh"):
            write_executable(bin_dir, name)
        detected = self.detect(self.home, PATH=str(bin_dir))
        self.assertEqual(detected, {
            "opencode": "command: opencode", "codex": "command: codex",
            "cursor": "command: cursor", "pi": "command: pi",
            "omp": "command: omp", "claude": "command: claude",
            "gemini": "command: gemini", "copilot": "command: copilot",
            "windsurf": "command: windsurf", "deepseek-harness": "command: dsh",
        })

    def test_windows_command_lookup_uses_pathext_extensions(self):
        if os.name != "nt":
            self.skipTest("Windows-only command lookup via PATHEXT")
        bin_dir = self.home.parent / "win-bin"
        (bin_dir / "omp.cmd").parent.mkdir(parents=True)
        (bin_dir / "omp.cmd").write_text("", encoding="utf-8")
        (bin_dir / "github-copilot-cli.cmd").write_text("", encoding="utf-8")
        # A different agent must stay undetected when only its extensionless
        # file exists: Windows lookup resolves through PATHEXT, not bare names.
        (bin_dir / "pi").write_text("", encoding="utf-8")
        detected = self.detect(self.home, PATH=str(bin_dir))
        self.assertEqual(detected, {"omp": "command: omp",
                                    "copilot": "command: github-copilot-cli"})

    def test_deepseek_harness_alternate_command_name(self):
        bin_dir = self.home.parent / "dsh-bin"
        bin_dir.mkdir()
        write_executable(bin_dir, "deepseek-harness")
        detected = self.detect(self.home, PATH=str(bin_dir))
        self.assertEqual(detected, {"deepseek-harness": "command: deepseek-harness"})

    def test_windows_appdata_and_localappdata_directories(self):
        appdata = self.home.parent / "appdata"
        localappdata = self.home.parent / "localappdata"
        (appdata / "Cursor").mkdir(parents=True)
        (appdata / "Windsurf").mkdir(parents=True)
        (localappdata / "Programs" / "cursor").mkdir(parents=True)
        detected = self.detect(self.home, APPDATA=appdata, LOCALAPPDATA=localappdata)
        self.assertEqual(detected, {"cursor": APP_REASON, "windsurf": APP_REASON})

    def test_macos_application_support_directories(self):
        support = self.home / "Library" / "Application Support"
        (support / "Cursor").mkdir(parents=True)
        (support / "Windsurf").mkdir(parents=True)
        self.assertEqual(self.detect(self.home), {"cursor": APP_REASON, "windsurf": APP_REASON})

    def test_deepseek_harness_uses_dsh_home(self):
        dsh_home = self.home.parent / "dsh-home"
        dsh_home.mkdir()
        self.assertEqual(self.detect(self.home, DSH_HOME=dsh_home),
                         {"deepseek-harness": CONFIG_REASON})
        missing = self.home.parent / "dsh-missing"
        self.assertEqual(self.detect(self.home, DSH_HOME=missing), {})
        (self.home / ".deepseek-harness").mkdir()
        self.assertEqual(self.detect(self.home, DSH_HOME=missing),
                         {"deepseek-harness": CONFIG_REASON})

    def test_empty_environment_detects_nothing(self):
        self.assertEqual(self.detect(self.home), {})
        self.assertEqual(self.detect(self.home, project=self.project), {})


class InstallerCliDetectionTests(DetectionBase):
    """Subprocess CLI coverage with a scrubbed environment (real detector)."""

    def make_bin(self, *names):
        bin_dir = self.home.parent / "cli-bin"
        bin_dir.mkdir(exist_ok=True)
        for name in names:
            write_executable(bin_dir, name)
        return bin_dir

    def read_state(self, home, scope):
        path = home / (".prompt-optimizer-install.json" if scope == "project"
                       else ".config/prompt-optimizer/install.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_global_first_install_selects_only_detected_agents(self):
        bin_dir = self.make_bin("omp")
        env = cli_env(self.home, bin_dir)
        result = run_installer(["--scope", "global", "--yes", "--auto"], env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agents: omp", result.stdout)
        self.assertIn("[x] OMP", result.stdout)
        self.assertIn("command: omp", result.stdout)
        self.assertIn("[ ] DeepSeek Harness", result.stdout)
        state = self.read_state(self.home, "global")
        self.assertEqual(state["adapters"], ["omp"])
        self.assertTrue((self.home / ".omp/agent/extensions/prompt-optimizer/index.ts").exists())
        self.assertFalse((self.home / ".dsh").exists())

    def test_global_update_adds_harness_and_retains_recorded_settings_and_config(self):
        bin_dir = self.make_bin("omp")
        first = run_installer(["--scope", "global", "--yes", "--agents", "omp,pi", "--auto",
                               "--behavior", "preview", "--quality-gate", "light"],
                              cli_env(self.home, bin_dir))
        self.assertEqual(first.returncode, 0, first.stderr)
        config_path = self.home / ".config/prompt-optimizer/config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["userNote"] = "keep-me"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        # The newly available Harness command appears only now.
        write_executable(bin_dir, "dsh")
        second = run_installer(["--scope", "global", "--yes"], cli_env(self.home, bin_dir))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("agents: deepseek-harness, omp, pi", second.stdout)
        state = self.read_state(self.home, "global")
        self.assertEqual(state["adapters"], ["deepseek-harness", "omp", "pi"])
        self.assertTrue(state["automatic"])
        self.assertTrue((self.home / ".dsh/skills/prompt-optimizer/SKILL.md").exists())
        self.assertTrue((self.home / ".dsh/plugins/prompt-optimizer/index.mjs").exists())
        self.assertTrue((self.home / ".omp/agent/extensions/prompt-optimizer/index.ts").exists())
        self.assertTrue((self.home / ".pi/agent/extensions/prompt-optimizer.ts").exists())
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual((config["behavior"], config["qualityGate"], config["userNote"]),
                         ("preview", "light", "keep-me"))

    def test_explicit_agents_does_not_auto_add_detected_agents(self):
        bin_dir = self.make_bin("omp", "dsh")
        result = run_installer(["--scope", "global", "--yes", "--auto",
                                "--agents", "deepseek-harness"],
                               cli_env(self.home, bin_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agents: deepseek-harness", result.stdout)
        self.assertNotIn("agents: deepseek-harness, omp", result.stdout)
        # An explicit selection skips the detection scan entirely.
        self.assertNotIn("Agent detection:", result.stdout)
        state = self.read_state(self.home, "global")
        self.assertEqual(state["adapters"], ["deepseek-harness"])
        self.assertFalse((self.home / ".omp").exists())

    def test_global_zero_detection_fails_before_writes(self):
        result = run_installer(["--scope", "global", "--yes"],
                               cli_env(self.home, self.empty_bin))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No supported agent is detectable or recorded", result.stdout + result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_detect_agents_project_scope_uses_home_and_project(self):
        bin_dir = self.make_bin("omp")
        (self.home / ".cursor").mkdir()
        (self.project / ".pi").mkdir()
        result = run_installer(["--scope", "project", "--project", str(self.project),
                                "--yes", "--detect-agents"],
                               cli_env(self.home, bin_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agents: cursor, omp, pi", result.stdout)
        state = self.read_state(self.project, "project")
        self.assertEqual(state["adapters"], ["cursor", "omp", "pi"])
        self.assertTrue((self.project / ".agents/skills/prompt-optimizer/SKILL.md").exists())

    def test_project_default_selection_stays_all_agents(self):
        result = run_installer(["--scope", "project", "--project", str(self.project), "--yes"],
                               cli_env(self.home, self.empty_bin))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("agents: claude, codex, copilot, cursor, deepseek-harness, "
                      "gemini, omp, opencode, pi, windsurf", result.stdout)
        state = self.read_state(self.project, "project")
        self.assertEqual(state["adapters"], sorted(AGENT_NAMES))
        self.assertTrue((self.project / ".agents/skills/prompt-optimizer/SKILL.md").exists())

    def test_list_agents_is_read_only_and_global_ignores_cwd(self):
        (self.home / ".config" / "opencode").mkdir(parents=True)
        (self.project / ".cursor").mkdir()
        (self.project / ".codex").mkdir()
        result = run_installer(["--list-agents", "--scope", "global"],
                               cli_env(self.home, self.empty_bin), cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[x] OpenCode", result.stdout)
        self.assertIn("[ ] OpenAI Codex", result.stdout)
        self.assertIn("[ ] Cursor", result.stdout)
        self.assertEqual([entry.name for entry in self.home.iterdir()], [".config"])
        self.assertEqual(sorted(entry.name for entry in self.project.iterdir()),
                         [".codex", ".cursor"])

    def test_list_agents_project_scope_reads_project_directories(self):
        (self.project / ".pi").mkdir()
        result = run_installer(["--list-agents", "--scope", "project",
                                "--project", str(self.project)],
                               cli_env(self.home, self.empty_bin), cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[x] Pi", result.stdout)
        self.assertIn("[ ] OMP", result.stdout)
        self.assertEqual([entry.name for entry in self.project.iterdir()], [".pi"])

    def test_list_agents_rejects_mutating_flags(self):
        result = run_installer(["--list-agents", "--scope", "global", "--uninstall"],
                               cli_env(self.home, self.empty_bin))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--list-agents is read-only", result.stdout + result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])


class InstallerCliPatchedDetectionTests(unittest.TestCase):
    """In-process main() coverage with the backend detector patched out."""

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

    def test_global_default_uses_detection_result_for_first_install(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            detector = MagicMock(return_value={"omp": "command: omp"})
            with patch("install.detect_agents", detector):
                output = self.run_interactive(["--scope", "global", "--dry-run"], [], home)
            self.assertIn("agents: omp", output)
            self.assertIn("[x] OMP", output)
            self.assertIn("command: omp", output)
            self.assertIn("[ ] DeepSeek Harness", output)
            self.assertEqual(detector.call_count, 1)
            self.assertEqual(detector.call_args, call(home, project=None))
            self.assertFalse(any(home.iterdir()))

    def test_global_union_uses_one_detection_call_with_saved_adapters(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            # A pre-recorded global installation: previous adapters survive.
            state = home / ".config/prompt-optimizer/install.json"
            state.parent.mkdir(parents=True)
            state.write_text(json.dumps({
                "schema": 1, "scope": "global", "version": "5.0.0",
                "adapters": ["pi"], "automatic": True,
                "settings": {"behavior": "preview", "prompt_scope": "first",
                             "quality_gate": "light", "unsupported_model": "skip"},
                "files": [], "created_configs": [],
            }), encoding="utf-8")
            detector = MagicMock(return_value={"omp": "command: omp"})
            with patch("install.detect_agents", detector):
                output = self.run_interactive(["--scope", "global", "--dry-run"], [], home)
            self.assertIn("agents: omp, pi", output)
            self.assertIn("auto integration: on", output)
            self.assertIn("behavior: preview; prompt scope: first; quality gate: light", output)
            self.assertEqual(detector.call_count, 1)
            self.assertEqual(detector.call_args, call(home, project=None))

    def test_uninstall_does_not_consult_detection(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            detector = MagicMock(return_value={})
            with patch("install.detect_agents", detector):
                output = self.run_interactive(["--uninstall", "--dry-run"], ["2"], home)
            self.assertIn("scope: global", output)
            self.assertIn("agents: " + ", ".join(sorted(AGENT_NAMES)), output)
            detector.assert_not_called()
            self.assertFalse(any(home.iterdir()))

    def test_doctor_does_not_consult_detection(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            detector = MagicMock(return_value={})
            with patch("install.detect_agents", detector), \
                    self.assertRaises(SystemExit):
                self.run_interactive(["--scope", "global", "--doctor"], [], home)
            detector.assert_not_called()
            self.assertFalse(any(home.iterdir()))

    def test_explicit_agents_skips_detection(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            detector = MagicMock(return_value={"omp": "command: omp"})
            with patch("install.detect_agents", detector):
                output = self.run_interactive(
                    ["--scope", "global", "--dry-run", "--agents", "omp"], [], home)
            self.assertIn("agents: omp", output)
            self.assertNotIn("Agent detection:", output)
            detector.assert_not_called()

    def test_global_zero_detection_without_previous_fails_before_writes(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            detector = MagicMock(return_value={})
            with patch("install.detect_agents", detector), \
                    self.assertRaises(SystemExit) as caught:
                self.run_interactive(["--scope", "global", "--yes"], [], home)
            self.assertIn("No supported agent is detectable or recorded", str(caught.exception))
            self.assertEqual(detector.call_count, 1)
            self.assertEqual(detector.call_args, call(home, project=None))
            self.assertEqual(list(home.iterdir()), [])

    def test_list_agents_is_read_only_without_invoking_the_installer(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            detector = MagicMock(return_value={"omp": "command: omp"})
            with patch("install.detect_agents", detector), \
                    patch("install.install_global") as install_global:
                output = self.run_interactive(
                    ["--scope", "global", "--list-agents"], [], home)
            self.assertIn("[x] OMP", output)
            self.assertIn("[ ] DeepSeek Harness", output)
            self.assertIn("not detected", output)
            self.assertEqual(detector.call_count, 1)
            self.assertEqual(detector.call_args, call(home, project=None))
            install_global.assert_not_called()
            self.assertFalse(any(home.iterdir()))


def bash_command_path(bash):
    """Directories the Bash front end itself needs (tr/dirname/python)."""
    bash = Path(bash).resolve()
    if os.name == "nt":
        # Git for Windows layout: <root>/bin/bash.exe with tools in <root>/usr/bin.
        root = bash.parents[1]
        return [root / "usr" / "bin", root / "bin"]
    return [bash.parent]


def find_git_bash():
    if os.name != "nt":
        return shutil.which("bash")
    for candidate in ("C:/Program Files/Git/bin/bash.exe",
                      "C:/Program Files (x86)/Git/bin/bash.exe"):
        if Path(candidate).exists():
            return candidate
    return None


class InstallerBashDetectionTests(DetectionBase):
    """Bash end-to-end coverage with isolated HOME/USERPROFILE and PATH."""

    BASH = find_git_bash()

    def setUp(self):
        super().setUp()
        if self.BASH is None:
            self.skipTest("Bash is unavailable")
        self.bash_path = bash_command_path(self.BASH)

    def bash_env(self, bin_dir, extra=None):
        entries = [str(path) for path in [*self.bash_path, bin_dir]]
        env = {
            "PATH": os.pathsep.join(entries),
            "PYTHONPATH": isolated_registry_path(bin_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "PYTHON_BIN": Path(sys.executable).as_posix(),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
            "TEMP": os.environ.get("TEMP", tempfile.gettempdir()),
            "TMP": os.environ.get("TMP", tempfile.gettempdir()),
        }
        env.update(extra or {})
        return env

    def run_bash(self, args, env, cwd=None):
        return subprocess.run([self.BASH, str(ROOT / "install.sh"), *args],
                              capture_output=True, text=True, env=env,
                              cwd=cwd or ROOT, check=False)

    def read_state(self):
        return json.loads((self.home / ".config/prompt-optimizer/install.json")
                          .read_text(encoding="utf-8"))

    def test_bash_global_default_installs_detected_and_update_adds_harness(self):
        bin_dir = self.home.parent / "bash-bin"
        bin_dir.mkdir()
        write_executable(bin_dir, "omp")
        first = self.run_bash(["--scope", "global", "--yes", "--behavior", "preview",
                               "--quality-gate", "light"],
                              self.bash_env(bin_dir))
        self.assertEqual(first.returncode, 0, first.stderr)
        state = self.read_state()
        self.assertEqual(state["adapters"], ["omp"])
        self.assertTrue((self.home / ".omp/agent/extensions/prompt-optimizer/index.ts").exists())
        # The Harness command becomes available only after the first install.
        write_executable(bin_dir, "dsh")
        second = self.run_bash(["--scope", "global", "--yes"], self.bash_env(bin_dir))
        self.assertEqual(second.returncode, 0, second.stderr)
        state = self.read_state()
        self.assertEqual(state["adapters"], ["deepseek-harness", "omp"])
        self.assertTrue((self.home / ".dsh/skills/prompt-optimizer/SKILL.md").exists())
        self.assertTrue((self.home / ".dsh/plugins/prompt-optimizer/index.mjs").exists())
        self.assertTrue((self.home / ".omp/agent/extensions/prompt-optimizer/index.ts").exists())
        config = json.loads((self.home / ".config/prompt-optimizer/config.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual((config["behavior"], config["qualityGate"]), ("preview", "light"))
        # Recorded adapters survive an update run where nothing is detected:
        # remove the installed agent signals so only the recorded state remains.
        shutil.rmtree(self.home / ".omp")
        shutil.rmtree(self.home / ".dsh")
        third = self.run_bash(["--scope", "global", "--yes"], self.bash_env(self.empty_bin))
        self.assertEqual(third.returncode, 0, third.stderr)
        self.assertEqual(self.read_state()["adapters"], ["deepseek-harness", "omp"])
        # The recorded adapters are redeployed from the saved installation state.
        self.assertTrue((self.home / ".dsh/skills/prompt-optimizer/SKILL.md").exists())
        self.assertTrue((self.home / ".dsh/plugins/prompt-optimizer/index.mjs").exists())
        self.assertTrue((self.home / ".omp/agent/extensions/prompt-optimizer/index.ts").exists())
        # Removal is not tied to current detection: with no command detectable
        # anymore, uninstall still removes the complete recorded installation.
        uninstall = subprocess.run([self.BASH, str(ROOT / "uninstall.sh"),
                                    "--scope", "global", "--yes"],
                                   capture_output=True, text=True,
                                   env=self.bash_env(self.empty_bin), check=False)
        self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
        for path in (".dsh/skills/prompt-optimizer/SKILL.md",
                     ".dsh/plugins/prompt-optimizer/index.mjs",
                     ".omp/agent/extensions/prompt-optimizer/index.ts",
                     ".config/prompt-optimizer/install.json",
                     ".config/prompt-optimizer/config.json"):
            self.assertFalse((self.home / path).exists(), path)

    def test_bash_global_explicit_agents_does_not_auto_add(self):
        bin_dir = self.home.parent / "bash-bin"
        bin_dir.mkdir()
        write_executable(bin_dir, "omp")
        write_executable(bin_dir, "dsh")
        result = self.run_bash(["--scope", "global", "--yes", "--agents", "deepseek-harness"],
                               self.bash_env(bin_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_state()
        self.assertEqual(state["adapters"], ["deepseek-harness"])
        self.assertFalse((self.home / ".omp").exists())

    def test_bash_list_agents_global_ignores_cwd_directories(self):
        (self.home / ".config" / "opencode").mkdir(parents=True)
        (self.project / ".cursor").mkdir()
        (self.project / ".codex").mkdir()
        result = self.run_bash(["--list-agents", "--scope", "global"],
                               self.bash_env(self.empty_bin), cwd=self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[x] OpenCode", result.stdout)
        self.assertIn("[ ] OpenAI Codex", result.stdout)
        self.assertIn("[ ] Cursor", result.stdout)
        self.assertEqual([entry.name for entry in self.home.iterdir()], [".config"])


if __name__ == "__main__":
    unittest.main()
