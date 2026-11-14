"""User-visible installation lifecycle for the DeepSeek Harness adapter.

Covers the installer-owned surfaces only: the canonical native skill copy at
``<root>/.dsh/skills``, the self-contained native package, the explicit project
overlay, the manual-versus-automatic difference, dry-run read-only behavior,
rollback, symlink rejection, idempotence and preservation of unrelated ``.dsh``
content. Global Desktop registration is covered by
``test_deepseek_harness_desktop.py``.
"""

import json
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
PACKAGE_FILES = ("package.json", "index.mjs", "icon.svg", "cordis.patch.yml", "locale/en.json", "locale/ru.json")


def read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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

    def test_automatic_install_deploys_a_self_contained_package_and_skill(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)

                # Act
                plan = plan_install(request(root, scope), load_catalog(ROOT))
                execute_plan(plan, source_root=ROOT)

                # Assert: the plugin tree is a self-contained native package, so a
                # Host that reads only that directory still finds a working plugin
                # and the executable skill-guidance it resolves.
                package = root / PLUGIN_RUNTIME.parent
                self.assertTrue((root / SKILL_ENTRY).is_file())
                for name in PACKAGE_FILES:
                    self.assertTrue((package / name).is_file(), name)
                self.assertEqual((package / "package.json").read_bytes(),
                                 (ROOT / "adapters/deepseek-harness/plugin/package.json").read_bytes())
                self.assertEqual((package / "skills/prompt-optimizer/SKILL.md").read_bytes(),
                                 (ROOT / ".agents/skills/prompt-optimizer/SKILL.md").read_bytes())
                # The skill travels inside the package, not in a nested tree.
                self.assertFalse((package / "skill").exists())
                mapping = managed_file_map(root, ROOT, scope)
                self.assertEqual(mapping["dsh-skills"][1], root / ".dsh/skills")
                self.assertEqual(mapping["dsh-plugin"][1], root / PLUGIN_RUNTIME.parent)
                self.assertEqual(mapping["dsh-overlay"][1], root / OVERLAY)

    def test_only_a_project_install_keeps_the_explicit_overlay(self):
        for scope, expected in (("project", True), ("global", False)):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)

                # Act
                execute_plan(plan_install(request(root, scope), load_catalog(ROOT)), source_root=ROOT)

                # Assert: a global install registers the native bundle instead, so
                # the overlay that asked for explicit loading is not left behind.
                overlay = root / OVERLAY
                self.assertEqual(overlay.exists(), expected)
                if expected:
                    text = overlay.read_text(encoding="utf-8")
                    self.assertIn("id: universal-prompt-optimizer", text)
                    self.assertIn("name: './plugins/prompt-optimizer/index.mjs'", text)

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

    def test_global_install_mirrors_the_package_into_the_desktop_profile(self):
        # The native manager resolves <profile>/node_modules/<name>, so the same
        # self-contained package is deployed there as well as in .dsh/plugins.
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)

            # Act
            execute_plan(plan_install(request(home, "global"), load_catalog(ROOT)), source_root=ROOT)

            # Assert
            profile = home / ".dsh/profiles/desktop/node_modules/universal-prompt-optimizer"
            installed = home / PLUGIN_RUNTIME.parent
            for name in PACKAGE_FILES:
                self.assertTrue((profile / name).is_file(), name)
                self.assertEqual((profile / name).read_bytes(), (installed / name).read_bytes(), name)
            self.assertEqual((profile / "skills/prompt-optimizer/SKILL.md").read_bytes(),
                             (ROOT / ".agents/skills/prompt-optimizer/SKILL.md").read_bytes())
            self.assertTrue((home / SKILL_ENTRY).is_file())

    def test_dry_run_install_is_read_only_and_reinstall_is_idempotent(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)
                plan = plan_install(request(root, scope), load_catalog(ROOT))

                # Act
                execute_plan(plan, source_root=ROOT, dry_run=True)

                # Assert
                self.assertFalse((root / ".dsh").exists())

                # Act
                execute_plan(plan, source_root=ROOT)
                deployed = {path.relative_to(root).as_posix(): path.read_bytes()
                            for path in (root / ".dsh").rglob("*")
                            if path.is_file() and path.suffix != ".bak"}
                execute_plan(plan, source_root=ROOT)

                # Assert: every deployed artifact is byte-identical after a rerun.
                for relative, content in deployed.items():
                    self.assertEqual((root / relative).read_bytes(), content, relative)
                state = read_state(root, scope)
                self.assertIn(SKILL_ENTRY.as_posix(), state["files"])
                self.assertIn(PLUGIN_RUNTIME.as_posix(), state["files"])
                self.assertIn(f"{PLUGIN_RUNTIME.parent.as_posix()}/skills/prompt-optimizer/SKILL.md", state["files"])
                if scope == "project":
                    self.assertIn(OVERLAY.as_posix(), state["files"])
                # A rerun never duplicates the bundle registration.
                if scope == "global":
                    manifest = (root / ".dsh/profiles/desktop/package.json").read_text(encoding="utf-8")
                    self.assertEqual(manifest.count('"universal-prompt-optimizer"'), 2)

    def test_dry_run_leaves_an_existing_desktop_profile_manifest_untouched(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            manifest = home / ".dsh/profiles/desktop/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"name": "dsh-profile-desktop", "dependencies": {}}', encoding="utf-8")
            before = manifest.read_bytes()

            # Act
            execute_plan(plan_install(request(home, "global"), load_catalog(ROOT)), source_root=ROOT, dry_run=True)

            # Assert
            self.assertEqual(manifest.read_bytes(), before)
            self.assertEqual(sorted(p.name for p in manifest.parent.iterdir()), ["package.json"])
            self.assertFalse((home / ".dsh/plugins").exists())

    def test_install_preserves_unrelated_dsh_files_and_user_content(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
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
                desktop = root / ".dsh/profiles/desktop/cordis.patch.yml"
                desktop.parent.mkdir(parents=True)
                desktop.write_text("# desktop model preferences\n", encoding="utf-8")

                # Act
                execute_plan(plan_install(request(root, scope), load_catalog(ROOT)), source_root=ROOT)

                # Assert
                self.assertEqual(unrelated.read_text(encoding="utf-8"), "user skill")
                self.assertEqual(user_plugin.read_text(encoding="utf-8"), "user plugin")
                self.assertEqual(profile.read_text(encoding="utf-8"), "# user profile overlay\n")
                self.assertEqual(desktop.read_text(encoding="utf-8"), "# desktop model preferences\n")

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

                # Assert: Prompt Optimizer artifacts go, user neighbors stay, and a
                # global uninstall leaves the Host's own profile manifest in place.
                self.assertFalse((root / ".dsh/plugins").exists())
                self.assertFalse((root / OVERLAY).exists())
                self.assertFalse((root / ".dsh/skills/prompt-optimizer").exists())
                self.assertEqual(unrelated.read_text(encoding="utf-8"), "user skill")
                self.assertEqual(unrelated_notes.read_text(encoding="utf-8"), "user notes")
                self.assertEqual(user_config.read_text(encoding="utf-8"), "# user profile overlay\n")
                self.assertFalse(list(root.rglob("*.prompt-optimizer.bak")))
                if scope == "global":
                    manifest = root / ".dsh/profiles/desktop/package.json"
                    self.assertEqual(read_json_file(manifest), {
                        "name": "dsh-profile-desktop",
                        "private": True,
                        "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]}},
                    })
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
        for scope, relative in (("project", ".dsh"), ("project", ".dsh/skills"),
                                ("global", ".dsh/plugins"), ("global", ".dsh/profiles"), ("global", ".dsh/skills")):
            with self.subTest(scope=scope, relative=relative), tempfile.TemporaryDirectory() as raw:
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
                plan = plan_install(request(root, scope), load_catalog(ROOT))

                # Act / Assert
                with self.assertRaises(ValueError):
                    execute_plan(plan, source_root=ROOT)
                self.assertEqual(list(outside.rglob("*")), [])

    def test_inventory_rejects_unowned_dsh_paths(self):
        for scope, relative in (("project", ".dsh/skills/user-skill/SKILL.md"),
                                ("project", ".dsh/plugins/user-plugin/index.mjs"),
                                ("project", ".dsh/cordis.patch.yml"),
                                # The Desktop profile manifest and lock are the Host's,
                                # never part of the installer inventory.
                                ("global", ".dsh/profiles/desktop/package.json"),
                                ("global", ".dsh/profiles/desktop/package.json.lock"),
                                ("global", ".dsh/profiles/desktop/cordis.patch.yml")):
            with self.subTest(scope=scope, relative=relative), tempfile.TemporaryDirectory() as raw:
                # Arrange
                root = Path(raw)

                # Act / Assert
                with self.assertRaises(ValueError):
                    owned_path(root, scope, relative)

    def test_uninstall_targets_classify_deepseek_harness_entries(self):
        # Arrange
        root = Path("/tmp/project")

        # Act
        targets = uninstall_targets(root, ROOT, "project")

        # Assert
        self.assertEqual(targets["dsh-skills"][2], "dir")
        self.assertEqual(targets["dsh-plugin"][2], "dir")
        self.assertEqual(targets["dsh-plugin-skill"][2], "dir")
        self.assertEqual(targets["dsh-overlay"][2], "owned_file")
        self.assertEqual(targets["dsh-plugin"][1], root / ".dsh/plugins/prompt-optimizer")
        self.assertEqual(targets["dsh-profile-plugin"][1],
                         root / ".dsh/profiles/desktop/node_modules/universal-prompt-optimizer")

    def test_first_install_of_a_bundle_happens_before_its_source_files_exist(self):
        # The Desktop payload mirrors the plugin tree, so planning must not depend
        # on files a previous run left behind: a clean root installs from scratch.
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            root = Path(raw)
            self.assertFalse((root / ".dsh").exists())

            # Act
            execute_plan(plan_install(request(root, "global"), load_catalog(ROOT)), source_root=ROOT)

            # Assert
            profile = root / ".dsh/profiles/desktop/node_modules/universal-prompt-optimizer"
            self.assertTrue((profile / "index.mjs").is_file())
            self.assertTrue((profile / "skills/prompt-optimizer/SKILL.md").is_file())
            self.assertEqual((profile / "index.mjs").read_bytes(),
                             (root / PLUGIN_RUNTIME).read_bytes())

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
                self.assertTrue((target / SKILL_ENTRY).is_file())
                self.assertTrue((target / PLUGIN_RUNTIME).is_file())
                self.assertTrue((target / PLUGIN_RUNTIME.parent / "package.json").is_file())
                if scope == "project":
                    # A project install stays explicit: the overlay is written and quoted.
                    self.assertIn("--patch", result.stdout)
                    self.assertTrue((target / OVERLAY).is_file())
                else:
                    # A global install registers the native bundle instead.
                    self.assertTrue((target / ".dsh/profiles/desktop/package.json").is_file())
                    self.assertIn("universal-prompt-optimizer",
                                  (target / ".dsh/profiles/desktop/package.json").read_text(encoding="utf-8"))
                    self.assertFalse((target / OVERLAY).exists())

                # Act
                rerun = run("--auto")

                # Assert
                self.assertIn("universal-prompt-optimizer" if scope == "global" else ".dsh",
                              rerun.stdout)
                self.assertTrue((target / PLUGIN_RUNTIME).is_file())
                if scope == "project":
                    self.assertTrue((target / OVERLAY).is_file())
                    self.assertTrue((target / OVERLAY).with_name(OVERLAY.name + ".prompt-optimizer.bak").is_file())
                else:
                    self.assertEqual(
                        (target / ".dsh/profiles/desktop/package.json").read_text(encoding="utf-8")
                        .count('"universal-prompt-optimizer"'), 2)

                # Act
                remove = [sys.executable, "-B", str(ROOT / "uninstall.py"), "--scope", scope, "--yes"]
                if scope == "project":
                    remove += ["--project", str(root)]
                subprocess.run(remove, capture_output=True, text=True, check=True, env=environment)

                # Assert: everything the installer owns is gone; a global run leaves
                # only the Host's own profile file, which it never owned.
                if scope == "project":
                    self.assertFalse((target / ".dsh").exists())
                else:
                    profile = target / ".dsh/profiles/desktop"
                    self.assertEqual(sorted(p.name for p in profile.iterdir()), ["package.json"])
                    text = (profile / "package.json").read_text(encoding="utf-8")
                    self.assertNotIn("universal-prompt-optimizer", text)
                self.assertFalse(list(target.rglob("*.prompt-optimizer.bak")))


if __name__ == "__main__":
    unittest.main()
