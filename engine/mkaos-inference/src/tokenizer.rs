//! Dependency-free UTF-8 byte tokenizer for tiny byte-level models and loader tests.
//! This is NOT compatible with SentencePiece/BPE tokenizers used by most pretrained LLMs.
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
}