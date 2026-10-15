//! MKAOS native LLM runtime foundation.
//!
//! This crate has no third-party Rust dependencies and forbids unsafe Rust. It provides
//! checked CPU tensor primitives, model-manifest validation, and bounded autoregressive
//! decoding. A production transformer, tokenizer, signed bundle verification, and
//! accelerator kernels remain separate work.

#![forbid(unsafe_code)]

use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EngineError {
    InvalidShape(&'static str),
    InvalidManifest(&'static str),
    InvalidInput(&'static str),
    Backend(String),
}
impl fmt::Display for EngineError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidShape(message) | Self::InvalidManifest(message) |
            Self::InvalidInput(message) => write!(f, "{message}"),
            Self::Backend(message) => write!(f, "backend error: {message}"),
        }
    }
}
impl std::error::Error for EngineError {}
pub type EngineResult<T> = Result<T, EngineError>;

#[derive(Debug, Clone, PartialEq)]
pub struct Tensor { rows: usize, cols: usize, data: Vec<f32> }

impl Tensor {
    pub fn new(rows: usize, cols: usize, data: Vec<f32>) -> EngineResult<Self> {
        if rows == 0 || cols == 0 || rows.checked_mul(cols) != Some(data.len()) {
            return Err(EngineError::InvalidShape("tensor dimensions do not match data"));
        }
        if data.iter().any(|value| !value.is_finite()) {
            return Err(EngineError::InvalidInput("tensor contains a non-finite value"));
        }
        Ok(Self { rows, cols, data })
    }
    pub fn rows(&self) -> usize { self.rows }
    pub fn cols(&self) -> usize { self.cols }
    pub fn data(&self) -> &[f32] { &self.data }

    pub fn matmul(&self, rhs: &Self) -> EngineResult<Self> {
        if self.cols != rhs.rows { return Err(EngineError::InvalidShape("matmul inner dimensions differ")); }
        let mut output = vec![0.0; self.rows * rhs.cols];
        for row in 0..self.rows {
            for inner in 0..self.cols {
                let left = self.data[row * self.cols + inner];
                for col in 0..rhs.cols { output[row * rhs.cols + col] += left * rhs.data[inner * rhs.cols + col]; }
            }
        }
        Self::new(self.rows, rhs.cols, output)
    }

    pub fn softmax_rows(&self) -> EngineResult<Self> {
        let mut output = vec![0.0; self.data.len()];
        for row in 0..self.rows {
            let start = row * self.cols;
            let values = &self.data[start..start + self.cols];
            let maximum = values.iter().copied().fold(f32::NEG_INFINITY, f32::max);
            let sum: f32 = values.iter().map(|value| (value - maximum).exp()).sum();
            if !sum.is_finite() || sum <= 0.0 { return Err(EngineError::InvalidInput("softmax normalization failed")); }
            for col in 0..self.cols { output[start + col] = (values[col] - maximum).exp() / sum; }
        }
        Self::new(self.rows, self.cols, output)
    }

    pub fn rms_norm_rows(&self, epsilon: f32) -> EngineResult<Self> {
        if !epsilon.is_finite() || epsilon <= 0.0 { return Err(EngineError::InvalidInput("RMSNorm epsilon must be positive")); }
        let mut output = vec![0.0; self.data.len()];
        for row in 0..self.rows {
            let start = row * self.cols;
            let values = &self.data[start..start + self.cols];
            let mean_square = values.iter().map(|value| value * value).sum::<f32>() / self.cols as f32;
            let scale = (mean_square + epsilon).sqrt().recip();
            for col in 0..self.cols { output[start + col] = values[col] * scale; }
        }
        Self::new(self.rows, self.cols, output)
    }

    pub fn silu(&self) -> EngineResult<Self> {
        let output = self.data.iter().map(|value| value / (1.0 + (-value).exp())).collect();
        Self::new(self.rows, self.cols, output)
    }

