import tempfile
import unittest
from pathlib import Path

from evals.cases_loader import load_cases, select_cases


class CasesLoaderTests(unittest.TestCase):
    def test_load_and_select_cases(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text('{"id":"one"}\n{"id":"two"}\n', encoding="utf-8")
            cases = load_cases(path)
        self.assertEqual([case["id"] for case in select_cases(cases, ["two"])], ["two"])

    def test_select_rejects_unknown_ids(self):
        with self.assertRaisesRegex(ValueError, "unknown case"):
            select_cases([{"id": "one"}], ["missing"])


if __name__ == "__main__":
    unittest.main()
