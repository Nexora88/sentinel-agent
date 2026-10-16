import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SharedTokenizerContractTests(unittest.TestCase):
    def test_contract_is_explicit_and_byte_compatible(self):
        contract = json.loads((ROOT / "spec" / "mkaos-tokenizer-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["format"], "mkaos-byte-v1")
        self.assertEqual(contract["vocab_size"], 257)
        self.assertEqual(contract["eos_id"], 256)
        self.assertEqual(contract["mapping"], "UTF-8 byte value -> same token ID; 256 is EOS")
        self.assertEqual(contract["normalization"], "none")
        self.assertIn("document_boundary", contract)

    def test_rust_implementation_references_same_contract(self):
        rust = (ROOT / "engine" / "mkaos-inference" / "src" / "tokenizer.rs").read_text(encoding="utf-8")
        self.assertIn('include_str!("../../../spec/mkaos-tokenizer-v1.json")', rust)
        self.assertIn("UTF-8 byte value -> same token ID; 256 is EOS", rust)

    def test_training_export_uses_shared_contract(self):
        trainer = (ROOT / "tools" / "train_mkaos_from_scratch.py").read_text(encoding="utf-8")
        self.assertIn('ROOT / "spec" / "mkaos-tokenizer-v1.json"', trainer)
        self.assertIn("tokenizer_sha256", trainer)


if __name__ == "__main__":
    unittest.main()
