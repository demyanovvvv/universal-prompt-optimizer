"""Consumer-visible DeepSeek Harness Desktop registration.

The Harness Desktop plugin screen manages bundles by reading the profile manifest
(``<home>/.dsh/profiles/desktop/package.json``) plus the package its dependency
names. These tests install the optimizer there and assert what the Host can see
afterwards: the loadable package, the manifest registration, the plugin-list
display metadata, and the untouched neighbours a person already had.

Nothing here launches Harness, runs a package manager or touches the registry.
"""

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

PACKAGE = "universal-prompt-optimizer"
# The dependency spec is relative to the profile directory and points at the
# installer-owned plugin tree, so a native reinstall works without a network.
DEPENDENCY_SPEC = "file:../../plugins/prompt-optimizer"
PLUGIN_TREE = Path(".dsh/plugins/prompt-optimizer")
PROFILE = Path(".dsh/profiles/desktop")
PROFILE_MANIFEST = PROFILE / "package.json"
SKILL_ENTRY = Path(".dsh/skills/prompt-optimizer/SKILL.md")
OVERLAY = Path(".dsh/prompt-optimizer.patch.yml")
PACKAGE_FILES = ("package.json", "index.mjs", "icon.svg", "cordis.patch.yml", "locale/en.json", "locale/ru.json")


def request(root: Path, scope: str, **overrides) -> InstallRequest:
    values = dict(root=root, scope=scope, adapters=frozenset({"deepseek-harness"}), automatic=True)
    values.update(overrides)
    return InstallRequest(**values)


def install(root: Path, scope: str, **overrides) -> InstallPlan:
    plan = plan_install(request(root, scope, **overrides), load_catalog(ROOT))
    execute_plan(plan, source_root=ROOT)
    return plan


def desktop_profile(home: Path, manifest: dict | None = None) -> Path:
    """Create a Desktop profile the way the application leaves it."""
    path = home / PROFILE_MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    value = manifest if manifest is not None else {
        "name": "dsh-profile-desktop",
        "private": True,
        "version": "0.2.0-rc.2",
        "dependencies": {"@deepseek-ai/dsh-base": "0.2.2-rc.3", "@deepseek-ai/dsh-web-app": "0.2.2-rc.3"},
        "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"]}},
    }
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_skill_files() -> dict[str, bytes]:
    source = ROOT / ".agents/skills/prompt-optimizer"
    return {p.relative_to(source).as_posix(): p.read_bytes() for p in source.rglob("*") if p.is_file()}


def activation_entries(patch_text: str) -> list[tuple[str, str]]:
    """Read the loader rows a bundle patch contributes, as ``(id, name)`` pairs."""
    rows, current = [], {}
    for line in patch_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            current = {"id": stripped.split(":", 1)[1].strip()}
        elif stripped.startswith("name:") and current:
            current["name"] = stripped.split(":", 1)[1].strip().strip("'\"")
            rows.append((current["id"], current["name"]))
    return rows


def write_install_state(root: Path, scope: str, *, recorded: list[str]) -> Path:
    """Write the previous installation inventory a global install reads.

    Mirrors what an earlier optimizer release recorded: the scope state file at
    ``<root>/.config/prompt-optimizer/install.json``, adapter, scope and inventory.
    """
    path = root / (".prompt-optimizer-install.json" if scope == "project" else ".config/prompt-optimizer/install.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": 1,
        "scope": scope,
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "adapters": ["deepseek-harness"],
        "automatic": True,
        "settings": {"behavior": "auto", "prompt_scope": "all", "quality_gate": "adaptive", "unsupported_model": "skip"},
        "files": sorted(recorded),
        "created_configs": [],
    }, indent=2) + "\n", encoding="utf-8")
    return path


def files_under(path: Path) -> list[str]:
    """Every regular file below ``path`` relative to it; empty directories ignored."""
    return sorted(p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()) if path.exists() else []


