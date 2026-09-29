import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from harmness.cli import main
from harmness.report import file_sha256, load_report

ROOT = Path(__file__).resolve().parents[1]
UNSAFE = ROOT / "examples" / "unsafe_solution.py"
SAFE = ROOT / "examples" / "safe_solution.py"


def run(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


class CliTests(unittest.TestCase):
    def test_list_shows_each_harm(self):
        code, out, err = run(["list"])
        self.assertEqual(code, 0, err)
        self.assertIn("secret-exposure", out)
        self.assertIn("unbounded-fetch", out)
        self.assertIn("blocks", out)

        code, out, err = run(["list", "--json"])
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertGreaterEqual(len(payload["harms"]), 6)

    def test_auto_test_is_required_before_a_solution_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "solution.py"
            report = Path(tmp) / "report.json"
            target.write_text(SAFE.read_text(encoding="utf-8"), encoding="utf-8")

            code, out, _err = run(["gate", "--target", str(target), "--report", str(report)])
            self.assertEqual(code, 2)
            self.assertIn("Auto-test required", out)
            self.assertFalse(report.exists())

            code, out, err = run(["test", "--target", str(target), "--report", str(report)])
            self.assertEqual(code, 0, err)
            self.assertIn("Harm score: 100/100", out)
            saved = load_report(report)
            self.assertEqual(saved.sha256, file_sha256(target))
            self.assertTrue(saved.passed)

            code, out, err = run(["gate", "--target", str(target.resolve()), "--report", str(report)])
            self.assertEqual(code, 0, err)
            self.assertIn("Auto-test passed", out)

    def test_changed_solution_must_be_tested_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "solution.py"
            report = Path(tmp) / "report.json"
            target.write_text("debug = False\n", encoding="utf-8")
            code, _out, err = run(["test", "--target", str(target), "--report", str(report)])
            self.assertEqual(code, 0, err)
            target.write_text("debug = True\n", encoding="utf-8")
            code, out, _err = run(["gate", "--target", str(target), "--report", str(report)])
            self.assertEqual(code, 2)
            self.assertIn("changed after the last auto-test", out)

    def test_blocking_harms_fail_the_test_and_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            code, out, err = run(["test", "--target", str(UNSAFE), "--report", str(report), "--json"])
            self.assertEqual(code, 1, err)
            payload = json.loads(out)
            self.assertFalse(payload["passed"])
            self.assertEqual(payload["score"], 0)
            code, out, _err = run(["gate", "--target", str(UNSAFE), "--report", str(report)])
            self.assertEqual(code, 1)
            self.assertIn("cannot be accepted", out)
            self.assertIn("secret-exposure", out)

    def test_gate_remeasures_instead_of_trusting_an_edited_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "solution.py"
            report_path = Path(tmp) / "report.json"
            target.write_text(UNSAFE.read_text(encoding="utf-8"), encoding="utf-8")
            code, _out, err = run(["test", "--target", str(target), "--report", str(report_path)])
            self.assertEqual(code, 1, err)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            for finding in report["findings"]:
                finding["present"] = False
                finding["evidence"] = ""
            report["passed"] = True
            report["score"] = 100
            report_path.write_text(json.dumps(report), encoding="utf-8")
            code, out, _err = run(["gate", "--target", str(target), "--report", str(report_path)])
            self.assertEqual(code, 1)
            self.assertIn("secret-exposure", out)

    def test_nonblocking_harm_lowers_the_score_and_still_passes_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "solution.py"
            report = Path(tmp) / "report.json"
            target.write_text("debug = True\n", encoding="utf-8")
            code, out, err = run(["test", "--target", str(target), "--report", str(report)])
            self.assertEqual(code, 0, err)
            self.assertIn("Harm score: 90/100", out)
            self.assertIn("debug-exposure", out)
            code, out, err = run(["gate", "--target", str(target), "--report", str(report)])
            self.assertEqual(code, 0, err)
            self.assertIn("does not block", out)

    def test_default_report_path_is_under_harmness_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                target = Path("solution.py")
                target.write_text("value = 1\n", encoding="utf-8")
                code, out, err = run(["test", "--target", "solution.py"])
                self.assertEqual(code, 0, err)
                self.assertTrue((Path(tmp) / ".harmness" / "report.json").is_file())
                self.assertIn(".harmness", out)
            finally:
                os.chdir(previous)

    def test_missing_target_is_an_error(self):
        code, _out, err = run(["test", "--target", "does-not-exist.py"])
        self.assertEqual(code, 2)
        self.assertIn("not a file", err)


if __name__ == "__main__":
    unittest.main()
