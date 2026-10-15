//! Multi-layer Llama-style decoder reference with grouped-query attention and per-layer incremental KV cache.
//! This is a tested-by-unit-tests synthetic-weight implementation; it is not yet a SmolLM2 file adapter.
use crate::{apply_rope, embed_tokens, KernelError, Tensor2};

#[derive(Debug, Clone)]
pub struct GqaLayerWeights {
    pub q_proj: Tensor2, // [hidden, query_heads * head_dim] (normally [hidden, hidden])
    pub k_proj: Tensor2, // [hidden, kv_heads * head_dim]
    pub v_proj: Tensor2, // [hidden, kv_heads * head_dim]
    pub o_proj: Tensor2, // [hidden, hidden]
    pub input_norm: Vec<f32>,
    pub post_attention_norm: Vec<f32>,
    pub gate_proj: Tensor2, // [hidden, intermediate]
    pub up_proj: Tensor2,   // [hidden, intermediate]
    pub down_proj: Tensor2, // [intermediate, hidden]
}

#[derive(Debug, Clone)]
pub struct GqaConfig {
    pub query_heads: usize,
    pub kv_heads: usize,
    pub rms_epsilon: f32,
    pub rope_theta: f32,
    pub max_sequence_len: usize,
}

#[derive(Debug, Clone)]
pub struct GqaDecoderWeights {
    pub token_embedding: Tensor2, // [vocab, hidden]
    pub layers: Vec<GqaLayerWeights>,
    pub final_norm: Vec<f32>,
    pub lm_head: Tensor2, // [hidden, vocab]
}

#[derive(Debug, Clone, Default)]
struct LayerKv {
    // Each vector stores row-major [cached_tokens, kv_heads * head_dim].
    keys: Vec<f32>,
    values: Vec<f32>,
}

#[derive(Debug, Clone, Default)]
pub struct KvCache {
    layers: Vec<LayerKv>,
    sequence_len: usize,
}
impl KvCache {
    pub fn new(layer_count: usize) -> Self {
        Self { layers: vec![LayerKv::default(); layer_count], sequence_len: 0 }
    }
    pub fn sequence_len(&self) -> usize { self.sequence_len }
    pub fn layer_count(&self) -> usize { self.layers.len() }
    pub fn clear(&mut self) {
        for layer in &mut self.layers { layer.keys.clear(); layer.values.clear(); }
        self.sequence_len = 0;
    }
}

pub struct GqaDecoder {
    pub config: GqaConfig,
    pub weights: GqaDecoderWeights,
    hidden_size: usize,
    head_dim: usize,
    kv_width: usize,
}
impl GqaDecoder {
    pub fn new(config: GqaConfig, weights: GqaDecoderWeights) -> Result<Self, KernelError> {
        let d = weights.token_embedding.cols();
        if d == 0 || config.query_heads == 0 || config.kv_heads == 0
            || config.query_heads % config.kv_heads != 0 || d % config.query_heads != 0
            || (d / config.query_heads) % 2 != 0 || weights.layers.is_empty()
            || config.max_sequence_len == 0 || !config.rms_epsilon.is_finite()
            || config.rms_epsilon <= 0.0 || !config.rope_theta.is_finite() || config.rope_theta <= 1.0
            || weights.final_norm.len() != d
            || weights.final_norm.iter().any(|x| !x.is_finite())
            || weights.lm_head.rows() != d || weights.lm_head.cols() == 0 {
            return Err(KernelError::InvalidConfig);
        }
        let head_dim = d / config.query_heads;
        let kv_width = config.kv_heads.checked_mul(head_dim).ok_or(KernelError::InvalidDimension)?;
        for layer in &weights.layers {
            if layer.q_proj.rows() != d || layer.q_proj.cols() != d
                || layer.k_proj.rows() != d || layer.k_proj.cols() != kv_width
                || layer.v_proj.rows() != d || layer.v_proj.cols() != kv_width
                || layer.o_proj.rows() != d || layer.o_proj.cols() != d
                || layer.input_norm.len() != d || layer.post_attention_norm.len() != d
                || layer.input_norm.iter().chain(&layer.post_attention_norm).any(|x| !x.is_finite())
                || layer.gate_proj.rows() != d || layer.up_proj.rows() != d
                || layer.gate_proj.cols() != layer.up_proj.cols()
                || layer.down_proj.rows() != layer.gate_proj.cols() || layer.down_proj.cols() != d {
                return Err(KernelError::InvalidConfig);
            }
        }
        if weights.token_embedding.rows() != weights.lm_head.cols() {
            return Err(KernelError::InvalidConfig);
        }
        Ok(Self { config, weights, hidden_size: d, head_dim, kv_width })
    }

