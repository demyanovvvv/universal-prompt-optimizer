import unittest
import sys
import hashlib
import json
import subprocess
import time
from tempfile import TemporaryDirectory
from pathlib import Path

from evals.provider import cli_provider, run_provider_cases, run_provider_matrix
from evals.quality import compare_reports, score_exact_match, score_response


class ProviderHarnessTests(unittest.TestCase):
    def test_exact_scorer_reports_match(self):
        self.assertEqual(score_exact_match({"ok": True}, {"ok": True}), {"passed": True, "matched": True})
        self.assertEqual(score_exact_match({"ok": True}, {"ok": False}), {"passed": False, "matched": False})

    def test_score_response_checks_expected_phrases_case_insensitively(self):
        score = score_response({"text": "Implemented the fix and ran focused verification."}, ["fix", "verification"])

        self.assertEqual(score, {"expected": 2, "matched": 2, "passed": True, "missing": []})

    def test_score_response_reports_missing_phrases(self):
        score = score_response("Implemented the fix.", ["fix", "verification"])

        self.assertEqual(score["expected"], 2)
        self.assertEqual(score["matched"], 1)
        self.assertFalse(score["passed"])
        self.assertEqual(score["missing"], ["verification"])

    def test_provider_report_fails_when_expected_phrase_is_missing(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello", "expect": ["required phrase"]}],
            mode="AUTO",
            provider=lambda payload: {"text": "different response"},
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["failures"], 0)
        self.assertFalse(report["caseResults"][0]["quality"]["passed"])

    def test_provider_forwards_only_supported_rubric_fields(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"text": "fix verification"}

        run_provider_cases(
            [{
                "id": "one",
                "model": "astra",
                "request": "hello",
                "expect": ["fix"],
                "rubric": {"forbidden": ["unrelated"], "minScore": 1.0},
                "secretMetadata": "must not be forwarded",
            }],
            mode="AUTO",
            provider=provider,
        )

        self.assertEqual(calls[0]["rubric"], {"forbidden": ["unrelated"], "minScore": 1.0})
        self.assertNotIn("secretMetadata", calls[0])

    def test_provider_envelope_preserves_response_and_metrics_without_zero_filling(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello", "expect": ["done"]}],
            mode="AUTO",
            provider=lambda payload: {
                "response": {"text": "done"},
                "metrics": {"inputTokens": 4, "outputTokens": 2, "cost": 0.01},
            },
        )

        result = report["caseResults"][0]
        self.assertEqual(result["response"], {"text": "done"})
        self.assertEqual(result["metrics"]["inputTokens"], 4)
        self.assertNotIn("reasoningTokens", result["metrics"])
        self.assertEqual(report["metrics"]["available"], ["cost", "inputTokens", "outputTokens"])
        self.assertEqual(report["metrics"]["total"]["inputTokens"], 4)

    def test_provider_envelope_preserves_bounded_redacted_trace(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {
                "response": {"text": "done"},
                "trace": [{"event": "request", "durationMs": 2, "detail": "Bearer trace-secret"}],
            },
        )

        self.assertEqual(report["caseResults"][0]["trace"][0]["event"], "request")
        self.assertEqual(report["caseResults"][0]["trace"][0]["detail"], "Bearer [REDACTED]")
        self.assertEqual(report["trace"]["events"], 1)

    def test_provider_rejects_malformed_trace_as_case_failure(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {"response": {"ok": True}, "trace": [{"event": ""}]},
        )

        self.assertFalse(report["passed"])
        self.assertIn("trace[0].event", report["caseResults"][0]["error"])

    def test_provider_redacts_secret_like_response_strings(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {"text": "Bearer secret-token-123456"},
        )

        self.assertEqual(report["caseResults"][0]["response"]["text"], "Bearer [REDACTED]")

    def test_provider_report_exposes_quality_aggregate(self):
        report = run_provider_cases(
            [
                {"id": "good", "model": "astra", "request": "hello", "expect": ["done"]},
                {"id": "bad", "model": "astra", "request": "hello", "expect": ["missing"]},
            ],
            mode="AUTO",
            provider=lambda payload: {"text": "done"},
        )

        self.assertEqual(report["quality"], {"cases": 2, "scored": 2, "passed": 1, "passRate": 0.5})

    def test_rubric_can_require_fields_and_exact_response(self):
        report = run_provider_cases(
            [{
                "id": "one",
                "model": "astra",
                "request": "hello",
                "expect": ["done"],
                "rubric": {"requiredFields": ["text"], "exact": {"text": "done"}},
            }],
            mode="AUTO",
            provider=lambda payload: {"text": "done"},
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["caseResults"][0]["quality"]["fields"]["passed"])
        self.assertTrue(report["caseResults"][0]["quality"]["exact"]["passed"])

    def test_provider_report_exposes_latency_percentiles(self):
        report = run_provider_cases(
            [
                {"id": "one", "model": "astra", "request": "hello"},
                {"id": "two", "model": "astra", "request": "hello"},
            ],
            mode="AUTO",
            provider=lambda payload: {"ok": True},
        )

        self.assertEqual(report["latency"]["measured"], 2)
        self.assertGreaterEqual(report["latency"]["p50Ms"], 0)
        self.assertGreaterEqual(report["latency"]["p95Ms"], report["latency"]["p50Ms"])

    def test_matrix_report_exposes_per_mode_quality_and_metrics(self):
        report = run_provider_matrix(
            [{"id": "one", "model": "astra", "request": "hello", "expect": ["done"]}],
            provider=lambda payload: {"response": {"text": "done"}, "metrics": {"cost": 0.1}},
            approve_preview=True,
        )

        self.assertEqual(report["quality"]["AUTO"]["passRate"], 1.0)
        self.assertEqual(report["metrics"]["OFF"]["total"]["cost"], 0.1)

    def test_provider_rejects_invalid_metrics_as_case_failure(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {"response": {"ok": True}, "metrics": {"cost": -1}},
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["caseResults"][0]["status"], "failed")
        self.assertIn("metrics.cost", report["caseResults"][0]["error"])

    def test_invalid_rubric_is_rejected_before_provider_calls(self):
        calls = []

        with self.assertRaisesRegex(ValueError, "requiredFields"):
            run_provider_cases(
                [{
                    "id": "one",
                    "model": "astra",
                    "request": "hello",
                    "expect": ["done"],
                    "rubric": {"requiredFields": "text"},
                }],
                mode="AUTO",
                provider=lambda payload: calls.append(payload),
            )

        self.assertEqual(calls, [])

    def test_provider_rejects_non_finite_metrics_as_case_failure(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {"response": {"ok": True}, "metrics": {"cost": float("nan")}},
        )

        self.assertFalse(report["passed"])
        self.assertIn("finite", report["caseResults"][0]["error"])

    def test_compare_reports_detects_quality_regression_by_case_id(self):
        baseline = {
            "caseResults": [
                {"id": "one", "quality": {"passed": True}},
                {"id": "two", "quality": {"passed": True}},
            ]
        }
        candidate = {
            "caseResults": [
                {"id": "one", "quality": {"passed": True}},
                {"id": "two", "quality": {"passed": False}},
            ]
        }

        comparison = compare_reports(baseline, candidate)

        self.assertFalse(comparison["passed"])
        self.assertEqual(comparison["regressions"], ["two"])
        self.assertEqual(comparison["baselineQualityPassRate"], 1.0)
        self.assertEqual(comparison["candidateQualityPassRate"], 0.5)

    def test_compare_reports_applies_minimum_candidate_quality_threshold(self):
        report = {"caseResults": [{"id": "one", "quality": {"passed": True}}, {"id": "two", "quality": {"passed": False}}]}

        comparison = compare_reports(report, report, min_candidate_rate=1.0)

        self.assertFalse(comparison["passed"])
        self.assertEqual(comparison["regressions"], [])
        self.assertIn("minimum quality pass rate", comparison["errors"][0])

    def test_compare_reports_rejects_duplicate_case_ids(self):
        report = {
            "caseResults": [
                {"id": "one", "quality": {"passed": True}},
                {"id": "one", "quality": {"passed": True}},
            ]
        }

        with self.assertRaisesRegex(ValueError, "duplicate case result id"):
            compare_reports(report, report)

    def test_cli_provider_sends_json_and_reads_json(self):
        script = Path(__file__).with_name("provider_echo.py")
        payload = {"id": "one", "model": "astra", "request": "hello", "mode": "OFF"}

        response = cli_provider([sys.executable, str(script)], payload)

        self.assertEqual(response["received"], payload)

    def test_cli_provider_reports_invalid_json(self):
        script = Path(__file__).with_name("provider_invalid.py")

        with self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            cli_provider([sys.executable, str(script)], {"id": "one"})

    def test_cli_provider_rejects_oversized_raw_stdout(self):
        script = Path(__file__).with_name("provider_large.py")

        with self.assertRaisesRegex(RuntimeError, "stdout exceeds 32 bytes"):
            cli_provider(
                [sys.executable, str(script)],
                {"id": "one"},
                max_output_bytes=32,
            )

    def test_off_forwards_original_request_to_provider(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"text": "answer"}

        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "Keep this exact request"}],
            mode="OFF",
            provider=provider,
        )

        self.assertEqual(calls[0]["request"], "Keep this exact request")
        self.assertEqual(calls[0]["mode"], "OFF")
        self.assertEqual(report["providerCalls"], 1)
        self.assertTrue(report["passed"])
        self.assertEqual(report["caseResults"][0]["status"], "measured")

    def test_preview_never_calls_provider_without_approval(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"text": "answer"}

        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "Do not execute"}],
            mode="PREVIEW",
            provider=provider,
        )

        self.assertEqual(calls, [])
        self.assertEqual(report["providerCalls"], 0)
        self.assertEqual(report["caseResults"][0]["status"], "approval_required")
        self.assertTrue(report["passed"])

    def test_preview_calls_provider_once_after_approval(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"text": "answer"}

        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "Approved request"}],
            mode="PREVIEW",
            provider=provider,
            approve=True,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["mode"], "PREVIEW")
        self.assertEqual(report["caseResults"][0]["status"], "measured")

    def test_auto_calls_provider_without_approval_prompt(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"text": "answer"}

        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "Run automatically"}],
            mode="AUTO",
            provider=provider,
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(report["caseResults"][0]["status"], "measured")

    def test_invalid_mode_is_rejected_before_provider_calls(self):
        with self.assertRaises(ValueError):
            run_provider_cases([], mode="sometimes", provider=lambda payload: {})

    def test_provider_failure_is_scoped_to_case_and_later_cases_run(self):
        calls = []

        def provider(payload):
            calls.append(payload["id"])
            if payload["id"] == "bad":
                raise RuntimeError("provider unavailable")
            return {"text": "answer"}

        report = run_provider_cases(
            [
                {"id": "bad", "model": "astra", "request": "first"},
                {"id": "good", "model": "astra", "request": "second"},
            ],
            mode="AUTO",
            provider=provider,
        )

        self.assertEqual(calls, ["bad", "good"])
        self.assertEqual(report["providerCalls"], 2)
        self.assertEqual(report["caseResults"][0]["status"], "failed")
        self.assertIn("provider unavailable", report["caseResults"][0]["error"])
        self.assertEqual(report["caseResults"][1]["status"], "measured")
        self.assertFalse(report["passed"])

    def test_report_includes_input_digest_without_provider_command(self):
        with TemporaryDirectory() as raw:
            path = Path(raw) / "cases.jsonl"
            content = '{"id":"one","model":"astra","request":"hello"}\n'
            path.write_text(content, encoding="utf-8")
            report = run_provider_cases(
                [json.loads(line) for line in content.splitlines() if line],
                mode="OFF",
                provider=lambda payload: {"ok": True},
                input_path=path,
            )
            expected_digest = hashlib.sha256(path.read_bytes()).hexdigest()

        self.assertEqual(report["input"]["format"], "jsonl")
        self.assertEqual(report["input"]["sha256"], expected_digest)
        self.assertNotIn("providerCommand", report)

    def test_invalid_case_is_rejected_before_provider_calls(self):
        calls = []

        def provider(payload):
            calls.append(payload)
            return {"ok": True}

        with self.assertRaisesRegex(ValueError, "case 1.*request"):
            run_provider_cases(
                [{"id": "one", "model": "astra", "request": ""}],
                mode="OFF",
                provider=provider,
            )

        self.assertEqual(calls, [])

    def test_cli_writes_report_to_output_path(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases.jsonl"
            output = root / "nested" / "report.json"
            cases.write_text(
                '{"id":"one","model":"astra","request":"hello"}\n',
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
                    "PREVIEW",
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["providerCalls"], 0)

    def test_cli_returns_structured_report_for_invalid_json(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "invalid.jsonl"
            output = root / "report.json"
            content = '{"id":"one"\n'
            cases.write_text(content, encoding="utf-8")
            expected_digest = hashlib.sha256(cases.read_bytes()).hexdigest()
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evals.provider",
                    "--cases",
                    str(cases),
                    "--mode",
                    "OFF",
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(report["passed"])
            self.assertEqual(report["providerCalls"], 0)
            self.assertTrue(report["errors"])
            self.assertIn("line 1", report["errors"][0])
            self.assertEqual(report["input"]["sha256"], expected_digest)

    def test_oversized_response_is_a_case_failure(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {"text": "x" * 100},
            max_response_bytes=32,
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["caseResults"][0]["status"], "failed")
        self.assertIn("response exceeds 32 bytes", report["caseResults"][0]["error"])

    def test_non_serializable_response_is_a_case_failure(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: {"value": object()},
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["caseResults"][0]["status"], "failed")
        self.assertIn("JSON-serializable", report["caseResults"][0]["error"])

    def test_non_positive_response_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "max_response_bytes"):
            run_provider_cases(
                [],
                mode="OFF",
                provider=lambda payload: {},
                max_response_bytes=0,
            )

    def test_case_limit_is_checked_before_provider_calls(self):
        calls = []
        cases = [
            {"id": "one", "model": "astra", "request": "one"},
            {"id": "two", "model": "astra", "request": "two"},
        ]

        with self.assertRaisesRegex(ValueError, "max_cases"):
            run_provider_cases(
                cases,
                mode="OFF",
                provider=lambda payload: calls.append(payload),
                max_cases=1,
            )

        self.assertEqual(calls, [])

    def test_cli_reports_case_limit_failure_without_provider_calls(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases.jsonl"
            output = root / "report.json"
            cases.write_text(
                '{"id":"one","model":"astra","request":"one"}\n'
                '{"id":"two","model":"astra","request":"two"}\n',
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
                    "OFF",
                    "--max-cases",
                    "1",
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["providerCalls"], 0)
            self.assertIn("max_cases exceeded", report["errors"][0])

    def test_duplicate_ids_are_rejected_before_provider_calls(self):
        calls = []
        cases = [
            {"id": "same", "model": "astra", "request": "one"},
            {"id": "same", "model": "astra", "request": "two"},
        ]

        with self.assertRaisesRegex(ValueError, "duplicate case id: same"):
            run_provider_cases(
                cases,
                mode="OFF",
                provider=lambda payload: calls.append(payload),
            )

        self.assertEqual(calls, [])

    def test_cli_reports_duplicate_id_failure(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases.jsonl"
            output = root / "report.json"
            cases.write_text(
                '{"id":"same","model":"astra","request":"one"}\n'
                '{"id":"same","model":"astra","request":"two"}\n',
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
                    "OFF",
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["providerCalls"], 0)
            self.assertIn("duplicate case id: same", report["errors"][0])

    def test_report_includes_status_summary(self):
        report = run_provider_cases(
            [
                {"id": "approved", "model": "astra", "request": "one"},
                {"id": "blocked", "model": "astra", "request": "two"},
            ],
            mode="PREVIEW",
            provider=lambda payload: {"ok": True},
            approve=False,
        )

        self.assertEqual(report["summary"], {
            "cases": 2,
            "measured": 0,
            "approvalRequired": 2,
            "failed": 0,
        })

    def test_report_summary_counts_measured_and_failed_cases(self):
        report = run_provider_cases(
            [
                {"id": "bad", "model": "astra", "request": "one"},
                {"id": "good", "model": "astra", "request": "two"},
            ],
            mode="AUTO",
            provider=lambda payload: (_ for _ in ()).throw(RuntimeError("down"))
            if payload["id"] == "bad" else {"ok": True},
        )

        self.assertEqual(report["summary"], {
            "cases": 2,
            "measured": 1,
            "approvalRequired": 0,
            "failed": 1,
        })

    def test_provider_results_include_non_negative_duration(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="AUTO",
            provider=lambda payload: (time.sleep(0.001) or {"ok": True}),
        )

        self.assertIsInstance(report["caseResults"][0]["durationMs"], int)
        self.assertGreaterEqual(report["caseResults"][0]["durationMs"], 0)

    def test_preview_without_approval_has_no_duration(self):
        report = run_provider_cases(
            [{"id": "one", "model": "astra", "request": "hello"}],
            mode="PREVIEW",
            provider=lambda payload: {"ok": True},
        )

        self.assertNotIn("durationMs", report["caseResults"][0])

    def test_matrix_joins_mode_results_by_case_id(self):
        calls = []

        def provider(payload):
            calls.append((payload["id"], payload["mode"]))
            return {"mode": payload["mode"]}

        report = run_provider_matrix(
            [{"id": "one", "model": "astra", "request": "hello"}],
            provider=provider,
        )

        self.assertEqual(calls, [("one", "OFF"), ("one", "AUTO")])
        self.assertEqual(report["modes"], ["OFF", "AUTO", "PREVIEW"])
        self.assertEqual(report["providerCalls"], 2)
        self.assertEqual(report["caseResults"][0]["id"], "one")
        self.assertEqual(report["caseResults"][0]["results"]["OFF"]["status"], "measured")
        self.assertEqual(report["caseResults"][0]["results"]["PREVIEW"]["status"], "approval_required")

    def test_matrix_approved_preview_calls_provider(self):
        calls = []
        report = run_provider_matrix(
            [{"id": "one", "model": "astra", "request": "hello"}],
            provider=lambda payload: calls.append(payload["mode"]) or {"ok": True},
            approve_preview=True,
        )

        self.assertEqual(calls, ["OFF", "AUTO", "PREVIEW"])
        self.assertEqual(report["providerCalls"], 3)

    def test_cli_matrix_writes_joined_report(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases.jsonl"
            output = root / "matrix.json"
            cases.write_text(
                '{"id":"one","model":"astra","request":"hello"}\n',
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
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "matrix")
            self.assertEqual(report["providerCalls"], 2)
            self.assertEqual(report["caseResults"][0]["results"]["PREVIEW"]["status"], "approval_required")

    def test_cli_runs_only_selected_cases(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases.jsonl"
            output = root / "report.json"
            cases.write_text(
                '{"id":"one","model":"astra","request":"one"}\n'
                '{"id":"two","model":"astra","request":"two"}\n',
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
                    "OFF",
                    "--case",
                    "two",
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in report["caseResults"]], ["two"])
            self.assertEqual(report["selection"], {"requested": ["two"], "selected": 1})

    def test_cli_rejects_unknown_selected_case_before_provider_calls(self):
        with TemporaryDirectory() as raw:
            root = Path(raw)
            cases = root / "cases.jsonl"
            output = root / "report.json"
            cases.write_text(
                '{"id":"one","model":"astra","request":"one"}\n',
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
                    "OFF",
                    "--case",
                    "missing",
                    "--output",
                    str(output),
                    "--provider",
                    sys.executable,
                    str(Path(__file__).with_name("provider_echo.py")),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["providerCalls"], 0)
            self.assertIn("unknown case id: missing", report["errors"][0])

    def test_provider_payload_includes_rubric_and_contract_only(self):
        calls = []
        contract = {"profile": "astra", "action": "apply"}
        run_provider_cases(
            [{
                "id": "one",
                "model": "astra",
                "request": "hello",
                "expect": ["preserve literal"],
                "contract": contract,
                "privateNote": "must not leak",
            }],
            mode="AUTO",
            provider=lambda payload: calls.append(payload) or {"ok": True},
        )

        self.assertEqual(calls[0]["expect"], ["preserve literal"])
        self.assertEqual(calls[0]["contract"], contract)
        self.assertNotIn("privateNote", calls[0])

    def test_invalid_optional_rubric_is_rejected_before_provider_calls(self):
        calls = []
        with self.assertRaisesRegex(ValueError, "case 1: expect"):
            run_provider_cases(
                [{
                    "id": "one",
                    "model": "astra",
                    "request": "hello",
                    "expect": [],
                }],
                mode="AUTO",
                provider=lambda payload: calls.append(payload),
            )

        self.assertEqual(calls, [])

    def test_invalid_optional_contract_is_rejected_before_provider_calls(self):
        calls = []
        with self.assertRaisesRegex(ValueError, "case 1: contract"):
            run_provider_cases(
                [{
                    "id": "one",
                    "model": "astra",
                    "request": "hello",
                    "contract": [],
                }],
                mode="AUTO",
                provider=lambda payload: calls.append(payload),
            )

        self.assertEqual(calls, [])
