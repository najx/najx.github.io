"""The weekly workflow must never send an oversized PR body to GitHub."""

import unittest

from newsbot.pr_body import MAX_BODY_BYTES, render_body


class TestPrBody(unittest.TestCase):
    def test_short_diagnostics_are_kept_in_full(self):
        body = render_body(
            "2026-w39", {"checked": 1, "unsupported": [], "reconsidered": [], "synthesis": []},
            "selection line\nverification line\n", "https://github.com/najx/najx.github.io/actions/runs/1",
        )
        self.assertIn("Aucune affirmation non étayée sur 1", body)
        self.assertIn("selection line\nverification line", body)
        self.assertIn("actions/runs/1", body)

    def test_large_multibyte_diagnostics_stay_below_github_limit(self):
        finding = {"support": 0.12, "sentence": "É" * 1000, "note": "🐈" * 1000,
                   "excerpt": "É" * 1000, "source": "https://example.org"}
        checks = {"checked": 150, "unsupported": [finding] * 150,
                  "reconsidered": [finding] * 150, "synthesis": [finding] * 150}
        body = render_body("2026-w39", checks, "début\n" + "🐈" * 100_000 + "\nfin",
                           "https://github.com/najx/najx.github.io/actions/runs/1")
        self.assertLessEqual(len(body.encode("utf-8")), MAX_BODY_BYTES)
        self.assertLess(MAX_BODY_BYTES, 65_536)
        self.assertIn("début", body)
        self.assertIn("fin", body)
        self.assertIn("omise(s) ici", body)
        self.assertIn("Milieu du journal omis", body)