class DesktopBundleRegistrationTests(unittest.TestCase):
    def test_global_install_delivers_a_loadable_native_package(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            desktop_profile(home)

            # Act
            install(home, "global")

            # Assert: the package the profile dependency names carries its own
            # runtime, manifest, patch, locale metadata and the skill it resolves.
            package = home / PLUGIN_TREE
            for name in PACKAGE_FILES:
                self.assertTrue((package / name).is_file(), name)
            self.assertEqual(
                {p.relative_to(package / "skills/prompt-optimizer").as_posix(): p.read_bytes()
                 for p in (package / "skills/prompt-optimizer").rglob("*") if p.is_file()},
                canonical_skill_files(),
            )
            manifest = read_json(package / "package.json")
            self.assertEqual(manifest["name"], PACKAGE)
            self.assertEqual(manifest["version"], f"{(ROOT / 'VERSION').read_text(encoding='utf-8').strip()}.0")
            self.assertIn("./icon.svg", manifest["exports"])

            # The row ID is concise; the name resolves the native package.
            patch = package / manifest["dsh"]["bundle"]["patch"].removeprefix("./")
            self.assertEqual(patch.resolve(), (package / "cordis.patch.yml").resolve())
            self.assertEqual(activation_entries(patch.read_text(encoding="utf-8")),
                             [("prompt-optimizer", PACKAGE)])

    def test_global_install_registers_dependency_and_bundle_selection(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            desktop_profile(home)

            # Act
            install(home, "global")

            # Assert: a person opening the plugin screen sees the bundle listed
            # and enabled, resolved to the installed package.
            manifest = read_json(home / PROFILE_MANIFEST)
            self.assertEqual(manifest["dependencies"][PACKAGE], DEPENDENCY_SPEC)
            self.assertIn(PACKAGE, manifest["dsh"]["profile"]["bundles"])
            self.assertEqual(
                [name for name in manifest["dsh"]["profile"]["bundles"] if name != PACKAGE],
                ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"],
            )
            # The dependency resolves from the profile directory to the payload.
            resolved = (home / PROFILE / DEPENDENCY_SPEC.removeprefix("file:")).resolve()
            self.assertEqual(resolved, (home / PLUGIN_TREE).resolve())
            self.assertEqual(read_json(resolved / "package.json")["name"], PACKAGE)

    def test_global_install_preserves_unrelated_profile_state(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange: a person already has a disabled bundle and other dependencies.
            home = Path(raw)
            path = desktop_profile(home, {
                "name": "dsh-profile-desktop",
                "private": True,
                "dependencies": {
                    "@deepseek-ai/dsh-base": "0.2.2-rc.3",
                    "@deepseek-ai/dsh-experimental-voice-input-bundle": "0.2.2-rc.3",
                },
                "dsh": {"profile": {"bundles": [
                    "@deepseek-ai/dsh-base",
                    "!@deepseek-ai/dsh-experimental-voice-input-bundle",
                ]}},
            })
            preferences = home / PROFILE / "cordis.patch.yml"
            preferences.write_text("# user model preferences\n- insert:\n    - id: model\n", encoding="utf-8")
            neighbor = home / PROFILE / "node_modules/@deepseek-ai/dsh-base/package.json"
            neighbor.parent.mkdir(parents=True)
            neighbor.write_text('{"name":"@deepseek-ai/dsh-base"}', encoding="utf-8")
            before = read_json(path)

            # Act
            install(home, "global")

            # Assert
            manifest = read_json(path)
            self.assertEqual(manifest["name"], before["name"])
            self.assertTrue(manifest["private"])
            self.assertEqual(manifest["dsh"]["profile"]["bundles"][0], "@deepseek-ai/dsh-base")
            self.assertIn("!@deepseek-ai/dsh-experimental-voice-input-bundle", manifest["dsh"]["profile"]["bundles"])
            self.assertEqual(
                {k: v for k, v in manifest["dependencies"].items() if k != PACKAGE},
                before["dependencies"],
            )
            self.assertEqual(preferences.read_text(encoding="utf-8"), "# user model preferences\n- insert:\n    - id: model\n")
            self.assertEqual(read_json(neighbor), {"name": "@deepseek-ai/dsh-base"})

    def test_reinstall_keeps_a_disabled_bundle_choice_and_refreshes_the_payload(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange: the person turned the plugin off after the first install.
            home = Path(raw)
            path = desktop_profile(home)
            install(home, "global")
            manifest = read_json(path)
            manifest["dsh"]["profile"]["bundles"] = [
                "!" + PACKAGE if name == PACKAGE else name for name in manifest["dsh"]["profile"]["bundles"]
            ]
            path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            selected = list(manifest["dsh"]["profile"]["bundles"])
            (home / PLUGIN_TREE / "index.mjs").write_text("// stale runtime\n", encoding="utf-8")

            # Act
            install(home, "global")
            install(home, "global")

            # Assert: the runtime is repaired, the disabled choice is not reverted,
            # and the registration is not duplicated.
            self.assertEqual((home / PLUGIN_TREE / "index.mjs").read_bytes(),
                             (ROOT / "adapters/deepseek-harness/plugin/index.mjs").read_bytes())
            reread = read_json(path)
            self.assertEqual(reread["dsh"]["profile"]["bundles"], selected)
            self.assertEqual(reread["dependencies"][PACKAGE], DEPENDENCY_SPEC)

    def test_reinstall_restores_dependency_without_enabling_a_disabled_bundle(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            manifest = desktop_profile(home)
            values = read_json(manifest)
            values["dsh"]["profile"]["bundles"].append("!" + PACKAGE)
            manifest.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")

            install(home, "global")

            result = read_json(manifest)
            self.assertEqual(result["dependencies"][PACKAGE], DEPENDENCY_SPEC)
            self.assertIn("!" + PACKAGE, result["dsh"]["profile"]["bundles"])
            self.assertNotIn(PACKAGE, result["dsh"]["profile"]["bundles"])

    def test_reinstall_restores_a_missing_skill_inside_the_package(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            desktop_profile(home)
            install(home, "global")
            (home / PLUGIN_TREE / "skills/prompt-optimizer/SKILL.md").unlink()
            (home / PLUGIN_TREE / "locale/ru.json").unlink()

            # Act
            install(home, "global")

            # Assert
            self.assertEqual((home / PLUGIN_TREE / "skills/prompt-optimizer/SKILL.md").read_bytes(),
                             (ROOT / ".agents/skills/prompt-optimizer/SKILL.md").read_bytes())
            self.assertTrue((home / PLUGIN_TREE / "locale/ru.json").is_file())

    def test_missing_desktop_profile_is_initialized_without_touching_its_patch(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange: a home where the application never ran.
            home = Path(raw)

            # Act
            install(home, "global")

            # Assert: the profile is recognizable to the Host, composes the shipped
            # Desktop bundles and leaves the user's own patch file absent.
            manifest = read_json(home / PROFILE_MANIFEST)
            self.assertTrue(manifest["private"])
            self.assertEqual(manifest["name"], "dsh-profile-desktop")
            self.assertEqual(manifest["dependencies"][PACKAGE], DEPENDENCY_SPEC)
            self.assertEqual(manifest["dsh"]["profile"]["bundles"],
                             ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app", PACKAGE])
            self.assertFalse((home / PROFILE / "cordis.patch.yml").exists())


    def test_no_auto_global_install_registers_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            path = desktop_profile(home)
            before = path.read_bytes()

            # Act
            install(home, "global", automatic=False)

            # Assert: skills only, no plugin and no registration.
            self.assertTrue((home / SKILL_ENTRY).is_file())
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((home / PLUGIN_TREE).exists())
            self.assertEqual(files_under(home / PROFILE), ["package.json"])

    def test_project_install_stays_explicit_and_out_of_the_desktop_profile(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            root = home / "project"
            root.mkdir()
            path = desktop_profile(home)
            before = path.read_bytes()

            # Act
            install(root, "project")

            # Assert: same self-contained package, activated only through --patch.
            for name in PACKAGE_FILES:
                self.assertTrue((root / PLUGIN_TREE / name).is_file(), name)
            self.assertTrue((root / PLUGIN_TREE / "skills/prompt-optimizer/SKILL.md").is_file())
            self.assertTrue((root / SKILL_ENTRY).is_file())
            self.assertEqual(
                activation_entries((root / OVERLAY).read_text(encoding="utf-8")),
                [(PACKAGE, "./plugins/prompt-optimizer/index.mjs")],
            )
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(files_under(home / PROFILE), ["package.json"])

    def test_dry_run_desktop_install_writes_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            path = desktop_profile(home)
            before = path.read_bytes()
            plan = plan_install(request(home, "global"), load_catalog(ROOT))

            # Act
            execute_plan(plan, source_root=ROOT, dry_run=True)

            # Assert
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((home / PLUGIN_TREE).exists())
            self.assertFalse((home / PROFILE / "node_modules").exists())
            self.assertEqual(files_under(home / PROFILE), ["package.json"])
            self.assertFalse((home / SKILL_ENTRY).exists())

    def test_global_install_withdraws_only_the_overlay_a_previous_install_recorded(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange: an earlier optimizer release recorded the overlay in its
            # installation inventory, next to a same-named file it never owned.
            home = Path(raw)
            desktop_profile(home)
            overlay = home / OVERLAY
            overlay.parent.mkdir(parents=True, exist_ok=True)
            overlay.write_bytes((ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            overlay.with_name(overlay.name + ".prompt-optimizer.bak").write_bytes(
                (ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            write_install_state(home, "global", recorded=[OVERLAY.as_posix()])
            untracked = home / "project"
            untracked.mkdir()
            (untracked / ".dsh").mkdir()
            (untracked / OVERLAY).write_bytes(
                (ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())

            # Act
            install(home, "global")

            # Assert: the recorded overlay and its backup are gone, while the same
            # text outside the recorded inventory is preserved untouched.
            self.assertFalse(overlay.exists())
            self.assertFalse(overlay.with_name(overlay.name + ".prompt-optimizer.bak").exists())
            self.assertEqual((untracked / OVERLAY).read_bytes(),
                             (ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            self.assertIn(PACKAGE, read_json(home / PROFILE_MANIFEST)["dependencies"])

    def test_unrecorded_overlay_is_left_for_a_human_to_remove(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange: a hand-written overlay the inventory never recorded.
            home = Path(raw)
            desktop_profile(home)
            overlay = home / OVERLAY
            overlay.parent.mkdir(parents=True, exist_ok=True)
            overlay.write_bytes((ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            self.assertFalse((home / ".config/prompt-optimizer/install.json").exists())

            # Act
            install(home, "global")

            # Assert: nothing claimed it, so nothing deletes it.
            self.assertEqual(overlay.read_bytes(),
                             (ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            self.assertIn(PACKAGE, read_json(home / PROFILE_MANIFEST)["dependencies"])

    def test_uninstall_removes_registration_and_payload_but_keeps_neighbors(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            path = desktop_profile(home)
            install(home, "global")
            keep_manifest = home / PROFILE / "node_modules/@deepseek-ai/dsh-base/package.json"
            keep_manifest.parent.mkdir(parents=True)
            keep_manifest.write_text('{"name":"@deepseek-ai/dsh-base"}', encoding="utf-8")
            preferences = home / PROFILE / "cordis.patch.yml"
            preferences.write_text("# user model preferences\n", encoding="utf-8")

            # Act
            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)
            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)

            # Assert
            manifest = read_json(path)
            self.assertNotIn(PACKAGE, manifest.get("dependencies", {}))
            self.assertEqual(manifest["dsh"]["profile"]["bundles"], ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"])
            self.assertFalse((home / PLUGIN_TREE).exists())
            self.assertFalse((home / SKILL_ENTRY).exists())
            self.assertFalse((home / OVERLAY).exists())
            self.assertEqual(read_json(keep_manifest), {"name": "@deepseek-ai/dsh-base"})
            self.assertEqual(preferences.read_text(encoding="utf-8"), "# user model preferences\n")
            self.assertFalse(list(home.rglob("*.prompt-optimizer.bak")))

    def test_uninstall_removes_a_disabled_owned_bundle_selection(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            manifest = desktop_profile(home)
            install(home, "global")
            values = read_json(manifest)
            values["dsh"]["profile"]["bundles"] = [
                "!" + item if item == PACKAGE else item
                for item in values["dsh"]["profile"]["bundles"]
            ]
            manifest.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")

            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)

            result = read_json(manifest)
            self.assertNotIn(PACKAGE, result.get("dependencies", {}))
            self.assertNotIn("!" + PACKAGE, result["dsh"]["profile"]["bundles"])
            self.assertEqual(result["dsh"]["profile"]["bundles"],
                             ["@deepseek-ai/dsh-base", "@deepseek-ai/dsh-web-app"])

    def test_uninstall_without_harness_inventory_preserves_unowned_registration_and_files(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            manifest = desktop_profile(home)
            values = read_json(manifest)
            values["dependencies"][PACKAGE] = DEPENDENCY_SPEC
            values["dsh"]["profile"]["bundles"].append(PACKAGE)
            manifest.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
            overlay = home / OVERLAY
            overlay.parent.mkdir(parents=True, exist_ok=True)
            overlay.write_bytes((ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            overlay_backup = overlay.with_name(overlay.name + ".prompt-optimizer.bak")
            overlay_backup.write_bytes(b"user backup\n")
            plugin = home / PLUGIN_TREE / "package.json"
            plugin.parent.mkdir(parents=True)
            plugin.write_text(json.dumps({"name": PACKAGE}), encoding="utf-8")
            before = manifest.read_bytes()

            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)

            self.assertEqual(manifest.read_bytes(), before)
            self.assertEqual(overlay.read_bytes(),
                             (ROOT / "adapters/deepseek-harness/prompt-optimizer.patch.yml").read_bytes())
            self.assertEqual(overlay_backup.read_bytes(), b"user backup\n")
            self.assertEqual(read_json(plugin), {"name": PACKAGE})


    def test_uninstall_removes_unlisted_native_package_files(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            desktop_profile(home)
            install(home, "global")
            extra = home / PLUGIN_TREE / "user-added.txt"
            extra.write_text("inside owned plugin package", encoding="utf-8")
            profile_extra = home / PROFILE / "node_modules" / PACKAGE / "user-added.txt"
            profile_extra.write_text("inside mirrored owned package", encoding="utf-8")

            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)

            self.assertFalse((home / PLUGIN_TREE).exists())
            self.assertFalse(profile_extra.exists())

    def test_uninstall_removes_bundle_selection_when_owned_dependency_is_missing(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            manifest = desktop_profile(home)
            install(home, "global")
            values = read_json(manifest)
            values["dependencies"].pop(PACKAGE)
            values["dsh"]["profile"]["bundles"].append("!" + PACKAGE)
            manifest.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")

            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)

            result = read_json(manifest)
            self.assertNotIn(PACKAGE, result.get("dependencies", {}))
            self.assertNotIn(PACKAGE, result["dsh"]["profile"]["bundles"])
            self.assertNotIn("!" + PACKAGE, result["dsh"]["profile"]["bundles"])

    def test_json_null_bundle_dependency_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            manifest = desktop_profile(home)
            values = read_json(manifest)
            values["dependencies"][PACKAGE] = None
            manifest.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
            before = manifest.read_bytes()

            with self.assertRaises(ValueError):
                install(home, "global")

            self.assertEqual(manifest.read_bytes(), before)
            self.assertFalse((home / PLUGIN_TREE).exists())

    def test_uninstall_preserves_conflicting_foreign_dependency_and_bundle(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            manifest = desktop_profile(home)
            install(home, "global")
            values = read_json(manifest)
            values["dependencies"][PACKAGE] = "^9.0.0"
            manifest.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
            before = manifest.read_bytes()

            execute_plan(build_uninstall_plan(home, ROOT, "global"), source_root=ROOT, backup=False)

            self.assertEqual(manifest.read_bytes(), before)
            self.assertFalse((home / PLUGIN_TREE).exists())


class DesktopLockAndBackupTests(unittest.TestCase):
    def test_failed_fresh_global_install_releases_lock_before_pruning_profile(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            plan = plan_install(request(home, "global"), load_catalog(ROOT))
            failing = InstallPlan((*plan.operations, Operation("merge", home / ".config/broken.json", content=b"not json")))

            with self.assertRaises(ValueError):
                execute_plan(failing, source_root=ROOT)

            self.assertFalse((home / ".dsh").exists())
            self.assertFalse((home / ".config").exists())
    def test_successful_install_leaves_no_manifest_lock_behind(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            desktop_profile(home)

            install(home, "global")

            self.assertFalse((home / PROFILE / "package.json.lock").exists())
            self.assertIn("package.json", files_under(home / PROFILE))
            self.assertIn(f"node_modules/{PACKAGE}/index.mjs", files_under(home / PROFILE))

    def test_concurrent_manifest_lock_blocks_the_install_before_writing(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            path = desktop_profile(home)
            before = path.read_bytes()
            lock = home / PROFILE / "package.json.lock"
            lock.write_text("4242\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                install(home, "global")

            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((home / PLUGIN_TREE).exists())
            self.assertEqual(lock.read_text(encoding="utf-8"), "4242\n")

    def test_failed_edit_does_not_leave_the_lock_or_a_manifest_backup(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            desktop_profile(home)
            plan = plan_install(request(home, "global"), load_catalog(ROOT))
            failing = InstallPlan((*plan.operations, Operation("merge", home / "broken.json", content=b"not json")))

            with self.assertRaises(ValueError):
                execute_plan(failing, source_root=ROOT)

            self.assertFalse((home / PROFILE / "package.json.lock").exists())
            self.assertFalse((home / PROFILE / "package.json.prompt-optimizer.bak").exists())




class DesktopRegistryRefusalTests(unittest.TestCase):
    def test_json_null_bundle_dependency_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            path = desktop_profile(home)
            manifest = read_json(path)
            manifest["dependencies"][PACKAGE] = None
            path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            before = path.read_bytes()

            with self.assertRaises(ValueError):
                install(home, "global")

            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((home / PLUGIN_TREE).exists())

        cases = {
            "broken json": "{not json",
            "non-object root": '["profile"]',
            "non-object dsh": '{"name": "dsh-profile-desktop", "dsh": 1}',
            "non-object profile": '{"name": "dsh-profile-desktop", "dsh": {"profile": 1}}',
            "non-array bundles": '{"name": "dsh-profile-desktop", "dsh": {"profile": {"bundles": "x"}}}',
            "foreign profile": '{"name": "some-other-profile", "dependencies": {}}',
        }
        for label, content in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                # Arrange
                home = Path(raw)
                path = home / PROFILE_MANIFEST
                path.parent.mkdir(parents=True)
                path.write_text(content, encoding="utf-8")

                # Act / Assert
                with self.assertRaises(ValueError):
                    install(home, "global")
                self.assertEqual(path.read_text(encoding="utf-8"), content)
                self.assertFalse((home / PLUGIN_TREE).exists())

    def test_colliding_unowned_package_is_refused_and_left_alone(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange: the plugin path holds somebody else's package.
            home = Path(raw)
            desktop_profile(home)
            foreign = home / PLUGIN_TREE / "package.json"
            foreign.parent.mkdir(parents=True)
            foreign.write_text('{"name": "someone-elses-plugin"}', encoding="utf-8")

            # Act / Assert
            with self.assertRaises(ValueError):
                install(home, "global")
            self.assertEqual(read_json(foreign), {"name": "someone-elses-plugin"})
            self.assertNotIn(PACKAGE, read_json(home / PROFILE_MANIFEST).get("dependencies", {}))

    def test_foreign_dependency_with_the_same_name_is_refused(self):
        for version in ("^9.0.0", "file:../../elsewhere", "git+https://example.invalid/other"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as raw:
                # Arrange
                home = Path(raw)
                path = desktop_profile(home)
                manifest = read_json(path)
                manifest["dependencies"][PACKAGE] = version
                path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                before = path.read_bytes()

                # Act / Assert
                with self.assertRaises(ValueError):
                    install(home, "global")
                self.assertEqual(path.read_bytes(), before)

    def test_symlinked_profile_components_are_refused(self):
        for relative in (".dsh", ".dsh/profiles", ".dsh/profiles/desktop"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                # Arrange
                home = Path(raw)
                outside = home / "outside"
                outside.mkdir()
                link = home / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                try:
                    link.symlink_to(outside, target_is_directory=True)
                except (OSError, NotImplementedError) as exc:
                    self.skipTest(f"symlinks unavailable: {exc}")

                # Act / Assert
                with self.assertRaises(ValueError):
                    install(home, "global")
                self.assertEqual(list(outside.rglob("*")), [])

    def test_late_failure_rolls_back_registration_and_payload(self):
        with tempfile.TemporaryDirectory() as raw:
            # Arrange
            home = Path(raw)
            path = desktop_profile(home)
            before = path.read_bytes()
            replacement = before.replace(b'"version"', b'"kept"')
            path.write_bytes(replacement)
            plan = plan_install(request(home, "global"), load_catalog(ROOT))
            failing = InstallPlan((*plan.operations, Operation("merge", home / "broken.json", content=b"not json")))

            # Act / Assert
            with self.assertRaises(ValueError):
                execute_plan(failing, source_root=ROOT)
            self.assertEqual(path.read_bytes(), replacement)
            self.assertFalse((home / PLUGIN_TREE).exists())
            self.assertFalse((home / SKILL_ENTRY).exists())
            self.assertEqual(files_under(home / PROFILE), ["package.json"])


if __name__ == "__main__":
    unittest.main()
