"""Contract checks for the evidence-first MKAOS command dashboard."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardContractTests(unittest.TestCase):
    def test_dashboard_has_accessible_status_and_primary_panels(self):
        html = (ROOT / "web" / "templates" / "index.html").read_text(encoding="utf-8")
        # Assert the stable panel layout currently rendered by index.html; avoid
        # requiring IDs from an older, unshipped command-dashboard mockup.
        for marker in (
            '<html lang="tr">',
            '<main class="main">',
            'id="panel-bridge"',
            'id="panel-status"',
            'id="status-text"',
            'id="control-status"',
            'id="sovereignty-mini-label"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)

    def test_dashboard_does_not_claim_airgap_without_host_evidence(self):
        js = (ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('hasHostProof = Boolean(sovereign.host_egress_verified || sovereign.air_gapped_verified)', js)
        self.assertIn('"AĞ ÇIKIŞI DOĞRULANMADI"', js)
        self.assertIn('textContent = String(job.title || job.name || job.kind || job.id || "İsimsiz görev")', js)

    def test_dashboard_styles_include_small_screen_layout(self):
        css = (ROOT / "web" / "static" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".command-dashboard", css)
        self.assertIn("@media(max-width:600px)", css)


if __name__ == "__main__":
    unittest.main()
