import unittest

from evals.run import run


class EvaluationFixtureTests(unittest.TestCase):
    def test_static_evaluation_matrix(self):
        result = run()
        self.assertTrue(result["passed"], result["errors"])
        self.assertGreaterEqual(result["cases"], 20)

    def test_machine_contracts_are_validated(self):
        result = run()
        self.assertGreaterEqual(result.get("contracts", 0), 7)


if __name__ == "__main__":
    unittest.main()