    pub fn embedding(&self, token_ids: &[u32]) -> EngineResult<Self> {
        if token_ids.is_empty() { return Err(EngineError::InvalidInput("token sequence must not be empty")); }
        let mut output = Vec::with_capacity(token_ids.len() * self.cols);
        for token in token_ids {
            let row = *token as usize;
            if row >= self.rows { return Err(EngineError::InvalidInput("token id is outside the vocabulary")); }
            output.extend_from_slice(&self.data[row * self.cols..(row + 1) * self.cols]);
        }
        Self::new(token_ids.len(), self.cols, output)
    }
}

/// Metadata validation only. Callers must separately verify the weight-file digest,
/// signature, provenance, and license evidence before loading a model bundle.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ModelManifest {
    pub format_version: u32, pub model_id: String, pub architecture: String,
    pub vocabulary_size: u32, pub hidden_size: u32, pub layer_count: u32,
    pub attention_heads: u32, pub max_context_tokens: u32, pub stop_token_id: u32,
    pub weights_file: String, pub weights_sha256: String, pub license_id: String,
    pub dataset_manifest_sha256: String,
}
impl ModelManifest {
    pub fn validate(&self) -> EngineResult<()> {
        if self.format_version != 1 { return Err(EngineError::InvalidManifest("unsupported bundle format version")); }
        if self.model_id.trim().is_empty() || self.model_id.len() > 128 { return Err(EngineError::InvalidManifest("invalid model id")); }
        if self.architecture != "mkaos-transformer-v1" { return Err(EngineError::InvalidManifest("unsupported model architecture")); }
        if self.vocabulary_size < 2 || self.hidden_size == 0 || self.layer_count == 0 ||
            self.attention_heads == 0 || self.hidden_size % self.attention_heads != 0 {
            return Err(EngineError::InvalidManifest("invalid transformer dimensions"));
        }
        if self.max_context_tokens == 0 || self.max_context_tokens > 1_048_576 {
            return Err(EngineError::InvalidManifest("context length outside allowed bounds"));
        }
        if self.stop_token_id >= self.vocabulary_size { return Err(EngineError::InvalidManifest("stop token is outside the vocabulary")); }
        if self.weights_file.is_empty() || self.weights_file.contains("..") ||
            self.weights_file.starts_with('/') || self.weights_file.starts_with('\\') || self.weights_file.contains(':') {
            return Err(EngineError::InvalidManifest("weights path must be a relative bundle path"));
        }
        if !is_sha256_hex(&self.weights_sha256) || !is_sha256_hex(&self.dataset_manifest_sha256) {
            return Err(EngineError::InvalidManifest("manifest digests must be 64 hexadecimal characters"));
        }
        if self.license_id.trim().is_empty() || self.license_id.len() > 128 {
            return Err(EngineError::InvalidManifest("model license evidence is required"));
        }
        Ok(())
    }
}
fn is_sha256_hex(value: &str) -> bool { value.len() == 64 && value.bytes().all(|byte| byte.is_ascii_hexdigit()) }

pub trait Tokenizer {
    fn encode(&self, text: &str) -> EngineResult<Vec<u32>>;
    fn decode(&self, token_ids: &[u32]) -> EngineResult<String>;
}
/// A future CPU/GPU transformer backend must return vocabulary-sized finite logits.
pub trait InferenceBackend {
    fn next_logits(&mut self, token_ids: &[u32], manifest: &ModelManifest) -> EngineResult<Vec<f32>>;
}
pub struct NativeEngine<B, T> { backend: B, tokenizer: T, manifest: ModelManifest }

