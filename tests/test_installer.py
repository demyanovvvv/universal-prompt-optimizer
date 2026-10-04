import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
SPEC = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(installer)

CONTRACT_SPEC = importlib.util.spec_from_file_location("config_contract", ROOT / "config_contract.py")
config_contract = importlib.util.module_from_spec(CONTRACT_SPEC)
assert CONTRACT_SPEC.loader
CONTRACT_SPEC.loader.exec_module(config_contract)


class InstallerTests(unittest.TestCase):
    def test_russian_entry_point_uses_same_dry_run_without_writes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            outputs = []
            for script in ("install.py", "install.ru.py"):
                run = subprocess.run(
                    [sys.executable, "-B", str(ROOT / script), "--project", str(root),
                     "--agents", "opencode", "--dry-run"],
                    capture_output=True, text=True, check=True,
                )
                outputs.append(run.stdout)
            self.assertIn("scope: project", outputs[0])
            self.assertIn("область установки: проект", outputs[1])
            self.assertFalse(any(root.iterdir()))

    def test_legacy_opencode_install_registers_server_plugin(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw) / ".opencode"
            base.mkdir(parents=True)
            (base / "opencode.json").write_text(json.dumps({"plugin": [
                ["./plugins/user.js", {"enabled": True}],
            ]}), encoding="utf-8")
            installer.install_opencode(base, "auto", "all", "skip", "adaptive", backup=False)
            value = json.loads((base / "opencode.json").read_text(encoding="utf-8"))
            self.assertEqual(value["plugin"], [
                ["./plugins/user.js", {"enabled": True}],
                "./plugins/prompt-optimizer/index.ts",
            ])

    def test_opencode_install_registers_server_plugin_without_replacing_existing_plugins(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / ".opencode" / "opencode.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"plugin": ["./plugins/user.js"]}), encoding="utf-8")

            plan = installer._plan_install(installer._InstallRequest(
                root=root,
                scope="project",
                adapters=frozenset({"opencode"}),
                automatic=True,
            ), installer.load_catalog(installer.PACKAGE_ROOT))
            installer._execute_plan(plan, source_root=installer.PACKAGE_ROOT, backup=False)

            value = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(value["plugin"], ["./plugins/user.js", "./plugins/prompt-optimizer/index.ts"])

    def test_config_contract_preserves_unknown_fields_and_normalizes_legacy_gate(self):
        value = config_contract.normalize({
            "schemaVersion": 1,
            "qualityGate": False,
            "custom": {"keep": True},
        }, include_schema=True)
        self.assertEqual(value["qualityGate"], "pass")
        self.assertEqual(value["custom"], {"keep": True})
        self.assertEqual(value["behavior"], "auto")

    def test_config_contract_rejects_malformed_managed_fields(self):
        with self.assertRaises(ValueError):
            config_contract.normalize({"behavior": "unexpected"})

    def test_install_transaction_can_be_used_without_global_state(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "value.txt"
            path.write_text("before", encoding="utf-8")
            transaction = installer.InstallTransaction()
            with transaction:
                transaction.record(path)
                path.write_text("after", encoding="utf-8")
                transaction.rollback()
            self.assertEqual(path.read_text(encoding="utf-8"), "before")

    def test_nonautomatic_project_install_uses_composable_plan_for_skills_and_commands(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            original_skills = installer.copy_skills
            original_commands = installer.copy_commands
            installer.copy_skills = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy copy_skills path used"))
            installer.copy_commands = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy copy_commands path used"))
            try:
                installer.install_project(root, {"opencode", "claude"}, False, "auto", "all", "skip", "adaptive", False, False, sys.executable)
            finally:
                installer.copy_skills = original_skills
                installer.copy_commands = original_commands
            self.assertTrue((root / ".agents/skills/prompt-optimizer/SKILL.md").is_file())
            self.assertTrue((root / ".claude/skills/prompt-optimizer/SKILL.md").is_file())
            self.assertTrue((root / ".opencode/commands/prompt.md").is_file())
            self.assertTrue((root / ".opencode/commands/prompt-only.md").is_file())
            self.assertTrue((root / ".opencode/commands/prompt-optimizer.md").is_file())
            self.assertFalse((root / ".opencode/commands/prompt-luna.md").exists())
            self.assertFalse((root / ".opencode/plugins/prompt-optimizer").exists())
            self.assertFalse((root / ".opencode/opencode.json").exists())

    def test_nonautomatic_composable_install_keeps_first_backup_of_managed_command(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            command = root / ".opencode/commands/prompt.md"
            command.parent.mkdir(parents=True)
            command.write_text("user version", encoding="utf-8")
            installer.install_project(root, {"opencode"}, False, "auto", "all", "skip", "adaptive", True, False, sys.executable)
            backup = command.with_name(command.name + ".prompt-optimizer.bak")
            self.assertEqual(backup.read_text(encoding="utf-8"), "user version")
            first_backup = backup.read_bytes()
            installer.install_project(root, {"opencode"}, False, "auto", "all", "skip", "adaptive", True, False, sys.executable)
            self.assertEqual(backup.read_bytes(), first_backup)

    def test_automatic_opencode_pi_install_uses_composable_plan(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legacy = {
                "install_opencode": installer.install_opencode,
                "install_pi": installer.install_pi,
                "install_opencode_tui": installer.install_opencode_tui,
                "write_shared_config": installer.write_shared_config,
            }
            for name in legacy:
                setattr(installer, name, lambda *args, _name=name, **kwargs: (_ for _ in ()).throw(AssertionError(f"legacy {_name} path used")))
            try:
                installer.install_project(root, {"opencode", "pi"}, True, "auto", "all", "skip", "adaptive", False, False, sys.executable)
            finally:
                for name, value in legacy.items():
                    setattr(installer, name, value)
            self.assertTrue((root / ".prompt-optimizer.json").is_file())
            self.assertTrue((root / ".opencode/plugins/prompt-optimizer/index.ts").is_file())
            self.assertTrue((root / ".opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx").is_file())
            self.assertTrue((root / ".opencode/tui.json").is_file())
            self.assertTrue((root / ".pi/extensions/prompt-optimizer.ts").is_file())

    def test_automatic_global_opencode_pi_install_uses_global_plan_destinations(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installer.install_global(root, {"opencode", "pi"}, True, "preview", "first", "generic", "light", False, False, sys.executable)
            self.assertTrue((root / ".config/prompt-optimizer/config.json").is_file())
            self.assertTrue((root / ".config/opencode/plugins/prompt-optimizer/index.ts").is_file())
            self.assertTrue((root / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx").is_file())
            self.assertTrue((root / ".config/opencode/tui.json").is_file())
            self.assertTrue((root / ".pi/agent/extensions/prompt-optimizer.ts").is_file())

    def test_automatic_global_markdown_adapters_use_composable_plan(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legacy = {
                name: getattr(installer, name)
                for name in ("merge_block", "copy_file")
            }
            for name in legacy:
                setattr(installer, name, lambda *args, _name=name, **kwargs: (_ for _ in ()).throw(AssertionError(f"legacy {_name} path used")))
            try:
                installer.install_global(
                    root, {"claude", "codex", "copilot", "windsurf"}, True,
                    "auto", "all", "skip", "adaptive", False, False, sys.executable,
                )
            finally:
                for name, value in legacy.items():
                    setattr(installer, name, value)
            self.assertTrue((root / ".claude/CLAUDE.md").is_file())
            self.assertTrue((root / ".codex/AGENTS.md").is_file())
            self.assertTrue((root / ".copilot/copilot-instructions.md").is_file())
            self.assertTrue((root / ".codeium/windsurf/memories/global_rules.md").is_file())
            self.assertIn(f"## Prompt Optimizer v{PACKAGE_VERSION} preflight", (root / ".codex/AGENTS.md").read_text(encoding="utf-8"))

    def test_automatic_global_gemini_install_uses_composable_plan_layout(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            legacy = installer.install_gemini
            installer.install_gemini = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy Gemini path used"))
            try:
                installer.install_global(root, {"gemini"}, True, "auto", "all", "skip", "adaptive", False, False, sys.executable)
            finally:
                installer.install_gemini = legacy
            self.assertTrue((root / ".gemini/hooks/prompt-preflight.py").is_file())
            self.assertTrue((root / ".gemini/GEMINI.md").is_file())
            self.assertFalse((root / "GEMINI.md").exists())
            self.assertIn(".gemini/.prompt-optimizer-model-state.json", (root / ".gitignore").read_text(encoding="utf-8"))

    def test_automatic_cursor_install_uses_composable_plan(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".gitignore").write_text("user-ignore\n", encoding="utf-8")
            legacy_hooks = installer.install_cursor
            installer.install_cursor = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy Cursor path used"))
            try:
                installer.install_project(root, {"cursor"}, True, "auto", "all", "skip", "adaptive", False, False, sys.executable)
            finally:
                installer.install_cursor = legacy_hooks
            self.assertTrue((root / ".cursor/hooks/prompt-optimizer-state.py").is_file())
            self.assertTrue((root / ".cursor/rules/prompt-optimizer.mdc").is_file())
            hooks = json.loads((root / ".cursor/hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(hooks["hooks"]["beforeSubmitPrompt"][0]["owner"], "universal-prompt-optimizer")
            ignore_text = (root / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("user-ignore", ignore_text)
            self.assertIn(".cursor/.prompt-optimizer-runtime.json", ignore_text)

    def test_installer_modules_are_importable_without_running_cli(self):
        from installer.catalog import load_catalog
        from installer.content import merge_json
        from installer.filesystem import atomic_write_text
        from installer.transaction import InstallTransaction

        self.assertIn("opencode", load_catalog(ROOT).ids)
        self.assertIn('"behavior": "auto"', merge_json("{}", {"behavior": "auto"}))
        self.assertTrue(callable(atomic_write_text))
        self.assertIsNotNone(InstallTransaction)

    def test_pi_install_deploys_generated_routing_dependency(self):
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw)
            installer.install_pi(destination, backup=False)
            self.assertTrue((destination / "extensions/prompt-optimizer.ts").is_file())
            self.assertTrue((destination / "extensions/model-registry.ts").is_file())

    def test_legacy_quality_gate_preserves_explicit_gate_semantics(self):
        self.assertFalse(installer.legacy_quality_gate_enabled("pass"))
        self.assertTrue(installer.legacy_quality_gate_enabled("light"))
        self.assertTrue(installer.legacy_quality_gate_enabled("full"))
        self.assertTrue(installer.legacy_quality_gate_enabled("adaptive"))

    def test_shared_config_keeps_explicit_quality_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "config.json"
            installer.write_shared_config(path, "auto", "all", "skip", "full")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["qualityGate"], "full")

    def test_runtime_ignores_merge_preserves_existing_entries(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / ".gitignore"
            path.write_text("user-rule\n", encoding="utf-8")
            installer.merge_runtime_ignores(path, [".cursor/state.json"])
            installer.merge_runtime_ignores(path, [".gemini/state.json"])
            content = path.read_text(encoding="utf-8")
            self.assertIn(".cursor/state.json", content)
            self.assertIn(".gemini/state.json", content)
            self.assertIn("user-rule\n", content)

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

    def test_pi_preview_does_not_consume_turn_without_interactive_ui(self):
        source = (ROOT / "adapters" / "pi" / "extensions" / "prompt-optimizer.ts").read_text(encoding="utf-8")
        ui_check = source.index("if (!ctx.hasUI)")
        preview_state = source.index("previewedTurns.set(sid, turn)")
        self.assertLess(ui_check, preview_state)

    def test_remove_json_fields_preserves_custom_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / ".prompt-optimizer.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "behavior": "auto",
                "scope": "all",
                "qualityGate": True,
                "unsupportedModel": "generic",
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

    def test_gemini_hook_resolves_shared_latest_model_profiles(self):
        gemini_path = ROOT / "adapters/gemini-cli/hooks/prompt-preflight.py"
        source = gemini_path.read_text(encoding="utf-8").split("inp = json.load(sys.stdin)", 1)[0]
        namespace = {"__name__": "gemini_hook_model_test"}
        exec(compile(source, str(gemini_path), "exec"), namespace)
        resolve = namespace["exact_profile_for"]
        self.assertEqual(resolve("gpt-6.1-sol"), "gpt-6.1-sol")
        self.assertEqual(resolve("vendor/GPT_6.1_SOL-latest"), "gpt-6.1-sol")
        self.assertEqual(resolve("claude-sonnet-5-5"), "claude-sonnet-5.5")
        self.assertEqual(resolve("vendor/CLAUDE_SONNET_5.5-latest"), "claude-sonnet-5.5")
        self.assertEqual(resolve("claude-opus-5.5"), "claude-opus-5.5")
        self.assertIsNone(resolve("gpt-6.1-sol-extra"))

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

    def test_reinstall_updates_existing_owned_files(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            installer.install_global(
                home,
                {"gemini"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                False,
                False,
                sys.executable,
            )
            hook = home / ".gemini/hooks/prompt-preflight.py"
            hook.write_text("stale installed version", encoding="utf-8")
            installer.install_global(
                home,
                {"gemini"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                False,
                False,
                sys.executable,
            )
            self.assertEqual(hook.read_bytes(), (ROOT / "adapters/gemini-cli/hooks/prompt-preflight.py").read_bytes())

    def test_uninstall_removes_modified_owned_files_and_installer_backups(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            installer.install_global(
                home,
                {"gemini", "cursor"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                True,
                False,
                sys.executable,
            )
            hook = home / ".gemini/hooks/prompt-preflight.py"
            hook.write_text("modified by user", encoding="utf-8")
            installer.install_global(
                home,
                {"gemini", "cursor"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                True,
                False,
                sys.executable,
            )
            backup = hook.with_name(hook.name + ".prompt-optimizer.bak")
            self.assertTrue(backup.exists())
            installer.uninstall(home, "global")
            self.assertFalse(hook.exists())
            self.assertFalse(backup.exists())
            self.assertFalse((home / ".cursor/hooks/prompt-optimizer-state.py").exists())

    def test_global_markdown_adapters_diagnose_and_uninstall_round_trip(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            installer.install_global(
                home,
                {"claude", "codex", "copilot", "windsurf"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                False,
                False,
                sys.executable,
            )
            for relative in (
                ".claude/CLAUDE.md",
                ".codex/AGENTS.md",
                ".copilot/copilot-instructions.md",
                ".codeium/windsurf/memories/global_rules.md",
            ):
                self.assertTrue((home / relative).is_file(), relative)
            self.assertEqual(installer.doctor(home, "global"), 0)
            installer.uninstall(home, "global")
            for relative in (
                ".agents/skills/prompt-optimizer/SKILL.md",
                ".claude/CLAUDE.md",
                ".codex/AGENTS.md",
                ".copilot/copilot-instructions.md",
                ".codeium/windsurf/memories/global_rules.md",
            ):
                self.assertFalse((home / relative).exists(), relative)

    def test_global_cursor_auto_is_not_installed(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            output = installer.install_global(
                home,
                {"cursor"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                False,
                False,
                sys.executable,
            )
            self.assertFalse((home / ".cursor").exists())
            self.assertTrue(any("Cursor" in line for line in output))

    def test_global_cursor_with_other_adapters_skips_cursor_only(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            installer.install_global(
                home,
                {"cursor", "gemini"},
                True,
                "auto",
                "all",
                "skip",
                "adaptive",
                False,
                False,
                sys.executable,
            )
            self.assertFalse((home / ".cursor").exists())
            self.assertTrue((home / ".gemini/GEMINI.md").is_file())

    def test_doctor_reports_invalid_managed_block(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            broken = home / "CLAUDE.md"
            broken.write_text("<!-- prompt-optimizer:auto:start -->\nmissing end\n", encoding="utf-8")
            self.assertEqual(installer.doctor(home, "project"), 1)

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

    def test_opencode_tui_uninstall_preserves_byte_identical_user_plugin(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            config = home / ".config/opencode/tui.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({"theme": "user-theme", "plugin": ["./plugins/prompt-optimizer-tui/prompt-optimizer.tsx"]}), encoding="utf-8")
            destination = home / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            destination.parent.mkdir(parents=True)
            destination.write_bytes((ROOT / "adapters/opencode/tui/prompt-optimizer.tsx").read_bytes())
            installer.uninstall(home, "global")
            self.assertTrue(destination.exists())
            value = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(value["theme"], "user-theme")
            self.assertNotIn("plugin", value)

    def test_opencode_tui_uninstall_removes_installer_owned_plugin(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            installer.install_opencode_tui(home / ".config/opencode", backup=False)
            destination = home / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            owner = destination.parent / ".prompt-optimizer-owner.json"
            self.assertTrue(destination.exists())
            self.assertTrue(owner.exists())
            installer.uninstall(home, "global")
            self.assertFalse(destination.exists())
            self.assertFalse(owner.exists())

    def test_opencode_tui_install_refuses_modified_user_plugin(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            destination = home / ".config/opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            destination.parent.mkdir(parents=True)
            destination.write_text("user plugin\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                installer.install_opencode_tui(home / ".config/opencode", backup=False)
            self.assertEqual(destination.read_text(encoding="utf-8"), "user plugin\n")

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

    def test_legacy_quality_gate_mapping_preserves_explicit_enabled_mode(self):
        self.assertTrue(installer.legacy_quality_gate_enabled(True))

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

    def test_adapter_combination_matrix_round_trip_preserves_user_files(self):
        adapters = sorted(installer.AGENTS)
        combos = [(name,) for name in adapters]
        combos += [
            tuple(adapters),
            ("opencode", "claude"),
            ("cursor", "gemini"),
            ("claude", "codex", "copilot", "windsurf"),
            ("opencode", "pi", "gemini"),
        ]
        for scope in ("project", "global"):
            for combo in combos:
                for automatic in (True, False):
                    if not automatic and not set(combo) <= {"opencode", "claude"}:
                        continue
                    label = f"{scope}/{'-'.join(combo)}/auto={automatic}"
                    with self.subTest(case=label):
                        with tempfile.TemporaryDirectory() as raw:
                            root = Path(raw)
                            user_agents = root / "AGENTS.md"
                            user_agents.write_text("# user content\n", encoding="utf-8")
                            user_skill = root / ".agents/skills/custom/SKILL.md"
                            user_skill.parent.mkdir(parents=True)
                            user_skill.write_text("user\n", encoding="utf-8")
                            selected = set(combo)
                            if scope == "project":
                                installer.install_project(root, selected, automatic, "auto", "all", "skip", "adaptive", False, False, sys.executable)
                            else:
                                installer.install_global(root, selected, automatic, "auto", "all", "skip", "adaptive", False, False, sys.executable)
                            self.assertEqual(installer.doctor(root, scope), 0, label)
                            installer.uninstall(root, scope)
                            self.assertEqual(user_agents.read_text(encoding="utf-8"), "# user content\n", label)
                            self.assertEqual(user_skill.read_text(encoding="utf-8"), "user\n", label)
                            self.assertFalse((root / ".agents/skills/prompt-optimizer/SKILL.md").exists(), label)

    def test_adapter_matrix_dry_run_reinstall_backup_and_json_preservation(self):
        adapters = sorted(installer.AGENTS)
        cases = [
            ("opencode", "project"),
            ("cursor", "project"),
            ("gemini", "project"),
            ("opencode", "global"),
            ("gemini", "global"),
            (tuple(adapters), "project"),
        ]
        for combo, scope in cases:
            selected = set(combo if isinstance(combo, tuple) else (combo,))
            label = f"{scope}/{'all' if isinstance(combo, tuple) else combo}"
            with self.subTest(case=label):
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    config = root / (".prompt-optimizer.json" if scope == "project" else ".config/prompt-optimizer/config.json")
                    config.parent.mkdir(parents=True, exist_ok=True)
                    config.write_text(json.dumps({"customField": "keep-me"}), encoding="utf-8")

                    def do_install(dry_run):
                        if scope == "project":
                            installer.install_project(root, selected, True, "auto", "all", "skip", "adaptive", True, dry_run, sys.executable)
                        else:
                            installer.install_global(root, selected, True, "auto", "all", "skip", "adaptive", True, dry_run, sys.executable)

                    do_install(True)
                    self.assertEqual(json.loads(config.read_text(encoding="utf-8")), {"customField": "keep-me"}, label)
                    do_install(False)
                    after_first = json.loads(config.read_text(encoding="utf-8"))
                    self.assertEqual(after_first.get("customField"), "keep-me", label)
                    self.assertEqual(after_first.get("behavior"), "auto", label)
                    self.assertTrue((root / ".agents/skills/prompt-optimizer/SKILL.md").is_file(), label)

                    do_install(False)
                    after_second = json.loads(config.read_text(encoding="utf-8"))
                    self.assertEqual(after_first, after_second, label)

                    installer.uninstall(root, scope)
                    self.assertEqual(json.loads(config.read_text(encoding="utf-8")), {"customField": "keep-me"}, label)

    def test_failed_install_rolls_back_partial_changes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".gemini").mkdir(parents=True)
            (root / ".prompt-optimizer.json").write_text("{}\n", encoding="utf-8")
            settings = root / ".gemini/settings.json"
            settings.write_text("{broken\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                installer.install_project(root, {"opencode", "gemini"}, True, "auto", "all", "skip", "adaptive", False, False, sys.executable)
            self.assertFalse((root / ".agents/skills/prompt-optimizer/SKILL.md").exists())
            self.assertFalse((root / ".prompt-optimizer-install.lock").exists())
            self.assertEqual(settings.read_text(encoding="utf-8"), "{broken\n")

    def test_uninstall_plan_removes_managed_content_and_is_transactional_on_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            installer.install_project(root, {"opencode", "gemini"}, True, "auto", "all", "skip", "adaptive", False, False, sys.executable)
            self.assertEqual(installer.doctor(root, "project"), 0)
            skill = root / ".agents/skills/prompt-optimizer/SKILL.md"
            self.assertTrue(skill.is_file())

            settings = root / ".gemini/settings.json"
            settings.write_text("{broken\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                installer.uninstall(root, "project")
            self.assertTrue(skill.is_file())
            self.assertEqual(settings.read_text(encoding="utf-8"), "{broken\n")

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
