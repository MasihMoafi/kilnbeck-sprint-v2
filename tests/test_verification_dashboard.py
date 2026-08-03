import unittest

import verification_dashboard as dashboard


class VerificationDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = dashboard.build_report()

    def test_report_has_no_executable_failures(self):
        failures = [item for item in self.report["checks"]
                    if item["status"] == "fail"]
        self.assertEqual([], failures, failures)

    def test_real_dataset_is_verified(self):
        item = next(item for item in self.report["checks"]
                    if item["id"] == "dataset-run")
        self.assertEqual("pass", item["status"])

    def test_golden_cases_are_visible(self):
        ids = {item["id"] for item in self.report["checks"]}
        self.assertTrue({f"golden-{i}" for i in range(1, 8)}.issubset(ids))

    def test_regression_gap_is_not_hidden(self):
        item = next(item for item in self.report["checks"]
                    if item["id"] == "golden-6")
        self.assertIn(item["status"], {"warn", "pass"})

    def test_static_export_embeds_report(self):
        html = dashboard.render_html(self.report)
        self.assertIn("Kilnbeck verification", html)
        self.assertNotIn("__REPORT__", html)
        self.assertIn('"checks":', html)


if __name__ == "__main__":
    unittest.main()