    /// Consumes exactly one token and returns vocabulary logits. The KV cache is updated
    /// once per layer; previous hidden states are not recomputed.
    pub fn step(&self, token_id: usize, cache: &mut KvCache) -> Result<Vec<f32>, KernelError> {
        if cache.layers.len() != self.weights.layers.len() { return Err(KernelError::InvalidConfig); }
        if cache.sequence_len >= self.config.max_sequence_len { return Err(KernelError::InvalidConfig); }
        if cache.layers.iter().any(|l| l.keys.len() != cache.sequence_len * self.kv_width
            || l.values.len() != cache.sequence_len * self.kv_width) {
            return Err(KernelError::InvalidConfig);
        }
        let mut x = embed_tokens(&self.weights.token_embedding, &[token_id])?;
        let pos = cache.sequence_len;
        for (index, w) in self.weights.layers.iter().enumerate() {
            let n1 = norm_scale(&x, &w.input_norm, self.config.rms_epsilon)?;
            let q = apply_rope(&n1.matmul(&w.q_proj)?, self.head_dim, pos, self.config.rope_theta)?;
            let k = apply_rope(&n1.matmul(&w.k_proj)?, self.head_dim, pos, self.config.rope_theta)?;
            let v = n1.matmul(&w.v_proj)?;
            let kv = &mut cache.layers[index];
            kv.keys.extend_from_slice(k.as_slice());
            kv.values.extend_from_slice(v.as_slice());
            let mut joined = vec![0.0_f32; self.hidden_size];
            let cached_len = pos + 1;
            for q_head in 0..self.config.query_heads {
                let kv_head = q_head / (self.config.query_heads / self.config.kv_heads);
                let q_offset = q_head * self.head_dim;
                let kv_offset = kv_head * self.head_dim;
                let mut scores = Vec::with_capacity(cached_len);
                let scale = (self.head_dim as f32).sqrt().recip();
                for t in 0..cached_len {
                    let mut dot = 0.0;
                    for j in 0..self.head_dim {
                        dot += q.as_slice()[q_offset + j] * kv.keys[t * self.kv_width + kv_offset + j];
                    }
                    scores.push(dot * scale);
                }
                let max = scores.iter().copied().fold(f32::NEG_INFINITY, f32::max);
                let mut denom = 0.0_f32;
                for score in &mut scores { *score = (*score - max).exp(); denom += *score; }
                if !denom.is_finite() || denom <= 0.0 { return Err(KernelError::NonFiniteInput); }
                for (t, score) in scores.iter().enumerate() {
                    let p = *score / denom;
                    for j in 0..self.head_dim {
                        joined[q_offset + j] += p * kv.values[t * self.kv_width + kv_offset + j];
                    }
                }
            }
            let attn = Tensor2::new(1, self.hidden_size, joined)?.matmul(&w.o_proj)?;
            let residual = x.add(&attn)?;
            let n2 = norm_scale(&residual, &w.post_attention_norm, self.config.rms_epsilon)?;
            let gate = n2.matmul(&w.gate_proj)?.map(|z| z / (1.0 + (-z).exp()))?;
            let up = n2.matmul(&w.up_proj)?;
            x = residual.add(&gate.multiply(&up)?.matmul(&w.down_proj)?)?;
        }
        cache.sequence_len += 1;
        let normalized = norm_scale(&x, &self.weights.final_norm, self.config.rms_epsilon)?;
        let logits = normalized.matmul(&self.weights.lm_head)?;
        if logits.as_slice().iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
        Ok(logits.as_slice().to_vec())
    }

