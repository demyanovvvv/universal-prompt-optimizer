import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from evals.baseline import (
    baseline_fingerprint,
    summarize_matrix,
    to_matrix_report,
    validate_baseline,
)
from evals.baseline_gate import evaluate

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evals" / "baselines" / "matrix.json"


def _build_report(quality_by_mode=None):
    quality_by_mode = quality_by_mode or {}
    cases = []
    for index, case_id in enumerate(("one", "two")):
        results = {}
        for mode in ("OFF", "AUTO", "PREVIEW"):
            passed = quality_by_mode.get(mode, {}).get(case_id, True)
            results[mode] = {
                "id": case_id,
                "status": "measured",
                "quality": {"passed": passed},
            }
        cases.append({"id": case_id, "results": results})
    return {
        "schemaVersion": 1,
        "mode": "matrix",
        "modes": ["OFF", "AUTO", "PREVIEW"],
        "caseResults": cases,
        "input": {"format": "jsonl", "sha256": "a" * 64},
    }


class BaselineRoundTripTests(unittest.TestCase):
    def test_summarize_and_rebuild_preserves_passes(self):
        summary = summarize_matrix(_build_report())
        self.assertEqual(summary["kind"], "matrix-baseline")
        self.assertEqual(len(summary["cases"]), 2)
        rebuilt = to_matrix_report(summary)
        self.assertEqual(rebuilt["mode"], "matrix")
        self.assertEqual(rebuilt["input"]["sha256"], "a" * 64)

    def test_committed_baseline_is_well_formed(self):
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(validate_baseline(data), [])
        self.assertEqual(data["kind"], "matrix-baseline")
        self.assertEqual(data["modes"], ["OFF", "AUTO", "PREVIEW"])
        self.assertEqual(len(data["cases"]), 40)
        ids = [case["id"] for case in data["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, sorted(ids))

    def test_committed_baseline_fingerprint_matches_contents(self):
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(data["fingerprint"], baseline_fingerprint(data))

    def test_baseline_validation_flags_missing_digest_and_fingerprint(self):
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
        data["input"]["sha256"] = "not-a-digest"
        data["fingerprint"] = "short"
        errors = validate_baseline(data)

        self.assertTrue(any("input.sha256" in error for error in errors))
        self.assertTrue(any("fingerprint" in error for error in errors))

    def test_gate_reports_fingerprint_drift(self):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            report = _build_report()
            baseline_path.write_text(json.dumps(summarize_matrix(report)), encoding="utf-8")
            candidate = json.loads(json.dumps(report))
            candidate["caseResults"][0]["results"]["OFF"]["response"] = {"text": "changed"}
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = evaluate(baseline_path, candidate_path)

            self.assertFalse(result["passed"])
            self.assertTrue(any("drifted" in reason for reason in result["failureReasons"]))
            self.assertIn("fingerprint", result)

    def test_gate_reports_removed_case_reason(self):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            report = _build_report()
            baseline_path.write_text(json.dumps(summarize_matrix(report)), encoding="utf-8")
            candidate = json.loads(json.dumps(report))
            candidate["caseResults"] = candidate["caseResults"][:1]
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = evaluate(baseline_path, candidate_path)

            self.assertFalse(result["passed"])
            self.assertTrue(any("case removed: two" in reason for reason in result["failureReasons"]))

    def test_gate_flags_quality_regression(self):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            baseline_path.write_text(
                json.dumps(summarize_matrix(_build_report())), encoding="utf-8"
            )
            candidate_path.write_text(
                json.dumps(_build_report({"AUTO": {"one": False}})), encoding="utf-8"
            )
            result = evaluate(baseline_path, candidate_path)
            self.assertFalse(result["passed"])
            self.assertIn("one", result["modes"]["AUTO"]["regressions"])

    def test_gate_flags_fixture_digest_change(self):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            baseline_path.write_text(
                json.dumps(summarize_matrix(_build_report())), encoding="utf-8"
            )
            changed = _build_report()
            changed["input"]["sha256"] = "def"
            candidate_path.write_text(json.dumps(changed), encoding="utf-8")
            result = evaluate(baseline_path, candidate_path)
            self.assertFalse(result["passed"])
            self.assertTrue(any("fixture digest changed" in error for error in result["errors"]))

    def test_gate_passes_on_unchanged_matrix(self):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            report = _build_report()
            baseline_path.write_text(json.dumps(summarize_matrix(report)), encoding="utf-8")
            candidate_path.write_text(json.dumps(report), encoding="utf-8")
            result = evaluate(baseline_path, candidate_path)
            self.assertTrue(result["passed"], result["errors"])


class BaselineGateCliTests(unittest.TestCase):
    def test_cli_returns_nonzero_on_regression(self):
        with TemporaryDirectory() as raw:
            directory = Path(raw)
            baseline_path = directory / "baseline.json"
            candidate_path = directory / "candidate.json"
            baseline_path.write_text(json.dumps(summarize_matrix(_build_report())), encoding="utf-8")
            candidate_path.write_text(
                json.dumps(_build_report({"PREVIEW": {"two": False}})), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "evals.baseline_gate",
                    "--baseline",
                    str(baseline_path),
                    "--candidate",
                    str(candidate_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
            self.assertFalse(json.loads(completed.stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
