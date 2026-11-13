"""User-visible installation lifecycle for the DeepSeek Harness adapter.

Covers the installer-owned surfaces only: the canonical native skill copy at
``<root>/.dsh/skills``, the automatic Cordis plugin/overlay deployment, the
manual-versus-automatic difference, dry-run read-only behavior, rollback,
symlink rejection, idempotence and preservation of unrelated ``.dsh`` content.
"""

import tempfile
import unittest
from pathlib import Path

from installer.catalog import load_catalog
from installer.domain import InstallPlan, InstallRequest, Operation
from installer.executor import execute_plan
from installer.lifecycle import build_uninstall_plan, managed_file_map, uninstall_targets
from installer.planning import plan_install
from installer.state import owned_path, read_state

ROOT = Path(__file__).resolve().parents[1]

PLUGIN_RUNTIME = Path(".dsh/plugins/prompt-optimizer/index.mjs")
OVERLAY = Path(".dsh/prompt-optimizer.patch.yml")
SKILL_ENTRY = Path(".dsh/skills/prompt-optimizer/SKILL.md")


def request(root: Path, scope: str, **overrides) -> InstallRequest:
    values = dict(root=root, scope=scope, adapters=frozenset({"deepseek-harness"}), automatic=True)
    values.update(overrides)
    return InstallRequest(**values)


