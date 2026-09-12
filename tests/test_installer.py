import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_remove_managed_block_preserves_user_text(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "AGENTS.md"
            path.write_text(
                "before\n\n"
                f"{installer.START}\nmanaged\n{installer.END}\n\n"
                "after\n",
                encoding="utf-8",
            )
            installer.remove_managed_block(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "before\n\nafter\n")

    def test_remove_only_managed_block_removes_empty_file(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "AGENTS.md"
            path.write_text(f"{installer.START}\nmanaged\n{installer.END}\n", encoding="utf-8")
            installer.remove_managed_block(path)
            self.assertFalse(path.exists())

    def test_clean_managed_hooks_keeps_user_siblings(self):
        entries = [
            {"name": "prompt-optimizer", "command": "user-command"},
            {"hooks": [
                {"name": "user", "command": "keep"},
                {"owner": installer.MANAGED_HOOK_OWNER, "command": "remove"},
            ]},
        ]
        cleaned, changed = installer.clean_managed_hooks(entries)
        self.assertTrue(changed)
        self.assertEqual(cleaned[0]["command"], "user-command")
        self.assertEqual(cleaned[1]["hooks"], [{"name": "user", "command": "keep"}])

    def test_remove_json_fields_preserves_custom_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / ".prompt-optimizer.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "behavior": "auto",
                "scope": "all",
                "qualityGate": True,
                "unsupportedModel": "skip",
                "custom": "keep",
            }), encoding="utf-8")
            installer.remove_json_fields(path, {
                "schemaVersion", "behavior", "scope", "qualityGate", "unsupportedModel"
            })
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"custom": "keep"})

    def test_schema_version_validation(self):
        installer.validate_managed_config({"schemaVersion": 1}, Path("config.json"), "config")
        with self.assertRaises(SystemExit):
            installer.validate_managed_config({"schemaVersion": 2}, Path("config.json"), "config")

    def test_runtime_state_pruning(self):
        gemini_path = ROOT / "adapters/gemini-cli/hooks/prompt-preflight.py"
        source = gemini_path.read_text(encoding="utf-8").split("inp = json.load(sys.stdin)", 1)[0]
        namespace = {"__name__": "gemini_hook_test"}
        exec(compile(source, str(gemini_path), "exec"), namespace)
        now = namespace["time"].time()
        state = {
            "old": {"model": "old", "updatedAt": now - namespace["STATE_TTL_SECONDS"] - 1},
            "fresh": {"model": "new", "updatedAt": now},
            "legacy": "gemini-3.8-flash",
        }
        pruned = namespace["prune_state"](state)
        self.assertNotIn("old", pruned)
        self.assertIn("fresh", pruned)
        self.assertIn("legacy", pruned)

    def test_global_install_uninstall_lifecycle(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            user_command = home / ".config/opencode/commands/user.md"
            user_command.parent.mkdir(parents=True)
            user_command.write_text("keep\n", encoding="utf-8")
            installer.install_global(
                home,
                set(installer.AGENTS),
                True,
                "auto",
                "all",
                "skip",
                True,
                False,
                False,
                sys.executable,
            )
            self.assertTrue((home / ".config/opencode/plugins/prompt-optimizer/index.ts").is_file())
            self.assertTrue((home / ".gemini/settings.json").is_file())
            installer.uninstall(home, "global")
            self.assertFalse((home / ".agents/skills/prompt-optimizer/SKILL.md").exists())

    def test_opencode_tui_install_preserves_existing_config(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            config = home / ".config/opencode/tui.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"theme": "user-theme", "plugin": ["./plugins/user.tsx"]}), encoding="utf-8")
            installer.install_global(
                home,
                {"opencode"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                True,
                False,
                sys.executable,
            )
            value = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(value["theme"], "user-theme")
            self.assertIn("./plugins/user.tsx", value["plugin"])
            self.assertIn("./plugins/prompt-optimizer-tui/prompt-optimizer.tsx", value["plugin"])
            self.assertTrue((home / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx").is_file())

    def test_opencode_tui_uninstall_preserves_user_plugin(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            config = home / ".config/opencode/tui.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"plugin": ["./plugins/user.tsx", "./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"]}), encoding="utf-8")
            destination = home / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            destination.parent.mkdir(parents=True)
            destination.write_text((ROOT / "adapters/opencode/tui/prompt-optimizer.tsx").read_text(encoding="utf-8"), encoding="utf-8")
            installer.uninstall(home, "global")
            self.assertTrue(destination.exists())
            value = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(value["plugin"], ["./plugins/user.tsx"])

    def test_opencode_tui_uninstall_dry_run_does_not_change_config(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            config = home / ".config/opencode/tui.json"
            config.parent.mkdir(parents=True)
            original = {"theme": "user-theme", "plugin": ["./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"]}
            config.write_text(json.dumps(original), encoding="utf-8")
            destination = home / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            destination.parent.mkdir(parents=True)
            destination.write_text((ROOT / "adapters/opencode/tui/prompt-optimizer.tsx").read_text(encoding="utf-8"), encoding="utf-8")
            results = installer.uninstall(home, "global", dry_run=True)
            self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)
            self.assertTrue(destination.exists())
            self.assertTrue(any(str(config) in result and "write" in result for result in results))

    def test_legacy_quality_gate_mapping(self):
        self.assertTrue(installer.legacy_quality_gate_enabled("adaptive"))
        self.assertTrue(installer.legacy_quality_gate_enabled("light"))
        self.assertTrue(installer.legacy_quality_gate_enabled("full"))
        self.assertFalse(installer.legacy_quality_gate_enabled("pass"))
        self.assertFalse(installer.legacy_quality_gate_enabled(False))

    def test_opencode_duplicate_guard_distinguishes_pending_turn(self):
        source = (ROOT / "adapters/opencode/plugin/session-state.ts").read_text(encoding="utf-8")
        self.assertIn("if (state.pendingPromptHash) return false", source)
        self.assertIn("lastProcessedEventId", source)

    def test_remove_file_preserves_modified_copy(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.txt"
            destination = root / "destination.txt"
            source.write_text("package\n", encoding="utf-8")
            destination.write_text("user changed this\n", encoding="utf-8")
            result = installer.remove_file_if_matches(source, destination)
            self.assertIn("preserved", result)
            self.assertEqual(destination.read_text(encoding="utf-8"), "user changed this\n")

    def test_remove_hooks_preserves_user_entries(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "hooks.json"
            path.write_text(json.dumps({"custom": "keep", "hooks": {"BeforeAgent": [
                {"name": "user", "command": "keep"},
                {"hooks": [{"owner": installer.MANAGED_HOOK_OWNER, "command": "remove"}]},
            ]}}), encoding="utf-8")
            installer.remove_json_hooks(path, {"BeforeAgent"})
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(value["custom"], "keep")
            self.assertEqual(value["hooks"]["BeforeAgent"], [{"name": "user", "command": "keep"}])

    def test_remove_hooks_keeps_ambiguous_version_container(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "hooks.json"
            path.write_text(json.dumps({"version": 1, "hooks": {"BeforeAgent": [
                {"owner": installer.MANAGED_HOOK_OWNER, "command": "remove"},
            ]}}), encoding="utf-8")
            installer.remove_json_hooks(path, {"BeforeAgent"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"version": 1})


if __name__ == "__main__":
    unittest.main()
