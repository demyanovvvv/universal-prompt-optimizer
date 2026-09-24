import sys
import unittest

from evals.provider_protocol import call_cli_provider
from evals.case_runner import validate_cases


class ProviderProtocolTests(unittest.TestCase):
    def test_cli_protocol_round_trip(self):
        result = call_cli_provider(
            [sys.executable, "-c", "import json,sys; print(json.dumps(json.load(sys.stdin)))"],
            {"id": "fixture", "value": 2},
            timeout=5,
            max_output_bytes=1024,
        )
        self.assertEqual(result, {"id": "fixture", "value": 2})

    def test_cli_protocol_enforces_output_limit(self):
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            call_cli_provider([sys.executable, "-c", "print('x' * 50)"], {}, timeout=5, max_output_bytes=10)

    def test_case_validation_rejects_duplicate_ids_and_invalid_contracts(self):
        with self.assertRaisesRegex(ValueError, "duplicate case id"):
            validate_cases([
                {"id": "one", "model": "m", "request": "r"},
                {"id": "one", "model": "m", "request": "r"},
            ], lambda _rubric, _index: None)
        with self.assertRaisesRegex(ValueError, "request"):
            validate_cases([{"id": "one", "model": "m", "request": " "}], lambda _rubric, _index: None)


if __name__ == "__main__":
    unittest.main()
