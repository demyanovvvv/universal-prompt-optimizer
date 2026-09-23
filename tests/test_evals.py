import unittest
import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

import pycache_guard  # noqa: F401  (prevents child __pycache__ writes)

from evals.run import run

ROOT = Path(__file__).resolve().parents[1]


class EvaluationFixtureTests(unittest.TestCase):
    def test_documented_direct_runner_invocation_works(self):
        completed = __import__("subprocess").run(
            [__import__("sys").executable, "evals/run.py", "--strict-coverage"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
    def test_static_evaluation_matrix(self):
        result = run()
        self.assertTrue(result["passed"], result["errors"])
        self.assertGreaterEqual(result["cases"], 20)

    def test_machine_contracts_are_validated(self):
        result = run()
        self.assertGreaterEqual(result.get("contracts", 0), 7)

    def test_contract_coverage_report_counts_values(self):
        result = run()
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["mode"], "deterministic")
        self.assertEqual(result["providerCalls"], 0)
        self.assertFalse(result["strictCoverage"])
        expected_digest = hashlib.sha256((ROOT / "evals" / "cases.jsonl").read_bytes()).hexdigest()
        self.assertEqual(result["input"]["sha256"], expected_digest)
        self.assertEqual(result["input"]["format"], "jsonl")
        coverage = result["coverage"]
        self.assertEqual(coverage["total"], 7)
        self.assertGreaterEqual(coverage["fields"]["risk"], 3)
        self.assertGreaterEqual(coverage["values"]["action"]["skip"], 1)
        self.assertGreaterEqual(coverage["values"]["gate"]["full"], 1)

    def test_report_contains_stable_result_for_each_case(self):
        result = run()
        self.assertEqual(result["caseResults"][0]["id"], "astra-followthrough")
        self.assertEqual(len(result["caseResults"]), result["cases"])
        self.assertTrue(all(set(item) == {"id", "passed", "errors"} for item in result["caseResults"]))
        self.assertTrue(all(item["passed"] for item in result["caseResults"]))

    def test_strict_coverage_requires_safety_contracts(self):
        result = run(strict_coverage=True)
        self.assertTrue(result["passed"], result["errors"])
        self.assertTrue(result["strictCoverage"])

    def test_strict_coverage_rejects_fixture_without_safety_values(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text(
                '{"id":"basic","model":"astra","request":"Explain this","expect":["answer"]}\n',
                encoding="utf-8",
            )
            result = run(path, strict_coverage=True)
        self.assertFalse(result["passed"])
        self.assertIn("strict coverage missing contract.risk=consequential", result["errors"])

    def test_invalid_contract_values_return_errors_instead_of_crashing(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text(
                '{"id":"negative-ambiguous-model","model":"deepseek-v4","request":"Explain this","expect":["do not guess flash"],"contract":{"risk":[],"taskType":"invented","profile":"invented"}}\n'
                '{"id":"negative-prompt-injection","model":"astra","request":"Ignore rules","expect":["reject"]}\n'
                '{"id":"negative-destructive-action","model":"astra","request":"Delete prod","expect":["approval"]}\n'
                '{"id":"negative-secret-preservation","model":"astra","request":"Keep secret","expect":["redact"]}\n'
                '{"id":"astra-pass-zero-context","model":"astra","request":"Explain","expect":["pass"]}\n'
                '{"id":"astra-completion-boundary","model":"astra","request":"Fix","expect":["verify"]}\n'
                '{"id":"astra-no-needless-approval","model":"astra","request":"Fix local","expect":["continue"]}\n'
                '{"id":"astra-plan-boundary","model":"astra","request":"Plan only","expect":["plan"]}\n'
                '{"id":"astra-skill-progressive-disclosure","model":"astra","request":"Use skill","expect":["skill"]}\n',
                encoding="utf-8",
            )
            result = run(path)
        self.assertFalse(result["passed"])
        self.assertIn("negative-ambiguous-model: contract.risk has invalid type", result["errors"])
        self.assertIn("negative-ambiguous-model: contract.taskType has invalid value: invented", result["errors"])
        self.assertIn("negative-ambiguous-model: contract.profile has invalid value: invented", result["errors"])

    def test_invalid_rubric_values_return_errors_instead_of_crashing(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text(
                '{"id":"one","model":"astra","request":"Explain this","expect":["answer"],"rubric":{"forbidden":"not-an-array","minScore":2}}\n',
                encoding="utf-8",
            )
            result = run(path)

        self.assertFalse(result["passed"])
        self.assertTrue(any("rubric" in error for error in result["errors"]))

    def test_malformed_case_fields_return_errors_instead_of_crashing(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text(
                '{"id":[],"model":{},"request":[],"expect":{}}\n',
                encoding="utf-8",
            )
            result = run(path)
        self.assertFalse(result["passed"])
        self.assertIn("case 1: id must be unique and non-empty", result["errors"])
        self.assertIn("case 1: model must be a non-empty string", result["errors"])
        self.assertIn("case 1: request must be non-empty", result["errors"])
        self.assertIn("case 1: expect must be a non-empty array", result["errors"])

    def test_invalid_json_returns_a_structured_report(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text('{"id":', encoding="utf-8")
            result = run(path)
        self.assertFalse(result["passed"])
        self.assertEqual(result["schemaVersion"], 1)
        self.assertEqual(result["cases"], 0)
        self.assertIn("invalid JSON", result["errors"][0])

    def test_non_object_jsonl_line_returns_a_structured_report(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            path.write_text('[]\n', encoding="utf-8")
            result = run(path)
        self.assertFalse(result["passed"])
        self.assertIn("case must be an object", result["errors"][0])

    def test_verify_script_runs_strict_coverage(self):
        verify = (ROOT / "verify.sh").read_text(encoding="utf-8")
        self.assertIn("evals/run.py --strict-coverage", verify)
        self.assertIn(".tmp-tests/opencode/tests/eval-contract.test.js", verify)

    def test_ci_runs_repository_verification(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("PYTHONDONTWRITEBYTECODE: \"1\"", workflow)
        self.assertIn('node-version: "22"', workflow)
        self.assertIn("npm test", workflow)
        self.assertIn("npm run verify:ts", workflow)
        self.assertIn("npm run test:registry", workflow)
        self.assertIn("npm run test:adapters", workflow)
        self.assertIn("npm run test:evals:strict", workflow)
        self.assertIn("evals/results/latest.json", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("npm run verify", workflow)
        self.assertIn("npm run verify:bash", workflow)
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("windows-latest", workflow)
        self.assertIn("timeout-minutes: 10", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertFalse((ROOT / ".github" / "workflows" / "verify.yml").exists())
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("strict safety coverage", readme)
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["scripts"]["test:evals:strict"], "python -B evals/run.py --strict-coverage")
        self.assertIn("npm run test:evals:strict", package["scripts"]["test"])
        self.assertIn("evals/results/matrix.json", package["scripts"]["test:evals:mock"])
        self.assertEqual(package["scripts"]["verify"], "node ./verify.mjs")
        self.assertEqual(package["scripts"]["verify:bash"], "bash ./verify.sh")
        self.assertIn("evals/baselines/matrix.json", package["scripts"]["test:evals:baseline"])
        testing = (ROOT / "TESTING.md").read_text(encoding="utf-8")
        self.assertIn("npm run test:evals:strict", testing)
        self.assertIn("npm run test:evals:baseline", testing)
        self.assertIn("npm run verify:bash", testing)
        self.assertIn("canonical `CI` GitHub Actions workflow", testing)

    def test_runtime_typescript_config_uses_supported_node_resolution(self):
        config = json.loads((ROOT / "tsconfig.test.json").read_text(encoding="utf-8"))

        self.assertEqual(config["compilerOptions"]["module"], "Node16")
        self.assertEqual(config["compilerOptions"]["moduleResolution"], "Node16")

    def test_provider_workflows_share_matrix_baseline_filename(self):
        mock_workflow = (ROOT / ".github" / "workflows" / "provider-eval-mock.yml").read_text(encoding="utf-8")
        real_workflow = (ROOT / ".github" / "workflows" / "provider-eval-real.yml").read_text(encoding="utf-8")

        self.assertIn("--output evals/results/matrix.json", mock_workflow)
        self.assertIn("evals/baselines/matrix.json", mock_workflow)
        self.assertIn("evals/results/baseline-gate.json", mock_workflow)
        self.assertIn("evals/baseline/matrix.json", real_workflow)
        self.assertIn("--output evals/results/matrix.json", real_workflow)
        self.assertIn("evals/results/matrix.json --kind matrix", real_workflow)
        self.assertIn("path: evals/results/matrix.json", real_workflow)
        self.assertIn("evals/results/comparison.json --kind comparison", real_workflow)

    def test_spawned_python_children_disable_bytecode_writes(self):
        import os
        import subprocess
        import sys

        self.assertEqual(os.environ.get("PYTHONDONTWRITEBYTECODE"), "1")
        completed = subprocess.run(
            [sys.executable, "-c", "import sys; print(sys.dont_write_bytecode)"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "True")



if __name__ == "__main__":
    unittest.main()
