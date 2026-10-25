import json
import unittest
from pathlib import Path

from adapter_conformance import check

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "adapters" / "capability-matrix.json"


class AdapterConformanceTests(unittest.TestCase):
    def test_capability_matrix_is_aligned(self):
        self.assertEqual(check(), [])

    def test_matrix_lists_every_shipped_adapter_once(self):
        data = json.loads(MATRIX.read_text(encoding="utf-8"))
        ids = [item["id"] for item in data["adapters"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("opencode", ids)
        self.assertIn("pi", ids)
        self.assertIn("omp", ids)

    def test_adapter_manifest_is_explicit_and_complete(self):
        manifest = json.loads((ROOT / "adapters" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(set(manifest["adapters"]), {"opencode", "codex", "cursor", "pi", "omp", "claude", "gemini", "copilot", "windsurf"})

    def test_opencode_and_pi_claim_exact_routing(self):
        data = json.loads(MATRIX.read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in data["adapters"]}
        self.assertTrue(by_id["opencode"]["exactModelRouting"])
        self.assertEqual(by_id["opencode"]["firstTurnRouting"], "exact")
        self.assertTrue(by_id["pi"]["exactModelRouting"])
        self.assertEqual(by_id["pi"]["firstTurnRouting"], "exact")
        self.assertTrue(by_id["omp"]["exactModelRouting"])
        self.assertEqual(by_id["omp"]["firstTurnRouting"], "exact")


if __name__ == "__main__":
    unittest.main()