class DeepSeekHarnessInstallTests(unittest.TestCase):
    def test_manifest_exposes_the_adapter_and_aliases_resolve(self):
        # Arrange
        import importlib.util

        spec = importlib.util.spec_from_file_location("upo_install_dsh", ROOT / "install.py")
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)

        # Act
        catalog = load_catalog(ROOT)
        aliases = {name: legacy.parse_agents(name) for name in ("dsh", "deepseek", "deepseek-harness")}

        # Assert
        self.assertIn("deepseek-harness", catalog.ids)
        for name, resolved in aliases.items():
            self.assertEqual(resolved, {"deepseek-harness"}, name)

    def test_automatic_install_deploys_skill_plugin_and_owned_overlay(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)

                # Act
                plan = plan_install(request(root, scope), load_catalog(ROOT))
                execute_plan(plan, source_root=ROOT)

                # Assert
                self.assertTrue((root / SKILL_ENTRY).is_file())
                self.assertTrue((root / PLUGIN_RUNTIME).is_file())
                overlay = (root / OVERLAY).read_text(encoding="utf-8")
                self.assertIn("- insert:", overlay)
                self.assertIn("id: universal-prompt-optimizer", overlay)
                self.assertIn("name: './plugins/prompt-optimizer/index.mjs'", overlay)
                # The canonical skill is copied once per destination, not twice.
                self.assertFalse((root / ".dsh/plugins/prompt-optimizer/skill").exists())
                # Both scopes share the same .dsh layout.
                mapping = managed_file_map(root, ROOT, scope)
                self.assertEqual(mapping["dsh-skills"][1], root / ".dsh/skills")
                self.assertEqual(mapping["dsh-plugin"][1], root / ".dsh/plugins/prompt-optimizer")
                self.assertEqual(mapping["dsh-overlay"][1], root / OVERLAY)

    def test_manual_install_only_provides_native_discovery_skill(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)

                # Act
                plan = plan_install(request(root, scope, automatic=False), load_catalog(ROOT))
                execute_plan(plan, source_root=ROOT)

                # Assert
                self.assertTrue((root / SKILL_ENTRY).is_file())
                self.assertTrue((root / ".agents/skills/prompt-optimizer/SKILL.md").is_file())
                self.assertFalse((root / ".dsh/plugins").exists())
                self.assertFalse((root / OVERLAY).exists())

    def test_automatic_install_reports_exact_activation_message(self):
        # Arrange
        import importlib.util

        spec = importlib.util.spec_from_file_location("upo_install_dsh_msg", ROOT / "install.py")
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        with tempfile.TemporaryDirectory() as raw:
            # A path with a space proves the overlay argument is quoted.
            root = Path(raw) / "project dir"
            root.mkdir()

            # Act
            plan = plan_install(request(root, "project"), load_catalog(ROOT))
            messages = legacy._install_plan_messages(plan, dry_run=False, root=root, scope="project")
            dry_messages = legacy._install_plan_messages(plan, dry_run=True, root=root, scope="project")

            # Assert
            hint = [line for line in messages if "dsh --profile web --patch" in line]
            self.assertEqual(len(hint), 1)
            self.assertIn("dsh --profile web --patch", hint[0])
            from installer.planning import shell_command
            expected = shell_command(["dsh", "--profile", "web", "--patch", str(root / OVERLAY)])
            self.assertIn(expected, hint[0])
            self.assertIn(str(root / OVERLAY), hint[0])
            self.assertIn("before the app arguments", hint[0])
            self.assertIn("never edits your Harness profile", hint[0])

            # A dry run must not claim the plugin is already installed.
            dry_hint = [line for line in dry_messages if "dsh --profile web --patch" in line]
            self.assertEqual(len(dry_hint), 1)
            self.assertIn("To activate after installation", dry_hint[0])
            self.assertNotIn("plugin and skill installed", dry_hint[0])

    def test_dry_run_install_is_read_only_and_reinstall_is_idempotent(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            root = Path(raw)
            plan = plan_install(request(root, "project"), load_catalog(ROOT))

            # Act
            execute_plan(plan, source_root=ROOT, dry_run=True)

            # Assert
            self.assertFalse((root / ".dsh").exists())

            # Act
            execute_plan(plan, source_root=ROOT)
            overlay_before = (root / OVERLAY).read_text(encoding="utf-8")
            deployed = {path.relative_to(root).as_posix(): path.read_bytes()
                        for path in (root / ".dsh").rglob("*") if path.is_file()}
            execute_plan(plan, source_root=ROOT)

            # Assert
            self.assertEqual((root / OVERLAY).read_text(encoding="utf-8"), overlay_before)
            for relative, content in deployed.items():
                self.assertEqual((root / relative).read_bytes(), content)
            backups = {path.relative_to(root).as_posix(): path.read_bytes()
                       for path in (root / ".dsh").rglob("*.prompt-optimizer.bak")}
            self.assertEqual(len(backups), len(deployed))
            execute_plan(plan, source_root=ROOT)
            self.assertEqual({path.relative_to(root).as_posix(): path.read_bytes()
                              for path in (root / ".dsh").rglob("*.prompt-optimizer.bak")}, backups)
            state = read_state(root, "project")
            self.assertIn(SKILL_ENTRY.as_posix(), state["files"])
            self.assertIn(PLUGIN_RUNTIME.as_posix(), state["files"])
            self.assertIn(OVERLAY.as_posix(), state["files"])

    def test_install_preserves_unrelated_dsh_files_and_user_content(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            root = Path(raw)
            unrelated = root / ".dsh/skills/user-skill/SKILL.md"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("user skill", encoding="utf-8")
            user_plugin = root / ".dsh/plugins/user-plugin/index.mjs"
            user_plugin.parent.mkdir(parents=True)
            user_plugin.write_text("user plugin", encoding="utf-8")
            profile = root / ".dsh/cordis.patch.yml"
            profile.write_text("# user profile overlay\n", encoding="utf-8")

            # Act
            plan = plan_install(request(root, "project"), load_catalog(ROOT))
            execute_plan(plan, source_root=ROOT)

            # Assert
            self.assertEqual(unrelated.read_text(encoding="utf-8"), "user skill")
            self.assertEqual(user_plugin.read_text(encoding="utf-8"), "user plugin")
            self.assertEqual(profile.read_text(encoding="utf-8"), "# user profile overlay\n")

    def test_uninstall_removes_owned_entries_and_keeps_neighbors(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange: install first, then add user-owned neighbors inside the
                # shared .dsh skill root and the .dsh root itself.
                root = Path(raw)
                execute_plan(plan_install(request(root, scope), load_catalog(ROOT)), source_root=ROOT)
                unrelated = root / ".dsh/skills/user-skill/SKILL.md"
                unrelated.parent.mkdir(parents=True)
                unrelated.write_text("user skill", encoding="utf-8")
                unrelated_notes = root / ".dsh/skills/user-skill/notes.md"
                unrelated_notes.write_text("user notes", encoding="utf-8")
                user_config = root / ".dsh/cordis.patch.yml"
                user_config.write_text("# user profile overlay\n", encoding="utf-8")

                # Act
                execute_plan(build_uninstall_plan(root, ROOT, scope), source_root=ROOT, backup=False)
                execute_plan(build_uninstall_plan(root, ROOT, scope), source_root=ROOT, backup=False)

                # Assert: Prompt Optimizer artifacts go, user neighbors stay.
                self.assertFalse((root / ".dsh/plugins").exists())
                self.assertFalse((root / OVERLAY).exists())
                self.assertFalse((root / ".dsh/skills/prompt-optimizer").exists())
                self.assertEqual(unrelated.read_text(encoding="utf-8"), "user skill")
                self.assertEqual(unrelated_notes.read_text(encoding="utf-8"), "user notes")
                self.assertEqual(user_config.read_text(encoding="utf-8"), "# user profile overlay\n")
                self.assertFalse(list(root.rglob("*.prompt-optimizer.bak")))
                state_path = root / (".prompt-optimizer-install.json" if scope == "project" else ".config/prompt-optimizer/install.json")
                self.assertFalse(state_path.exists())

    def test_uninstall_removes_modified_owned_artifacts(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            root = Path(raw)
            execute_plan(plan_install(request(root, "project"), load_catalog(ROOT)), source_root=ROOT)
            (root / OVERLAY).write_text("# user edited overlay\n", encoding="utf-8")
            (root / PLUGIN_RUNTIME).write_text("// user edited runtime\n", encoding="utf-8")

            # Act
            execute_plan(build_uninstall_plan(root, ROOT, "project"), source_root=ROOT, backup=False)

            # Assert
            self.assertFalse((root / OVERLAY).exists())
            self.assertFalse((root / PLUGIN_RUNTIME).exists())

    def test_failed_install_rolls_back_created_harness_artifacts(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            root = Path(raw)
            user_config = root / ".dsh/cordis.patch.yml"
            user_config.parent.mkdir()
            user_config.write_bytes(b"# unchanged user overlay\n")
            plan = plan_install(request(root, "project"), load_catalog(ROOT))
            failing = InstallPlan((*plan.operations, Operation("merge", root / "broken.json", content=b"not json")))

            # Act / Assert
            with self.assertRaises(ValueError):
                execute_plan(failing, source_root=ROOT)
            self.assertEqual(user_config.read_bytes(), b"# unchanged user overlay\n")
            self.assertEqual([path for path in (root / ".dsh").rglob("*") if path.is_file()], [user_config])
            self.assertFalse(any(path.is_file() for path in (root / ".agents").rglob("*")))

    def test_install_rejects_symlinked_harness_destinations(self):
        for relative in (".dsh", ".dsh/skills"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)
                outside = Path(raw) / "outside"
                outside.mkdir()
                link = root / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                try:
                    link.symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlinks unavailable: {exc}")
                plan = plan_install(request(root, "project"), load_catalog(ROOT))

                # Act / Assert
                with self.assertRaises(ValueError):
                    execute_plan(plan, source_root=ROOT)
                self.assertEqual(list(outside.rglob("*")), [])

    def test_inventory_rejects_unowned_dsh_paths(self):
        for relative in (".dsh/skills/user-skill/SKILL.md", ".dsh/plugins/user-plugin/index.mjs", ".dsh/cordis.patch.yml"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)

                # Act / Assert
                with self.assertRaises(ValueError):
                    owned_path(root, "project", relative)

    def test_uninstall_targets_classify_deepseek_harness_entries(self):
        # Arrange
        root = Path("/tmp/project")

        # Act
        targets = uninstall_targets(root, ROOT, "project")

        # Assert
        self.assertEqual(targets["dsh-skills"][2], "dir")
        self.assertEqual(targets["dsh-plugin"][2], "dir")
        self.assertEqual(targets["dsh-overlay"][2], "owned_file")

    def test_cli_install_reinstall_dry_run_and_uninstall_end_to_end(self):
        import os
        import subprocess
        import sys

        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange: global installs resolve the user home from HOME/USERPROFILE.
                root = Path(raw)
                target = root
                environment = {**os.environ, "HOME": str(root), "USERPROFILE": str(root)}
                base = [sys.executable, "-B", str(ROOT / "install.py"), "--scope", scope, "--agents", "dsh", "--yes"]
                if scope == "project":
                    base += ["--project", str(root)]

                def run(*extra: str):
                    return subprocess.run([*base, *extra], capture_output=True, text=True, check=True, env=environment)

                # Act
                run("--auto", "--dry-run")

                # Assert
                self.assertFalse((target / ".dsh").exists(), "dry run must not create .dsh")
                result = run("--auto")

                # Assert
                self.assertIn(".dsh", result.stdout)
                self.assertIn("--patch", result.stdout)
                self.assertTrue((target / SKILL_ENTRY).is_file())
                self.assertTrue((target / PLUGIN_RUNTIME).is_file())
                self.assertTrue((target / OVERLAY).is_file())

                # Act
                run("--auto")

                # Assert
                self.assertTrue((target / OVERLAY).is_file())
                self.assertTrue((target / OVERLAY).with_name(OVERLAY.name + ".prompt-optimizer.bak").is_file())

                # Act
                remove = [sys.executable, "-B", str(ROOT / "uninstall.py"), "--scope", scope, "--yes"]
                if scope == "project":
                    remove += ["--project", str(root)]
                subprocess.run(remove, capture_output=True, text=True, check=True, env=environment)

                # Assert
                self.assertFalse((target / ".dsh").exists())
                self.assertFalse(list(target.rglob("*.prompt-optimizer.bak")))


if __name__ == "__main__":
    unittest.main()
