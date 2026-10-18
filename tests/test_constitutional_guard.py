import unittest

from core.constitutional_guard import guard_output


class ConstitutionalGuardTests(unittest.TestCase):
    def test_redacts_github_token(self):
        result = guard_output("example token ghp_" + "A" * 30 + " end")
        self.assertIn("[REDACTED: possible secret]", result.text)
        self.assertIn("github_token:1", result.findings)

    def test_redacts_private_key_block(self):
        # Assemble the sentinel at runtime so repository secret scanners do not
        # mistake this synthetic regression fixture for a committed private key.
        begin = "-----BEGIN " + "PRIVATE KEY-----"
        end = "-----END " + "PRIVATE KEY-----"
        value = begin + "\nsecret-material\n" + end
        result = guard_output(value)
        self.assertNotIn("secret-material", result.text)
        self.assertIn("private_key_block:1", result.findings)

    def test_keeps_normal_turkish_text(self):
        value = "Atatürk, bilimsel düşünceyi ve bağımsızlığı önemsemiştir."
        result = guard_output(value)
        self.assertEqual(result.text, value)
        self.assertEqual(result.findings, ())

    def test_does_not_claim_to_verify_truth(self):
        result = guard_output("Kaynak göstermeden tarihsel bir iddia.")
        self.assertEqual(result.text, "Kaynak göstermeden tarihsel bir iddia.")
        self.assertEqual(result.findings, ())


if __name__ == "__main__":
    unittest.main()
