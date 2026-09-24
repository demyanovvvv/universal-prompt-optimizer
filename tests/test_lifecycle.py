import json
import tempfile
import unittest
from pathlib import Path

from installer import lifecycle

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT


class ManagedFileMapTests(unittest.TestCase):
    def test_project_map_covers_every_shipped_adapter_destination(self):
        mapping = lifecycle.managed_file_map(Path("/tmp/project"), PACKAGE_ROOT, "project")
        self.assertEqual(mapping["shared-skills"], (PACKAGE_ROOT / ".agents/skills", Path("/tmp/project/.agents/skills")))
        self.assertEqual(mapping["gemini-block"], (PACKAGE_ROOT / "auto/GEMINI.snippet.md", Path("/tmp/project/GEMINI.md")))
        self.assertEqual(mapping["copilot-block"], (PACKAGE_ROOT / "auto/AGENTS.snippet.md", Path("/tmp/project/.github/copilot-instructions.md")))

    def test_global_map_relocates_config_and_documents(self):
        mapping = lifecycle.managed_file_map(Path("/tmp/home"), PACKAGE_ROOT, "global")
        self.assertEqual(mapping["shared-config"][1], Path("/tmp/home/.config/prompt-optimizer/config.json"))
        self.assertEqual(mapping["gemini-block"][1], Path("/tmp/home/.gemini/GEMINI.md"))
        self.assertEqual(mapping["codex-block"][1], Path("/tmp/home/.codex/AGENTS.md"))
        self.assertEqual(mapping["windsurf-block"][1], Path("/tmp/home/.codeium/windsurf/memories/global_rules.md"))
        self.assertEqual(mapping["windsurf-block"][0], PACKAGE_ROOT / "auto/AGENTS.snippet.md")

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            lifecycle.managed_file_map(Path("/tmp/x"), PACKAGE_ROOT, "workspace")


class UninstallPlanTests(unittest.TestCase):
    def test_build_uninstall_plan_targets_managed_destinations(self):
        plan = lifecycle.build_uninstall_plan(Path("/tmp/project"), PACKAGE_ROOT, "project")
        kinds = {(operation.kind, operation.path.as_posix()) for operation in plan.operations}
        self.assertIn(("delete_tree_if_matches", "/tmp/project/.agents/skills"), kinds)
        self.assertIn(("delete_block", "/tmp/project/GEMINI.md"), kinds)
        self.assertIn(("delete_file_if_matches", "/tmp/project/.gemini/hooks/prompt-preflight.py"), kinds)
        self.assertIn(("delete_json_fields", "/tmp/project/.prompt-optimizer.json"), kinds)

    def test_build_uninstall_plan_includes_runtime_cleanup(self):
        plan = lifecycle.build_uninstall_plan(Path("/tmp/project"), PACKAGE_ROOT, "project")
        kinds = {(operation.kind, operation.path.as_posix()) for operation in plan.operations}
        self.assertIn(("delete_block", "/tmp/project/.gitignore"), kinds)
        self.assertIn(("delete_owned_file", "/tmp/project/.gemini/.prompt-optimizer-model-state.json"), kinds)
        self.assertIn(("delete_owned_file", "/tmp/project/.cursor/.prompt-optimizer-runtime.json"), kinds)

    def test_build_uninstall_plan_includes_hooks_and_tui_registration(self):
        project = lifecycle.build_uninstall_plan(Path("/tmp/project"), PACKAGE_ROOT, "project")
        project_kinds = {(operation.kind, operation.path.as_posix()) for operation in project.operations}
        self.assertIn(("delete_json_hooks", "/tmp/project/.cursor/hooks.json"), project_kinds)
        self.assertIn(("delete_json_hooks", "/tmp/project/.gemini/settings.json"), project_kinds)
        self.assertIn(("delete_json_plugin_specs", "/tmp/project/.opencode/tui.json"), project_kinds)
        owner = next(operation for operation in project.operations if operation.label == "opencode-tui-owner")
        self.assertEqual(owner.kind, "delete_owned_file")

        global_plan = lifecycle.build_uninstall_plan(Path("/tmp/home"), PACKAGE_ROOT, "global")
        global_paths = {operation.path.as_posix() for operation in global_plan.operations}
        self.assertNotIn("/tmp/home/.cursor/hooks.json", global_paths)
        self.assertIn("/tmp/home/.gemini/settings.json", global_paths)


class DiagnoseTests(unittest.TestCase):
    def test_diagnose_reports_not_installed_for_empty_root(self):
        with tempfile.TemporaryDirectory() as raw:
            report = lifecycle.diagnose(Path(raw), PACKAGE_ROOT, "project")
            self.assertEqual(report.status, "not-installed")
            self.assertEqual(report.found, 0)

    def test_diagnose_reports_invalid_managed_config(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / ".prompt-optimizer.json"
            config.write_text(json.dumps({"behavior": "unexpected"}), encoding="utf-8")
            report = lifecycle.diagnose(root, PACKAGE_ROOT, "project")
            self.assertEqual(report.status, "invalid")
            self.assertTrue(any("behavior" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
