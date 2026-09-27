import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenCodePluginMetadataTests(unittest.TestCase):
    def test_server_and_tui_ids_are_stable_and_not_version_locked(self):
        server = (ROOT / "adapters/opencode/plugin/index.ts").read_text(encoding="utf-8")
        tui = (ROOT / "adapters/opencode/tui/prompt-optimizer.tsx").read_text(encoding="utf-8")
        self.assertIn('id: "prompt-optimizer", server', server)
        self.assertIn('id: "prompt-optimizer.tui",', tui)
        self.assertNotIn('id: "prompt-optimizer-v5-5", server', server)
        self.assertNotIn('id: "prompt-optimizer-v5-5.tui",', tui)

    def test_opencode_config_is_valid_json(self):
        config = json.loads((ROOT / "adapters/opencode/prompt-optimizer.auto.json").read_text(encoding="utf-8"))
        self.assertEqual(config["schemaVersion"], 1)
