import unittest

from harmness.catalog import load_catalog
from harmness.measure import WINDOW_BEFORE, evaluate, measure, score
from harmness.models import Finding


def harm(harm_id):
    return next(item for item in load_catalog() if item.id == harm_id)


class MeasureTests(unittest.TestCase):
    def test_secret_variants_are_measured(self):
        secret = harm("secret-exposure")
        samples = [
            'api_key = "AKIA1234567890ABCDEF"',
            'token = "ghp_abcdefghijklmnopqrst"',
            'key = "sk_live_1234567890"',
            "-----BEGIN PRIVATE KEY-----",
            'password = "s3cr3t-value"',
        ]
        for sample in samples:
            finding = evaluate(secret, sample)
            self.assertTrue(finding.present, sample)

    def test_placeholder_secrets_are_ignored_without_hiding_a_real_one(self):
        text = '\n'.join(
            [
                'api_key = "changeme-value"',
                'api_key = "AKIA1234567890ABCDEF"',
            ]
        )
        finding = evaluate(harm("secret-exposure"), text)
        self.assertTrue(finding.present)
        self.assertIn("line 2:", finding.evidence)
        self.assertNotIn("line 1:", finding.evidence)

    def test_nearby_confirmation_suppresses_a_destructive_call(self):
        destructive = harm("destructive-without-confirm")
        self.assertTrue(evaluate(destructive, "DROP TABLE users").present)
        self.assertFalse(evaluate(destructive, "dry_run = True\nDROP TABLE users\n").present)

    def test_confirmation_outside_the_window_does_not_suppress(self):
        gap = "\n".join(["user_confirmed = True", *([""] * WINDOW_BEFORE), "os.remove(path)"])
        finding = evaluate(harm("destructive-without-confirm"), gap)
        self.assertTrue(finding.present)
        self.assertIn("os.remove(path)", finding.evidence)

    def test_authorization_must_be_near_the_route(self):
        missing = harm("missing-authorization")
        open_route = '@app.route("/items", methods=["DELETE"])\ndef delete_item():\n    return None\n'
        closed_route = '@app.delete("/items/<item_id>")\ndef delete_item(user):\n    require_auth(user)\n'
        self.assertTrue(evaluate(missing, open_route).present)
        self.assertFalse(evaluate(missing, closed_route).present)

    def test_personal_data_in_a_log_is_measured(self):
        pii = harm("pii-in-logs")
        self.assertTrue(evaluate(pii, 'logger.info("removed ada@company.test")').present)
        self.assertTrue(evaluate(pii, 'print("ssn 000")').present)
        self.assertFalse(evaluate(pii, 'logger.info("removed the item")').present)

    def test_timeout_suppresses_an_http_call(self):
        fetch = harm("unbounded-fetch")
        self.assertTrue(evaluate(fetch, 'requests.get("https://api.company.test/items")').present)
        self.assertFalse(evaluate(fetch, 'requests.get(url, timeout=5)').present)

    def test_examples_cover_every_harm_and_a_clear_solution(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        unsafe = measure((root / "examples" / "unsafe_solution.py").read_text(encoding="utf-8"))
        safe = measure((root / "examples" / "safe_solution.py").read_text(encoding="utf-8"))
        self.assertEqual(
            {finding.id for finding in unsafe if finding.present},
            {item.id for item in load_catalog()},
        )
        self.assertTrue(all(not finding.present for finding in safe))
        self.assertEqual(score(unsafe), 0)
        self.assertEqual(score(safe), 100)

    def test_score_uses_severity_weights(self):
        findings = [
            Finding("a", "A", "critical", "data", True, True, "line 1: x"),
            Finding("b", "B", "medium", "exposure", False, False, ""),
        ]
        self.assertEqual(score(findings), 60)


if __name__ == "__main__":
    unittest.main()
