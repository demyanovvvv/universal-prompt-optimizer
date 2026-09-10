import unittest

from evals.run import run


class EvaluationFixtureTests(unittest.TestCase):
    def test_static_evaluation_matrix(self):
        result = run()
        self.assertTrue(result["passed"], result["errors"])
        self.assertGreaterEqual(result["cases"], 20)


if __name__ == "__main__":
    unittest.main()
