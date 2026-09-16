import unittest
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from evals.quality import compare_reports, score_response
from evals.report_schema import validate_report
from evals.redaction import redact_sensitive


class ReportContractTests(unittest.TestCase):
    def test_redaction_removes_common_secret_formats_recursively(self):
        value = {"text": "Bearer abcdefghijklmnop", "nested": ["api_key=sk-test-1234567890"]}

        redacted = redact_sensitive(value)

        self.assertNotIn("abcdefghijklmnop", json.dumps(redacted))
        self.assertNotIn("sk-test-1234567890", json.dumps(redacted))
        self.assertEqual(redacted["nested"][0], "api_key=[REDACTED]")

    def test_redaction_removes_values_for_sensitive_keys(self):
        redacted = redact_sensitive({"api_key": "plain-secret", "authorization": "plain-token"})

        self.assertEqual(redacted, {"api_key": "[REDACTED]", "authorization": "[REDACTED]"})
    def test_saved_deterministic_report_passes_cli_validation(self):
        with TemporaryDirectory() as raw:
            report_path = Path(raw) / "report.json"
            subprocess.run(
                [sys.executable, "-m", "evals.run", "--strict-coverage", "--output", str(report_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            completed = subprocess.run(
                [sys.executable, "-m", "evals.validate_report", str(report_path), "--kind", "deterministic"],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["passed"])

    def test_provider_cli_matrix_with_mock_executable_is_schema_valid(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            cases = directory / "cases.jsonl"
            report_path = directory / "matrix.json"
            cases.write_text(
                '{"id":"one","model":"astra","request":"hello","expect":["Выполнить first/default"]}\n',
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evals.provider",
                    "--cases",
                    str(cases),
                    "--mode",
                    "MATRIX",
                    "--approve",
                    "--output",
                    str(report_path),
                    "--provider",
                    sys.executable,
                    str(root / "tests" / "provider_mock.py"),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            validation = subprocess.run(
                [sys.executable, "-m", "evals.validate_report", str(report_path), "--kind", "matrix"],
                check=False,
                capture_output=True,
                text=True,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertEqual(report["providerCalls"], 3)
        self.assertTrue(report["passed"])
        self.assertTrue(report["caseResults"][0]["results"]["AUTO"]["quality"]["passed"])
    def test_provider_report_contract_accepts_measured_quality_result(self):
        report = {
            "schemaVersion": 1,
            "mode": "AUTO",
            "providerCalls": 1,
            "failures": 0,
            "caseResults": [{
                "id": "one",
                "status": "measured",
                "response": {"text": "done"},
                "durationMs": 3,
                "quality": {"expected": 1, "matched": 1, "passed": True, "missing": []},
            }],
            "summary": {"cases": 1, "measured": 1, "approvalRequired": 0, "failed": 0},
            "passed": True,
        }

        self.assertEqual(validate_report(report, "provider"), [])

    def test_report_contract_rejects_unknown_status_and_missing_required_fields(self):
        errors = validate_report({"schemaVersion": 1, "mode": "AUTO", "caseResults": [{"id": "one", "status": "unknown"}]}, "provider")

        self.assertTrue(any("providerCalls" in error for error in errors))
        self.assertTrue(any("status" in error for error in errors))

    def test_report_contract_rejects_invalid_quality_score(self):
        errors = validate_report({
            "schemaVersion": 1,
            "mode": "AUTO",
            "providerCalls": 1,
            "failures": 0,
            "caseResults": [{
                "id": "one",
                "status": "measured",
                "quality": {"expected": 1, "matched": 2, "passed": True, "missing": [], "score": 2.0},
            }],
            "summary": {"cases": 1, "measured": 1, "approvalRequired": 0, "failed": 0},
            "passed": True,
        }, "provider")

        self.assertTrue(any("score" in error for error in errors))

    def test_report_contract_rejects_quality_match_count_above_expected(self):
        errors = validate_report({
            "schemaVersion": 1,
            "mode": "AUTO",
            "providerCalls": 1,
            "failures": 0,
            "caseResults": [{
                "id": "one",
                "status": "measured",
                "quality": {"expected": 1, "matched": 2, "passed": True, "missing": []},
            }],
            "summary": {"cases": 1, "measured": 1, "approvalRequired": 0, "failed": 0},
            "passed": True,
        }, "provider")

        self.assertTrue(any("matched cannot exceed expected" in error for error in errors))

    def test_report_contract_rejects_invalid_metrics_and_latency(self):
        errors = validate_report({
            "schemaVersion": 1,
            "mode": "AUTO",
            "providerCalls": 1,
            "failures": 0,
            "caseResults": [{"id": "one", "status": "measured"}],
            "summary": {"cases": 1, "measured": 1, "approvalRequired": 0, "failed": 0},
            "metrics": {"available": ["cost", "unknown"], "total": {"cost": -1, "unknown": 2}},
            "latency": {"measured": 1, "p50Ms": 10, "p95Ms": 2},
            "passed": True,
        }, "provider")

        self.assertTrue(any("metrics.total.cost" in error for error in errors))
        self.assertTrue(any("metrics.total.unknown" in error for error in errors))
        self.assertTrue(any("p95Ms cannot be less" in error for error in errors))

    def test_report_contract_rejects_invalid_trace_event(self):
        errors = validate_report({
            "schemaVersion": 1,
            "mode": "AUTO",
            "providerCalls": 1,
            "failures": 0,
            "caseResults": [{"id": "one", "status": "measured", "trace": [{"event": ""}]}],
            "summary": {"cases": 1, "measured": 1, "approvalRequired": 0, "failed": 0},
            "passed": True,
        }, "provider")

        self.assertTrue(any("trace[0].event" in error for error in errors))

    def test_schema_files_are_valid_json_and_cover_all_report_kinds(self):
        schema_dir = Path(__file__).resolve().parents[1] / "evals" / "schemas"
        names = {path.name for path in schema_dir.glob("*.schema.json")}

        self.assertEqual(names, {
            "comparison-report.schema.json",
            "deterministic-report.schema.json",
            "matrix-report.schema.json",
            "provider-report.schema.json",
            "quality-score.schema.json",
        })
        for path in schema_dir.glob("*.schema.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(value["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(value["type"], "object")

    def test_quality_rubric_checks_forbidden_phrases_and_minimum_score(self):
        score = score_response(
            {"text": "Implemented the fix, but also performed an unrelated migration."},
            ["fix", "verification"],
            rubric={"forbidden": ["unrelated migration"], "minScore": 0.75},
        )

        self.assertEqual(score["matched"], 1)
        self.assertEqual(score["forbidden"], ["unrelated migration"])
        self.assertEqual(score["score"], 0.5)
        self.assertFalse(score["passed"])

    def test_compare_reports_detects_reliability_latency_and_cost_regressions(self):
        baseline = {
            "caseResults": [{"id": "one", "quality": {"passed": True, "score": 1.0}, "status": "measured", "durationMs": 100, "metrics": {"cost": 1.0}}],
            "summary": {"cases": 1, "measured": 1, "approvalRequired": 0, "failed": 0},
            "passed": True,
        }
        candidate = {
            "caseResults": [{"id": "one", "quality": {"passed": True, "score": 1.0}, "status": "failed", "durationMs": 250, "error": "timeout", "metrics": {"cost": 1.5}}],
            "summary": {"cases": 1, "measured": 0, "approvalRequired": 0, "failed": 1},
            "passed": False,
        }

        comparison = compare_reports(
            baseline,
            candidate,
            max_latency_increase=0.5,
            max_cost_increase=0.2,
        )

        self.assertFalse(comparison["passed"])
        self.assertIn("one", comparison["reliabilityRegressions"])
        self.assertIn("one", comparison["latencyRegressions"])
        self.assertIn("one", comparison["costRegressions"])

    def test_compare_reports_reports_added_and_removed_cases_as_warnings(self):
        baseline = {
            "caseResults": [{"id": "one", "quality": {"passed": True}}],
        }
        candidate = {
            "caseResults": [{"id": "two", "quality": {"passed": True}}],
        }

        comparison = compare_reports(baseline, candidate)

        self.assertFalse(comparison["passed"])
        self.assertEqual(comparison["addedCases"], ["two"])
        self.assertEqual(comparison["removedCases"], ["one"])
        self.assertTrue(comparison["warnings"])

    def test_compare_reports_blocks_changed_fixture_digest_by_default(self):
        baseline = {"input": {"sha256": "a"}, "caseResults": [{"id": "one", "quality": {"passed": True}}]}
        candidate = {"input": {"sha256": "b"}, "caseResults": [{"id": "one", "quality": {"passed": True}}]}

        comparison = compare_reports(baseline, candidate)

        self.assertFalse(comparison["passed"])
        self.assertIn("fixture digest", comparison["errors"][0])

    def test_compare_reports_can_compare_matrix_results_for_selected_mode(self):
        baseline = {
            "mode": "matrix",
            "caseResults": [{"id": "one", "results": {"AUTO": {"quality": {"passed": True}}}}],
        }
        candidate = {
            "mode": "matrix",
            "caseResults": [{"id": "one", "results": {"AUTO": {"quality": {"passed": False}}}}],
        }

        comparison = compare_reports(baseline, candidate, run_mode="AUTO")

        self.assertFalse(comparison["passed"])
        self.assertEqual(comparison["regressions"], ["one"])

    def test_compare_cli_returns_failure_for_quality_regression_and_writes_report(self):
        root = Path(__file__).resolve().parents[1]
        baseline = {
            "caseResults": [{"id": "one", "quality": {"passed": True}}],
        }
        candidate = {
            "caseResults": [{"id": "one", "quality": {"passed": False}}],
        }
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            output_path = directory / "comparison.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evals.compare",
                    str(baseline_path),
                    str(candidate_path),
                    "--output",
                    str(output_path),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            comparison = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(comparison["schemaVersion"], 1)
        self.assertFalse(comparison["passed"])
        self.assertEqual(comparison["regressions"], ["one"])

    def test_compare_reports_requires_mode_for_matrix_reports(self):
        report = {"mode": "matrix", "caseResults": [{"id": "one", "results": {"AUTO": {"quality": {"passed": True}}}}]}

        with self.assertRaisesRegex(ValueError, "run_mode"):
            compare_reports(report, report)