    /// Prefill a prompt using the same incremental path. Returns the last token's logits.
    pub fn prefill(&self, prompt: &[usize], cache: &mut KvCache) -> Result<Vec<f32>, KernelError> {
        if prompt.is_empty() { return Err(KernelError::EmptyTensor); }
        let mut logits = Vec::new();
        for &token in prompt { logits = self.step(token, cache)?; }
        Ok(logits)
    }
}

fn norm_scale(x: &Tensor2, scale: &[f32], epsilon: f32) -> Result<Tensor2, KernelError> {
    if x.cols() != scale.len() { return Err(KernelError::ShapeMismatch { expected: x.cols(), actual: scale.len() }); }
    let mut out = x.as_slice().to_vec();
    for row in out.chunks_exact_mut(x.cols()) {
        let mean_sq = row.iter().map(|v| v * v).sum::<f32>() / row.len() as f32;
        let inv = (mean_sq + epsilon).sqrt().recip();
        for (value, weight) in row.iter_mut().zip(scale) { *value *= inv * weight; }
    }
    Tensor2::new(x.rows(), x.cols(), out)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn matrix(rows: usize, cols: usize, seed: usize) -> Tensor2 {
        Tensor2::new(rows, cols, (0..rows * cols).map(|i| (((i + seed) % 13) as f32 - 6.0) * 0.015).collect()).unwrap()
    }
    fn layer(d: usize, kv_width: usize, ff: usize, seed: usize) -> GqaLayerWeights {
        GqaLayerWeights {
            q_proj: matrix(d, d, seed), k_proj: matrix(d, kv_width, seed+1),
            v_proj: matrix(d, kv_width, seed+2), o_proj: matrix(d, d, seed+3),
            input_norm: vec![1.0; d], post_attention_norm: vec![1.0; d],
            gate_proj: matrix(d, ff, seed+4), up_proj: matrix(d, ff, seed+5),
            down_proj: matrix(ff, d, seed+6),
        }
    }
    fn model() -> GqaDecoder {
        let d=8; let q_heads=4; let kv_heads=2; let kv_width=kv_heads*(d/q_heads);
        let weights=GqaDecoderWeights {
            token_embedding: matrix(17,d,1),
            layers: vec![layer(d,kv_width,12,2), layer(d,kv_width,12,11)],
            final_norm: vec![1.0;d], lm_head: matrix(d,17,8),
        };
        GqaDecoder::new(GqaConfig{query_heads:q_heads,kv_heads,rms_epsilon:1e-5,rope_theta:10000.0,max_sequence_len:64},weights).unwrap()
    }
    #[test]
    fn multi_layer_gqa_cache_advances_once_per_token() {
        let m=model(); let mut cache=KvCache::new(2);
        let first=m.step(1,&mut cache).unwrap();
        assert_eq!(first.len(),17); assert_eq!(cache.sequence_len(),1);
        assert_eq!(cache.layers[0].keys.len(),4*2);
        let _=m.step(2,&mut cache).unwrap();
        assert_eq!(cache.sequence_len(),2);
        assert_eq!(cache.layers[1].values.len(),2*4);
    }
    #[test]
    fn cached_prefill_and_step_are_finite_and_bounded() {
        let m=model(); let mut cache=KvCache::new(2);
        let logits=m.prefill(&[1,2,3],&mut cache).unwrap();
        assert_eq!(cache.sequence_len(),3); assert!(logits.iter().all(|x|x.is_finite()));
        assert!(m.step(4,&mut cache).unwrap().iter().all(|x|x.is_finite()));
        cache.clear(); assert_eq!(cache.sequence_len(),0);
    }
    #[test]
    fn rejects_cache_with_wrong_layer_count() {
        let m=model(); let mut cache=KvCache::new(1);
        assert!(m.step(1,&mut cache).is_err());
    }
}