impl<B: InferenceBackend, T: Tokenizer> NativeEngine<B, T> {
    pub fn new(backend: B, tokenizer: T, manifest: ModelManifest) -> EngineResult<Self> {
        manifest.validate()?;
        Ok(Self { backend, tokenizer, manifest })
    }
    pub fn generate(&mut self, prompt: &str, max_new_tokens: usize) -> EngineResult<String> {
        if prompt.trim().is_empty() { return Err(EngineError::InvalidInput("prompt must not be empty")); }
        if max_new_tokens == 0 || max_new_tokens > 16_384 {
            return Err(EngineError::InvalidInput("generation limit outside allowed bounds"));
        }
        let mut tokens = self.tokenizer.encode(prompt)?;
        if tokens.is_empty() || tokens.iter().any(|token| *token >= self.manifest.vocabulary_size) {
            return Err(EngineError::InvalidInput("tokenizer produced an invalid token sequence"));
        }
        if tokens.len() >= self.manifest.max_context_tokens as usize {
            return Err(EngineError::InvalidInput("prompt exceeds model context limit"));
        }
        let prompt_len = tokens.len();
        for _ in 0..max_new_tokens {
            if tokens.len() >= self.manifest.max_context_tokens as usize { break; }
            let logits = self.backend.next_logits(&tokens, &self.manifest)?;
            if logits.len() != self.manifest.vocabulary_size as usize || logits.iter().any(|v| !v.is_finite()) {
                return Err(EngineError::Backend("backend returned invalid logits".into()));
            }
            let next = logits.iter().enumerate().max_by(|left, right| left.1.total_cmp(right.1))
                .map(|(index, _)| index as u32).ok_or(EngineError::Backend("backend returned no logits".into()))?;
            if next >= self.manifest.vocabulary_size { return Err(EngineError::Backend("backend token outside vocabulary".into())); }
            if next == self.manifest.stop_token_id { break; }
            tokens.push(next);
        }
        self.tokenizer.decode(&tokens[prompt_len..])
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn manifest() -> ModelManifest {
        ModelManifest { format_version: 1, model_id: "test-model".into(),
            architecture: "mkaos-transformer-v1".into(), vocabulary_size: 4, hidden_size: 4,
            layer_count: 2, attention_heads: 2, max_context_tokens: 16, stop_token_id: 3,
            weights_file: "weights/model.bin".into(), weights_sha256: "a".repeat(64),
            license_id: "TEST-ONLY".into(), dataset_manifest_sha256: "b".repeat(64) }
    }
    struct TestTokenizer;
    impl Tokenizer for TestTokenizer {
        fn encode(&self, text: &str) -> EngineResult<Vec<u32>> { Ok(text.bytes().map(|byte| (byte % 2) as u32).collect()) }
        fn decode(&self, token_ids: &[u32]) -> EngineResult<String> {
            Ok(token_ids.iter().map(|token| char::from(b'a' + (*token as u8))).collect())
        }
    }
    struct TestBackend;
    impl InferenceBackend for TestBackend {
        fn next_logits(&mut self, _tokens: &[u32], _manifest: &ModelManifest) -> EngineResult<Vec<f32>> {
            Ok(vec![0.0, 2.0, 1.0, -1.0])
        }
    }
    #[test]
    fn tensor_matmul_and_embedding_are_checked() {
        let left = Tensor::new(2, 2, vec![1.0, 2.0, 3.0, 4.0]).unwrap();
        let right = Tensor::new(2, 1, vec![2.0, 1.0]).unwrap();
        assert_eq!(left.matmul(&right).unwrap().data(), &[4.0, 10.0]);
        assert_eq!(left.embedding(&[1]).unwrap().data(), &[3.0, 4.0]);
        assert!(left.embedding(&[2]).is_err());
    }
    #[test]
    fn softmax_is_stable_and_normalized() {
        let probabilities = Tensor::new(1, 3, vec![1000.0, 1001.0, 999.0]).unwrap().softmax_rows().unwrap();
        assert!((probabilities.data().iter().sum::<f32>() - 1.0).abs() < 1e-5);
    }
    #[test]
    fn rejects_unsafe_bundle_paths_and_bad_digests() {
        let mut model = manifest(); model.validate().unwrap();
        model.weights_file = "../outside.bin".into(); assert!(model.validate().is_err());
        model.weights_file = "weights.bin".into(); model.weights_sha256 = "not-a-digest".into();
        assert!(model.validate().is_err());
    }
    #[test]
    fn greedy_decode_is_bounded_and_uses_backend_contract() {
        let mut engine = NativeEngine::new(TestBackend, TestTokenizer, manifest()).unwrap();
        assert_eq!(engine.generate("x", 2).unwrap(), "bb");
        assert!(engine.generate(" ", 2).is_err());
        assert!(engine.generate("x", 0).is_err());
    }
    #[test]
    fn refuses_incompatible_transformer_dimensions() {
        let mut model = manifest(); model.hidden_size = 5; assert!(model.validate().is_err());
    }
}
