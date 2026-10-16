//! Dependency-free local dense-vector contract for future MKAOS-owned encoders.
//!
//! This module ranks vectors produced by a compatible encoder; it does not itself
//! tokenize text or claim semantic understanding. Until an audited Rust encoder and
//! owned/reviewed weights exist, callers must identify the provider in their reports.

#[derive(Debug, Clone, PartialEq)]
pub enum EmbeddingError {
    EmptyVector,
    NonFiniteValue,
    DimensionMismatch { expected: usize, actual: usize },
    ModelSpaceMismatch,
    InvalidTopK,
}
impl std::fmt::Display for EmbeddingError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptyVector => write!(f, "embedding vector must not be empty"),
            Self::NonFiniteValue => write!(f, "embedding contains NaN or infinity"),
            Self::DimensionMismatch { expected, actual } => write!(f, "embedding dimension mismatch: expected {expected}, got {actual}"),
            Self::ModelSpaceMismatch => write!(f, "vectors were produced by different embedding model spaces"),
            Self::InvalidTopK => write!(f, "top_k must be positive"),
        }
    }
}
impl std::error::Error for EmbeddingError {}

#[derive(Debug, Clone, PartialEq)]
pub struct EmbeddingVector {
    pub model_id: String,
    pub values: Vec<f32>,
}
impl EmbeddingVector {
    pub fn new(model_id: impl Into<String>, values: Vec<f32>) -> Result<Self, EmbeddingError> {
        let model_id = model_id.into();
        if model_id.trim().is_empty() || values.is_empty() { return Err(EmbeddingError::EmptyVector); }
        if values.iter().any(|v| !v.is_finite()) { return Err(EmbeddingError::NonFiniteValue); }
        if values.iter().all(|v| *v == 0.0) { return Err(EmbeddingError::EmptyVector); }
        Ok(Self { model_id, values })
    }
}

/// Contract implemented by a future local Rust tokenizer + trained encoder backend.
pub trait LocalTextEncoder {
    fn model_id(&self) -> &str;
    fn encode(&self, text: &str) -> Result<EmbeddingVector, EmbeddingError>;
}

pub fn cosine_similarity(query: &EmbeddingVector, candidate: &EmbeddingVector) -> Result<f32, EmbeddingError> {
    if query.model_id != candidate.model_id { return Err(EmbeddingError::ModelSpaceMismatch); }
    if query.values.len() != candidate.values.len() {
        return Err(EmbeddingError::DimensionMismatch { expected: query.values.len(), actual: candidate.values.len() });
    }
    let dot: f64 = query.values.iter().zip(&candidate.values).map(|(a,b)| *a as f64 * *b as f64).sum();
    let qn: f64 = query.values.iter().map(|v| (*v as f64) * (*v as f64)).sum::<f64>().sqrt();
    let cn: f64 = candidate.values.iter().map(|v| (*v as f64) * (*v as f64)).sum::<f64>().sqrt();
    if qn == 0.0 || cn == 0.0 { return Err(EmbeddingError::EmptyVector); }
    Ok((dot / (qn * cn)).clamp(-1.0, 1.0) as f32)
}

pub fn rank_by_cosine(
    query: &EmbeddingVector,
    candidates: &[(String, EmbeddingVector)],
    top_k: usize,
) -> Result<Vec<(String, f32)>, EmbeddingError> {
    if top_k == 0 { return Err(EmbeddingError::InvalidTopK); }
    let mut scored = Vec::with_capacity(candidates.len());
    for (id, vector) in candidates {
        scored.push((id.clone(), cosine_similarity(query, vector)?));
    }
    scored.sort_by(|a,b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    scored.truncate(top_k);
    Ok(scored)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn ranks_dense_vectors_deterministically() {
        let q = EmbeddingVector::new("mkaos-test-v1", vec![1.0, 0.0]).unwrap();
        let candidates = vec![
            ("far".to_string(), EmbeddingVector::new("mkaos-test-v1", vec![0.0, 1.0]).unwrap()),
            ("near".to_string(), EmbeddingVector::new("mkaos-test-v1", vec![0.9, 0.1]).unwrap()),
        ];
        assert_eq!(rank_by_cosine(&q, &candidates, 1).unwrap()[0].0, "near");
    }
    #[test]
    fn refuses_mixed_embedding_spaces() {
        let a = EmbeddingVector::new("encoder-a", vec![1.0, 0.0]).unwrap();
        let b = EmbeddingVector::new("encoder-b", vec![1.0, 0.0]).unwrap();
        assert_eq!(cosine_similarity(&a, &b), Err(EmbeddingError::ModelSpaceMismatch));
    }
}
