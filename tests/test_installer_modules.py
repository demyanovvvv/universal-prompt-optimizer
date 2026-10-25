import tempfile
import unittest
import json
from pathlib import Path

from installer import catalog, filesystem, transaction
from installer.domain import InstallRequest
from installer.planning import plan_config_write, plan_install
from installer.executor import execute_plan
from installer.domain import InstallPlan, Operation
from installer.locking import InstallLock
from installer.planning import validate_request

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

LEGACY_MODEL_COMMANDS = {
    "prompt-claude-opus-5-5.md": """---
description: Optimize and execute with the Claude Opus 5.5 profile
---
Use the `prompt-claude-opus-5-5` skill for the following task. Preserve the user's language and constraints, then execute it unless the user requests prompt-only mode.

$ARGUMENTS
""",
    "prompt-claude-fable-5-1.md": """---
description: Optimize and execute with the Claude Fable 5.1 profile
---
Use the `prompt-claude-fable-5-1` skill for the following task. Preserve the user's language and constraints, then execute it unless the user requests prompt-only mode.

$ARGUMENTS
""",
    "prompt-sol.md": """---
description: Optimize this task for GPT-6 Sol, then execute it.
---
Use the `prompt-sol` skill for this request.

$ARGUMENTS
""",
}


class InstallerModuleTests(unittest.TestCase):
    def test_catalog_is_explicit_and_validates_unknown_adapter(self):
        value = catalog.load_catalog(ROOT)
        self.assertEqual(value.ids, frozenset({"opencode", "codex", "cursor", "pi", "omp", "claude", "gemini", "copilot", "windsurf"}))
        with self.assertRaises(ValueError):
            value.require({"missing"})

    def test_atomic_write_and_transaction_restore_file_and_mode(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "value.txt"
            path.write_text("before", encoding="utf-8")
            path.chmod(0o640)
            with transaction.InstallTransaction() as active:
                active.record(path)
                filesystem.atomic_write_text(path, "after")
                active.rollback()
            self.assertEqual(path.read_text(encoding="utf-8"), "before")

    def test_atomic_write_creates_parent_and_rejects_directory_destination(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "nested" / "value.txt"
            filesystem.atomic_write_text(target, "ok")
            self.assertEqual(target.read_text(encoding="utf-8"), "ok")
            with self.assertRaises(ValueError):
                filesystem.atomic_write_text(target.parent, "bad")

    def test_install_planner_is_pure_and_covers_standalone_routing_asset(self):
        manifest = catalog.load_catalog(ROOT)
        request = InstallRequest(Path("/tmp/project"), "project", frozenset({"opencode", "pi"}), automatic=True)
        plan = plan_install(request, manifest)
        paths = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/project/.opencode/plugins/prompt-optimizer", paths)
        self.assertIn("/tmp/project/.pi/extensions", paths)
        config = next(operation for operation in plan.operations if operation.label == "managed configuration")
        self.assertIn(b'"qualityGate": "adaptive"', config.content or b"")

    def test_config_planner_preserves_existing_user_fields(self):
        operation = plan_config_write(Path("/tmp/config.json"), {"behavior": "off"}, existing='{"custom":true}')
        self.assertIn(b'"custom": true', operation.content or b"")

    def test_lock_is_explicit_and_releases_after_scope(self):
        with tempfile.TemporaryDirectory() as raw:
            lock_path = Path(raw) / "install.lock"
            validate = lambda path: None
            with InstallLock(lock_path, validate):
                self.assertTrue(lock_path.exists())
                with self.assertRaises(RuntimeError):
                    with InstallLock(lock_path, validate):
                        pass
            self.assertFalse(lock_path.exists())

    def test_catalog_rejects_duplicate_ids_at_source(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "adapters").mkdir()
            (root / "adapters/manifest.json").write_text('{"schemaVersion":1,"adapters":["pi","pi"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                catalog.load_catalog(root)

    def test_install_plan_rejects_invalid_scope_and_unknown_adapter(self):
        manifest = catalog.load_catalog(ROOT)
        with self.assertRaises(ValueError):
            validate_request(InstallRequest(Path("/tmp"), "bad", frozenset({"pi"})), manifest)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            plan_install(InstallRequest(Path("/tmp"), "project", frozenset({"missing"})), manifest)

    def test_install_plan_validates_all_managed_request_fields(self):
        manifest = catalog.load_catalog(ROOT)
        base = dict(root=Path("/tmp"), scope="project", adapters=frozenset({"pi"}))
        for field, value in {
            "prompt_scope": "middle",
            "quality_gate": "unknown",
            "unsupported_model": "error",
            "python_bin": "",
        }.items():
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    validate_request(InstallRequest(**{**base, field: value}), manifest)  # type: ignore[arg-type]

    def test_executor_applies_plan_and_preserves_existing_user_file(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source"
            source.mkdir()
            (source / "nested.txt").write_text("new", encoding="utf-8")
            destination = root / "destination"
            (destination / "nested.txt").parent.mkdir(parents=True)
            (destination / "nested.txt").write_text("old", encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"pi"}), automatic=True),
                catalog.AdapterCatalog(frozenset({"pi"})),
            )
            # Exercise the generic executor with a source-relative copy and a write.
            plan = type(plan)(
                (
                    plan.operations[0].__class__("copy_tree", destination, source=Path("source")),
                    plan_config_write(root / "config.json", {"behavior": "auto"}),
                )
            )
            execute_plan(plan, source_root=root)
            self.assertEqual((destination / "nested.txt").read_text(encoding="utf-8"), "new")
            self.assertTrue((root / "config.json").exists())

    def test_generated_pi_plan_is_executable_and_dry_run_is_read_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            request = InstallRequest(root, "project", frozenset({"pi"}), automatic=True)
            plan = plan_install(request, catalog.load_catalog(ROOT))
            execute_plan(plan, source_root=ROOT, dry_run=True)
            self.assertFalse((root / ".pi").exists())
            execute_plan(plan, source_root=ROOT)
            extension = root / ".pi/extensions/prompt-optimizer.ts"
            self.assertTrue(extension.is_file())
            self.assertTrue((root / ".pi/extensions/model-registry.ts").is_file())

    def test_omp_plan_is_self_contained_in_native_project_and_global_roots(self):
        from installer.state import owned_path
        from installer.lifecycle import build_uninstall_plan, managed_file_map
        for scope, relative in (("project", ".omp/extensions"), ("global", ".omp/agent/extensions")):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                request = InstallRequest(root, scope, frozenset({"omp"}), automatic=True)
                plan = plan_install(request, catalog.load_catalog(ROOT))
                execute_plan(plan, source_root=ROOT, dry_run=True)
                self.assertFalse((root / ".omp").exists())
                execute_plan(plan, source_root=ROOT)
                base = root / relative
                for name in ("index.ts", "runtime.ts", "model-registry.ts"):
                    path = base / "prompt-optimizer" / name
                    self.assertTrue(path.is_file())
                    self.assertEqual(owned_path(root, scope, path.relative_to(root).as_posix()), path)
                self.assertEqual(managed_file_map(root, ROOT, scope)["omp-extension"][1], base)
                neighbor = base / "user-extension.ts"
                neighbor.write_text("user extension", encoding="utf-8")
                execute_plan(plan, source_root=ROOT)
                execute_plan(build_uninstall_plan(root, ROOT, scope), source_root=ROOT, backup=False)
                self.assertFalse((base / "prompt-optimizer/index.ts").exists())
                self.assertEqual(neighbor.read_text(encoding="utf-8"), "user extension")

    def test_plan_install_includes_cursor_and_gemini_deployable_files(self):
        request = InstallRequest(
            Path("/tmp/project"), "project", frozenset({"cursor", "gemini"}),
            automatic=True, python_bin="python-custom",
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/project/.cursor/hooks/prompt-optimizer-state.py", destinations)
        self.assertIn("/tmp/project/.cursor/rules/prompt-optimizer.mdc", destinations)
        self.assertIn("/tmp/project/.gemini/hooks/prompt-preflight.py", destinations)
        self.assertIn("/tmp/project/.prompt-optimizer.json", destinations)

    def test_plan_install_includes_shared_skills_and_opencode_commands(self):
        request = InstallRequest(
            Path("/tmp/project"), "project", frozenset({"opencode", "claude"}), automatic=False,
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/project/.agents/skills", destinations)
        self.assertIn("/tmp/project/.claude/skills", destinations)
        self.assertIn("/tmp/project/.opencode/commands", destinations)

    def test_global_plan_uses_global_skill_command_and_config_destinations(self):
        request = InstallRequest(
            Path("/tmp/home"), "global", frozenset({"opencode", "claude"}), automatic=True,
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/home/.agents/skills", destinations)
        self.assertIn("/tmp/home/.claude/skills", destinations)
        self.assertIn("/tmp/home/.config/opencode/commands", destinations)
        self.assertIn("/tmp/home/.config/prompt-optimizer/config.json", destinations)

    def test_plan_snippet_block_matches_legacy_configured_block(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("upo_install", ROOT / "install.py")
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        from installer.content import configured_snippet_block

        snippet = (ROOT / "auto/GEMINI.snippet.md").read_text(encoding="utf-8")
        for gate in ("adaptive", "pass", "light", "full", True, False):
            expected = legacy.configured_block("auto/GEMINI.snippet.md", "auto", "all", gate, "skip")
            actual = configured_snippet_block(snippet, "auto", "all", "skip", gate)
            self.assertEqual(actual.strip(), expected.strip(), gate)

    def test_plan_shared_config_matches_legacy_managed_config(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("upo_install", ROOT / "install.py")
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        from config_contract import managed_config

        for gate in ("adaptive", "pass", True, False):
            self.assertEqual(managed_config("auto", "all", "skip", gate), legacy.managed_config("auto", "all", "skip", gate))

    def test_project_resources_execute_without_deleting_extra_user_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            custom_skill = root / ".agents/skills/custom-skill/notes.md"
            custom_skill.parent.mkdir(parents=True)
            custom_skill.write_text("user-owned", encoding="utf-8")
            custom_command = root / ".opencode/commands/custom.md"
            custom_command.parent.mkdir(parents=True)
            custom_command.write_text("user-command", encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"opencode"}), automatic=False),
                catalog.load_catalog(ROOT),
            )
            execute_plan(plan, source_root=ROOT)
            self.assertEqual(custom_skill.read_text(encoding="utf-8"), "user-owned")
            self.assertEqual(custom_command.read_text(encoding="utf-8"), "user-command")
            self.assertTrue((root / ".agents/skills/prompt-optimizer/SKILL.md").is_file())
            self.assertTrue((root / ".opencode/commands/prompt.md").is_file())
            self.assertFalse((root / ".opencode/commands/prompt-luna.md").exists())

    def test_install_migrates_legacy_model_commands_to_universal_commands(self):
        for scope in ("project", "global"):
            with self.subTest(scope=scope), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                commands = root / (".opencode/commands" if scope == "project" else ".config/opencode/commands")
                commands.mkdir(parents=True)
                for name, content in LEGACY_MODEL_COMMANDS.items():
                    (commands / name).write_text(content, encoding="utf-8")
                custom = commands / "custom.md"
                custom.write_text("user-command", encoding="utf-8")
                plan = plan_install(
                    InstallRequest(root, scope, frozenset({"opencode"}), automatic=False),
                    catalog.load_catalog(ROOT),
                )
                execute_plan(plan, source_root=ROOT, dry_run=True)
                for name, content in LEGACY_MODEL_COMMANDS.items():
                    self.assertEqual((commands / name).read_text(encoding="utf-8"), content)
                for _ in range(2):
                    execute_plan(plan, source_root=ROOT)
                    self.assertEqual(
                        {path.name for path in commands.glob("*.md")},
                        {"prompt.md", "prompt-only.md", "prompt-optimizer.md", "custom.md"},
                    )
                    self.assertEqual(custom.read_text(encoding="utf-8"), "user-command")

    def test_install_preserves_modified_or_mismatched_legacy_model_commands(self):
        for name, legacy in LEGACY_MODEL_COMMANDS.items():
            variants = {
                "appended instructions": legacy + "Custom instructions.\n",
                "changed task": legacy.replace("$ARGUMENTS", "Custom task: $ARGUMENTS"),
                "changed skill": legacy.replace(name.removesuffix(".md"), "prompt-custom"),
                "extra frontmatter": legacy.replace("\n---\n", "\nagent: custom\n---\n"),
                "custom content": "user-owned model command\n",
            }
            for label, content in variants.items():
                with self.subTest(command=name, change=label), tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    command = root / ".opencode/commands" / name
                    command.parent.mkdir(parents=True)
                    command.write_text(content, encoding="utf-8")
                    plan = plan_install(
                        InstallRequest(root, "project", frozenset({"opencode"}), automatic=False),
                        catalog.load_catalog(ROOT),
                    )
                    execute_plan(plan, source_root=ROOT)
                    self.assertEqual(command.read_text(encoding="utf-8"), content)

    def test_legacy_model_command_cleanup_rolls_back_on_install_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            commands = root / ".opencode/commands"
            commands.mkdir(parents=True)
            for name, content in LEGACY_MODEL_COMMANDS.items():
                (commands / name).write_text(content, encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"opencode"}), automatic=False),
                catalog.load_catalog(ROOT),
            )
            failing = InstallPlan((*plan.operations, Operation("merge", root / "broken.json", content=b"not json")))
            with self.assertRaises(ValueError):
                execute_plan(failing, source_root=ROOT)
            for name, content in LEGACY_MODEL_COMMANDS.items():
                self.assertEqual((commands / name).read_text(encoding="utf-8"), content)
            self.assertFalse((commands / "prompt.md").exists())

    def test_install_removes_only_unchanged_legacy_po_status_command(self):
        legacy = """---
description: Show Prompt Optimizer status for the current OpenCode session.
---
Use the Prompt Optimizer server plugin state for this session. Report the
resolved mode, scope, quality gate, model/profile and privacy-safe counters.
Do not edit persistent configuration and do not reveal hidden reasoning.
"""
        for content, removed in [(legacy, True), (legacy + "Custom instructions.\n", False)]:
            with self.subTest(removed=removed), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                command = root / ".opencode/commands/po-status.md"
                command.parent.mkdir(parents=True)
                command.write_text(content, encoding="utf-8")
                plan = plan_install(InstallRequest(root, "project", frozenset({"opencode"}), automatic=True), catalog.load_catalog(ROOT))
                execute_plan(plan, source_root=ROOT)
                self.assertEqual(command.exists(), not removed)
                if not removed:
                    self.assertEqual(command.read_text(encoding="utf-8"), content)

    def test_project_plan_contains_gemini_managed_block_and_opencode_tui_registration(self):
        request = InstallRequest(
            Path("/tmp/project"), "project", frozenset({"gemini", "opencode"}), automatic=True,
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/project/GEMINI.md", destinations)
        self.assertIn("/tmp/project/.opencode/tui.json", destinations)
        self.assertIn("/tmp/project/.opencode/plugins/prompt-optimizer-tui/.prompt-optimizer-owner.json", destinations)

    def test_global_gemini_plan_uses_global_document_and_runtime_ignores(self):
        request = InstallRequest(
            Path("/tmp/home"), "global", frozenset({"gemini"}), automatic=True,
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/home/.gemini/GEMINI.md", destinations)
        self.assertNotIn("/tmp/home/GEMINI.md", destinations)
        ignore_operations = [operation for operation in plan.operations if operation.kind == "merge_ignore"]
        self.assertEqual(len(ignore_operations), 1)
        self.assertEqual(ignore_operations[0].path, Path("/tmp/home/.gitignore"))

    def test_gemini_auto_execution_preserves_user_settings_and_adds_runtime_ignores(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            settings = root / ".gemini/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({"custom": True}), encoding="utf-8")
            ignore = root / ".gitignore"
            ignore.write_text("# user entry\n", encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"gemini"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            execute_plan(plan, source_root=ROOT)
            value = json.loads(settings.read_text(encoding="utf-8"))
            self.assertTrue(value["custom"])
            self.assertIn("BeforeAgent", value["hooks"])
            self.assertIn("BeforeModel", value["hooks"])
            ignored = ignore.read_text(encoding="utf-8")
            self.assertIn(".gemini/.prompt-optimizer-model-state.json", ignored)
            self.assertIn(".gemini/*.prompt-optimizer-*.json.lock", ignored)

    def test_auto_markdown_adapters_plan_project_destinations(self):
        request = InstallRequest(
            Path("/tmp/project"), "project", frozenset({"claude", "codex", "copilot", "windsurf"}), automatic=True,
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/project/CLAUDE.md", destinations)
        self.assertIn("/tmp/project/AGENTS.md", destinations)
        self.assertIn("/tmp/project/.github/copilot-instructions.md", destinations)
        self.assertIn("/tmp/project/.windsurf/rules/prompt-optimizer.md", destinations)

    def test_auto_markdown_adapters_plan_global_destinations(self):
        request = InstallRequest(
            Path("/tmp/home"), "global", frozenset({"claude", "codex", "copilot", "windsurf"}), automatic=True,
        )
        plan = plan_install(request, catalog.load_catalog(ROOT))
        destinations = {operation.path.as_posix() for operation in plan.operations}
        self.assertIn("/tmp/home/.claude/CLAUDE.md", destinations)
        self.assertIn("/tmp/home/.codex/AGENTS.md", destinations)
        self.assertIn("/tmp/home/.copilot/copilot-instructions.md", destinations)
        self.assertIn("/tmp/home/.codeium/windsurf/memories/global_rules.md", destinations)
        windsurf = [operation for operation in plan.operations if operation.path.as_posix() == "/tmp/home/.codeium/windsurf/memories/global_rules.md"]
        self.assertEqual(windsurf[0].kind, "merge_block")

    def test_auto_markdown_blocks_use_shared_snippets_and_preserve_user_content(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            claude_doc = root / "CLAUDE.md"
            claude_doc.write_text("User notes\n", encoding="utf-8")
            windsurf_dir = root / ".windsurf/rules"
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"claude", "codex", "copilot", "windsurf"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            execute_plan(plan, source_root=ROOT)
            document = claude_doc.read_text(encoding="utf-8")
            self.assertTrue(document.startswith("User notes"))
            self.assertIn(f"## Prompt Optimizer v{PACKAGE_VERSION}", document)
            self.assertIn("canonical `.agents/skills/prompt-optimizer/SKILL.md`", document)
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn(f"## Prompt Optimizer v{PACKAGE_VERSION} preflight", agents)
            self.assertTrue((root / ".github/copilot-instructions.md").is_file())
            self.assertTrue((root / ".windsurf/rules/prompt-optimizer.md").is_file())

    def test_auto_markdown_block_is_idempotent_across_reinstall(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            request = InstallRequest(root, "project", frozenset({"codex"}), automatic=True)
            plan = plan_install(request, catalog.load_catalog(ROOT))
            execute_plan(plan, source_root=ROOT)
            first = (root / "AGENTS.md").read_text(encoding="utf-8")
            execute_plan(plan, source_root=ROOT)
            self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), first)

    def test_executor_merges_managed_block_and_tui_config_preserving_user_content(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            gemini_doc = root / "GEMINI.md"
            gemini_doc.write_text("User notes\n", encoding="utf-8")
            tui_config = root / ".opencode/tui.json"
            tui_config.parent.mkdir(parents=True)
            tui_config.write_text('{"plugin":["./user-plugin.tsx"],"custom":true}', encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"gemini", "opencode"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            execute_plan(plan, source_root=ROOT)
            document = gemini_doc.read_text(encoding="utf-8")
            self.assertTrue(document.startswith("User notes"))
            self.assertIn("<!-- prompt-optimizer:auto:start -->", document)
            tui = json.loads(tui_config.read_text(encoding="utf-8"))
            self.assertTrue(tui["custom"])
            self.assertIn("./user-plugin.tsx", tui["plugin"])
            self.assertIn("./plugins/prompt-optimizer-tui/prompt-optimizer.tsx", tui["plugin"])

    def test_tui_owned_file_guard_and_managed_block_validation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tui_plugin = root / ".opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            tui_plugin.parent.mkdir(parents=True)
            tui_plugin.write_text("user plugin", encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"opencode"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            with self.assertRaises(ValueError):
                execute_plan(plan, source_root=ROOT)
            self.assertEqual(tui_plugin.read_text(encoding="utf-8"), "user plugin")

            bad_doc = root / "GEMINI.md"
            bad_doc.write_text("<!-- prompt-optimizer:auto:start -->\nmissing end", encoding="utf-8")
            gemini_plan = plan_install(
                InstallRequest(root, "project", frozenset({"gemini"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            with self.assertRaises(ValueError):
                execute_plan(gemini_plan, source_root=ROOT)
            self.assertEqual(bad_doc.read_text(encoding="utf-8"), "<!-- prompt-optimizer:auto:start -->\nmissing end")

    def test_cursor_plan_merges_runtime_ignore_block_without_losing_user_lines(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            gitignore = root / ".gitignore"
            gitignore.write_text("user-pattern\n", encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"cursor"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            self.assertIn(gitignore, {operation.path for operation in plan.operations})
            execute_plan(plan, source_root=ROOT)
            value = gitignore.read_text(encoding="utf-8")
            self.assertIn("user-pattern", value)
            self.assertIn("# prompt-optimizer:runtime:start", value)
            self.assertIn(".cursor/.prompt-optimizer-runtime.json", value)
            self.assertIn(".cursor/.prompt-optimizer-session-state.json", value)

    def test_cursor_runtime_ignore_merge_is_idempotent_and_rejects_incomplete_markers(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / ".gitignore"
            request = InstallRequest(root, "project", frozenset({"cursor"}), automatic=True)
            plan = plan_install(request, catalog.load_catalog(ROOT))
            execute_plan(plan, source_root=ROOT)
            initial = path.read_text(encoding="utf-8")
            execute_plan(plan, source_root=ROOT)
            self.assertEqual(path.read_text(encoding="utf-8"), initial)

            path.write_text("# prompt-optimizer:runtime:start\npartial\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                execute_plan(plan, source_root=ROOT)
            self.assertEqual(path.read_text(encoding="utf-8"), "# prompt-optimizer:runtime:start\npartial\n")

    def test_failed_tui_registration_rolls_back_plugin_and_owner_marker(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tui_config = root / ".opencode/tui.json"
            tui_config.parent.mkdir(parents=True)
            tui_config.write_text('{"plugin":"wrong-shape"}', encoding="utf-8")
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"opencode"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            with self.assertRaises(ValueError):
                execute_plan(plan, source_root=ROOT)
            plugin = root / ".opencode/plugins/prompt-optimizer-tui/prompt-optimizer.tsx"
            owner = plugin.parent / ".prompt-optimizer-owner.json"
            self.assertFalse(plugin.exists())
            self.assertFalse(owner.exists())
            self.assertEqual(json.loads(tui_config.read_text(encoding="utf-8")), {"plugin": "wrong-shape"})

    def test_plan_cursor_gemini_install_executes_all_files_as_one_transaction(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"cursor", "gemini"}), automatic=True),
                catalog.load_catalog(ROOT),
            )
            execute_plan(plan, source_root=ROOT)
            self.assertTrue((root / ".cursor/hooks/prompt-optimizer-state.py").is_file())
            self.assertTrue((root / ".cursor/rules/prompt-optimizer.mdc").is_file())
            self.assertTrue((root / ".gemini/hooks/prompt-preflight.py").is_file())
            self.assertTrue((root / ".prompt-optimizer.json").is_file())

    def test_plan_cursor_install_preserves_unowned_hooks_and_replaces_owned_hook(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            hooks_path = root / ".cursor/hooks.json"
            hooks_path.parent.mkdir(parents=True)
            hooks_path.write_text(
                '{"hooks":{"beforeSubmitPrompt":[{"name":"user-hook","command":"echo user"},{"name":"prompt-optimizer","owner":"universal-prompt-optimizer","command":"old"}]}}',
                encoding="utf-8",
            )
            plan = plan_install(
                InstallRequest(root, "project", frozenset({"cursor"}), automatic=True, python_bin="python-custom"),
                catalog.load_catalog(ROOT),
            )
            execute_plan(plan, source_root=ROOT)
            value = json.loads(hooks_path.read_text(encoding="utf-8"))
            entries = value["hooks"]["beforeSubmitPrompt"]
            self.assertEqual([entry["name"] for entry in entries], ["user-hook", "prompt-optimizer"])
            self.assertIn("python-custom", entries[1]["command"])

    def test_gemini_routes_every_canonical_alias(self):
        import ast
        source = ROOT / 'adapters/gemini-cli/hooks/prompt-preflight.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'exact_profile_for']
        namespace = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)
        registry = json.loads((ROOT / '.agents/skills/prompt-optimizer/references/model-registry.json').read_text(encoding='utf-8'))
        for profile in registry['profiles']:
            for alias in profile['aliases']:
                self.assertEqual(namespace['exact_profile_for'](alias), profile['id'], alias)

    def test_gemini_supported_profiles_render_without_false_fallback(self):
        import subprocess
        import sys
        import os
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / '.prompt-optimizer.json').write_text('{"unsupportedModel":"skip"}', encoding='utf-8')
            for model in ('gpt-6-astra', 'gpt-6-luna', 'gpt-5.6-terra', 'glm-5.3', 'kimi-k3', 'gemini-4-argon'):
                env = dict(os.environ, GEMINI_MODEL=model)
                run = subprocess.run([sys.executable, '-B', str(ROOT / 'adapters/gemini-cli/hooks/prompt-preflight.py')], input=json.dumps({'cwd': str(root), 'hook_event_name': 'BeforeAgent'}), text=True, capture_output=True, env=env, check=True)
                context = json.loads(run.stdout)['hookSpecificOutput']['additionalContext']
                self.assertIn('Resolved model profile:', context)
                self.assertNotIn('No exact installed model profile', context)

    def test_global_gemini_hook_uses_home_script_not_project_script(self):
        plan = plan_install(InstallRequest(Path('/example/home'), 'global', frozenset({'gemini'}), automatic=True), catalog.load_catalog(ROOT))
        hook = next(json.loads(op.content)['hook'] for op in plan.operations if op.kind == 'merge_hook')
        command = hook['hooks'][0]['command']
        self.assertIn('expanduser', command)
        self.assertNotIn('GEMINI_PROJECT_DIR', command)

    def test_hook_command_quotes_windows_executable_and_code(self):
        from installer.planning import shell_command
        command = shell_command(['C:/Program Files/Python/python.exe', '-c', 'print("ok")'], platform='nt')
        self.assertTrue(command.startswith('"C:/Program Files/Python/python.exe"'))
        self.assertNotIn("'C:/Program Files", command)

    def test_executor_rolls_back_all_files_when_later_operation_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            existing = root / "existing.txt"
            existing.write_text("before", encoding="utf-8")
            plan = InstallPlan(
                (
                    plan_config_write(existing, {"value": 1}),
                    plan_config_write(root / "new.txt", {"value": 2}),
                    plan_config_write(root / "bad", {"value": 3}),
                )
            )
            (root / "bad").mkdir()
            with self.assertRaises(ValueError):
                execute_plan(plan, source_root=root)
            self.assertEqual(existing.read_text(encoding="utf-8"), "before")
            self.assertFalse((root / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
