//! MKAOS byte-v1 tokenizer shared with the Python from-scratch trainer.
//! Contract: data/mkaos/tokenizer-contract.json; golden vectors are shared across Rust/Python.
use crate::KernelError;

#[derive(Debug, Clone, Copy, Default)]
pub struct ByteTokenizer;
impl ByteTokenizer {
    pub const VOCAB_SIZE: usize = 257;
    pub const EOS_ID: usize = 256;

    /// UTF-8 bytes map to token IDs 0..=255. EOS is not automatically appended.
    pub fn encode(&self, text: &str) -> Vec<usize> { text.as_bytes().iter().map(|b| *b as usize).collect() }

    /// Decode byte IDs. EOS is skipped; out-of-range IDs are rejected.
    /// Incomplete UTF-8 sequences are replaced, so callers should decode accumulated output.
    pub fn decode(&self, ids: &[usize]) -> Result<String, KernelError> {
        let mut bytes = Vec::with_capacity(ids.len());
        for &id in ids {
            if id == Self::EOS_ID { continue; }
            if id > 255 { return Err(KernelError::InvalidToken { token: id, vocab_size: Self::VOCAB_SIZE }); }
            bytes.push(id as u8);
        }
        Ok(String::from_utf8_lossy(&bytes).into_owned())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn round_trips_utf8_and_skips_eos() {
        let t=ByteTokenizer;
        let text="Merhaba, dünya! 🌍";
        let mut ids=t.encode(text);
        ids.push(ByteTokenizer::EOS_ID);
        assert_eq!(t.decode(&ids).unwrap(), text);
    }
    #[test] fn rejects_unknown_ids() { assert!(ByteTokenizer.decode(&[257]).is_err()); }

    #[test]
    fn shared_golden_vectors_match_python_contract() {
        let vectors = include_str!("../../../data/mkaos/tokenizer-golden-vectors.tsv");
        for (line_number, line) in vectors.lines().enumerate() {
            let mut parts = line.splitn(3, '\t');
            let name = parts.next().expect("vector name");
            let text = parts.next().expect("vector text");
            let encoded = parts.next().expect("vector token ids");
            let expected: Vec<usize> = if encoded.is_empty() {
                Vec::new()
            } else {
                encoded.split(',').map(|item| item.parse().expect("integer token id")).collect()
            };
            assert_eq!(ByteTokenizer.encode(text), expected, "vector {name} at line {}", line_number + 1);
            assert_eq!(ByteTokenizer.decode(&expected).unwrap(), text, "decode vector {name}");
        }
    }

    #[test]
    fn constants_match_shared_contract_metadata() {
        let contract = include_str!("../../../data/mkaos/tokenizer-contract.json");
        assert!(contract.contains("\"contract_id\": \"mkaos-byte-v1\""));
        assert!(contract.contains("\"vocab_size\": 257"));
        assert!(contract.contains("\"eos_id\": 256"));
        assert_eq!(ByteTokenizer::VOCAB_SIZE, 257);
        assert_eq!(ByteTokenizer::EOS_ID, 256);
    }
}