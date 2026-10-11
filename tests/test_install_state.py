import json
import tempfile
import unittest
from pathlib import Path

from installer.catalog import load_catalog
from installer.domain import InstallPlan, InstallRequest, Operation
from installer.executor import execute_plan
from installer.lifecycle import build_uninstall_plan
from installer.planning import plan_install

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


class InstallStateTests(unittest.TestCase):
    def test_version_inventory_upgrade_and_complete_removal_in_both_scopes(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                catalog = load_catalog(ROOT)
                request = InstallRequest(root, scope, catalog.ids, automatic=True)
                execute_plan(plan_install(request, catalog), source_root=ROOT)
                state_path = root / (".prompt-optimizer-install.json" if scope == "project"
                                     else ".config/prompt-optimizer/install.json")
                state = json.loads(state_path.read_text(encoding="utf-8"))
                self.assertEqual(state["version"], VERSION)
                self.assertEqual(set(state["adapters"]), set(catalog.ids))
                self.assertIn(".agents/skills/prompt-optimizer/SKILL.md", state["files"])
                self.assertNotIn("AGENTS.md", state["files"])
                obsolete = root / ".agents/skills/prompt-optimizer/obsolete.txt"
                obsolete.write_text("old version", encoding="utf-8")
                state["version"] = "5.0.0"
                state["files"].append(obsolete.relative_to(root).as_posix())
                state_path.write_text(json.dumps(state), encoding="utf-8")
                neighbor = root / ".agents/skills/user/SKILL.md"
                neighbor.parent.mkdir(parents=True)
                neighbor.write_text("user-owned", encoding="utf-8")
                plan = plan_install(request, catalog)
                execute_plan(plan, source_root=ROOT, dry_run=True)
                self.assertTrue(obsolete.exists())
                self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["version"], "5.0.0")
                execute_plan(plan, source_root=ROOT)
                self.assertFalse(obsolete.exists())
                self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))["version"], VERSION)
                runtime = root / ".gemini/.prompt-optimizer-session-state.json.lock"
                runtime.write_text("stale lock", encoding="utf-8")
                execute_plan(build_uninstall_plan(root, ROOT, scope), source_root=ROOT, backup=False)
                self.assertFalse(state_path.exists())
                self.assertFalse(runtime.exists())
                self.assertEqual(neighbor.read_text(encoding="utf-8"), "user-owned")
                self.assertEqual([p for p in root.rglob("*") if p.is_file()], [neighbor])

    def test_failed_update_restores_version_and_obsolete_file(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog = load_catalog(ROOT)
            request = InstallRequest(root, "project", frozenset({"opencode"}), automatic=True)
            execute_plan(plan_install(request, catalog), source_root=ROOT)
            state_path = root / ".prompt-optimizer-install.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            obsolete = root / ".opencode/plugins/prompt-optimizer/obsolete.ts"
            obsolete.write_text("old", encoding="utf-8")
            state["files"].append(obsolete.relative_to(root).as_posix())
            state["version"] = "5.0.0"
            before = json.dumps(state).encode()
            state_path.write_bytes(before)
            plan = plan_install(request, catalog)
            failing = InstallPlan((*plan.operations, Operation("copy_file", root / "failure", source=Path("missing"))))
            with self.assertRaises(ValueError):
                execute_plan(failing, source_root=ROOT)
            self.assertEqual(state_path.read_bytes(), before)
            self.assertEqual(obsolete.read_text(encoding="utf-8"), "old")

    def test_inventory_cannot_remove_user_files_or_escape_scope(self):
        for path in ("../outside.txt", "AGENTS.md", ".agents/skills/user/SKILL.md", "C:/outside.txt"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                state_path = root / ".prompt-optimizer-install.json"
                state_path.write_text(json.dumps({"schema": 1, "scope": "project", "version": "5.0.0",
                                                 "adapters": ["opencode"], "automatic": True, "files": [path]}), encoding="utf-8")
                with self.assertRaises(ValueError):
                    build_uninstall_plan(root, ROOT, "project")

    def test_preexisting_configs_and_nested_user_hooks_survive_removal(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / '.gemini/settings.json'
            config.parent.mkdir()
            user_hook = {"hooks": [{"type": "command", "command": "user-command"}]}
            config.write_text(json.dumps({"custom": True, "hooks": {"BeforeAgent": [user_hook]}}), encoding='utf-8')
            tui = root / '.opencode/tui.json'
            tui.parent.mkdir()
            tui.write_text('{"$schema":"https://opencode.ai/tui.json"}', encoding='utf-8')
            catalog = load_catalog(ROOT)
            request = InstallRequest(root, 'project', catalog.ids, automatic=True)
            execute_plan(plan_install(request, catalog), source_root=ROOT)
            execute_plan(build_uninstall_plan(root, ROOT, 'project'), source_root=ROOT, backup=False)
            self.assertEqual(json.loads(config.read_text(encoding='utf-8')), {"custom": True, "version": 1,
                             "hooks": {"BeforeAgent": [user_hook]}})
            self.assertEqual(json.loads(tui.read_text(encoding='utf-8')), {"$schema": "https://opencode.ai/tui.json"})

    def test_partial_install_retains_previous_adapter_inventory(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            catalog = load_catalog(ROOT)
            for adapter in ('opencode', 'gemini'):
                execute_plan(plan_install(InstallRequest(root, 'project', frozenset({adapter}), automatic=True), catalog), source_root=ROOT)
            state = json.loads((root / '.prompt-optimizer-install.json').read_text(encoding='utf-8'))
            self.assertEqual(state['adapters'], ['gemini', 'opencode'])
            self.assertIn('.opencode/plugins/prompt-optimizer/index.ts', state['files'])
            execute_plan(build_uninstall_plan(root, ROOT, 'project'), source_root=ROOT, backup=False)
            self.assertFalse(any(p.is_file() for p in root.rglob('*')))


if __name__ == "__main__":
    unittest.main()
