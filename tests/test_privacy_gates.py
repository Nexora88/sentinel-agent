import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.finance_engine import FinanceEngine
from tools.autonomous_finance import AutonomousFinance


class ExternalFinancePrivacyTests(unittest.TestCase):
    def test_external_quotes_are_disabled_without_opt_in(self):
        engine = FinanceEngine(ollama=Mock())
        with patch.dict(os.environ, {"ALLOW_EXTERNAL_FINANCE_DATA": "false"}):
            with patch("requests.get") as get:
                quote = engine.crypto_quote("bitcoin")
                stock = engine.stock_quote("AAPL")
                self.assertIn("error", quote)
                self.assertIn("error", stock)
                get.assert_not_called()

    def test_paper_prices_do_not_leave_machine_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = AutonomousFinance(ollama=Mock(), state_dir=directory)
            with patch.dict(os.environ, {"ALLOW_EXTERNAL_FINANCE_DATA": "false"}):
                with patch("requests.get") as get:
                    self.assertIsNone(engine.get_price("BTC"))
                    get.assert_not_called()

    def test_website_scanning_is_disabled_without_opt_in(self):
        from core.pipeline import SentinelPipeline
        pipeline = object.__new__(SentinelPipeline)
        with patch.dict(os.environ, {"ALLOW_SITE_SCANNING": "false"}):
            result = pipeline.scan_website("https://example.com")
        self.assertIn("varsayılan olarak kapalı", result)

    def test_corrupt_portfolio_fails_closed_instead_of_resetting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                AutonomousFinance(ollama=Mock(), state_dir=directory)
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")


if __name__ == "__main__":
    unittest.main()
