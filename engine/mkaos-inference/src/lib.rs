//! MKAOS: dependency-free, auditable CPU inference primitives.
//! Reference implementation for small models, not a fast production runtime.
//! Supports one decoder layer and one token sequence per call. No tokenizer,
//! checkpoint loader, batching, KV cache, quantization or GPU backend yet.
#![forbid(unsafe_code)]
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum KernelError {
    EmptyTensor, ShapeMismatch { expected: usize, actual: usize }, InvalidDimension,
    NonFiniteInput, InvalidToken { token: usize, vocab_size: usize }, InvalidConfig,
}
impl fmt::Display for KernelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyTensor => write!(f, "tensor must not be empty"),
            Self::ShapeMismatch { expected, actual } => write!(f, "shape mismatch: expected {expected}, got {actual}"),
            Self::InvalidDimension => write!(f, "dimensions must be non-zero"),
            Self::NonFiniteInput => write!(f, "input contains NaN or infinity"),
            Self::InvalidToken { token, vocab_size } => write!(f, "token {token} is outside vocabulary size {vocab_size}"),
            Self::InvalidConfig => write!(f, "invalid decoder configuration or weight shape"),
        }
    }
}
impl std::error::Error for KernelError {}

#[derive(Debug, Clone, PartialEq)]
pub struct Tensor2 { rows: usize, cols: usize, data: Vec<f32> }
impl Tensor2 {
    pub fn new(rows: usize, cols: usize, data: Vec<f32>) -> Result<Self, KernelError> {
        if rows == 0 || cols == 0 { return Err(KernelError::InvalidDimension); }
        let expected = rows.checked_mul(cols).ok_or(KernelError::InvalidDimension)?;
        if data.is_empty() { return Err(KernelError::EmptyTensor); }
        if data.len() != expected { return Err(KernelError::ShapeMismatch { expected, actual: data.len() }); }
        if data.iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
        Ok(Self { rows, cols, data })
    }
    pub fn rows(&self) -> usize { self.rows }
    pub fn cols(&self) -> usize { self.cols }
    pub fn as_slice(&self) -> &[f32] { &self.data }
    pub fn transpose(&self) -> Result<Self, KernelError> {
        let mut out = vec![0.0; self.data.len()];
        for r in 0..self.rows { for c in 0..self.cols { out[c * self.rows + r] = self.data[r * self.cols + c]; } }
        Self::new(self.cols, self.rows, out)
    }
    pub fn scale(&self, factor: f32) -> Result<Self, KernelError> {
        if !factor.is_finite() { return Err(KernelError::NonFiniteInput); }
        Self::new(self.rows, self.cols, self.data.iter().map(|x| x * factor).collect())
    }
    pub fn matmul(&self, rhs: &Self) -> Result<Self, KernelError> {
        if self.cols != rhs.rows { return Err(KernelError::ShapeMismatch { expected: self.cols, actual: rhs.rows }); }
        let count = self.rows.checked_mul(rhs.cols).ok_or(KernelError::InvalidDimension)?;
        let mut out = vec![0.0_f32; count];
        for i in 0..self.rows { for k in 0..self.cols {
            let a = self.data[i * self.cols + k];
            for j in 0..rhs.cols { out[i * rhs.cols + j] += a * rhs.data[k * rhs.cols + j]; }
        }}
        Self::new(self.rows, rhs.cols, out)
    }
    pub fn softmax_rows(&self) -> Result<Self, KernelError> {
        let mut out = self.data.clone();
        for row in out.chunks_exact_mut(self.cols) {
            let max = row.iter().copied().fold(f32::NEG_INFINITY, f32::max);
            let mut sum = 0.0;
            for x in row.iter_mut() { *x = (*x - max).exp(); sum += *x; }
            if !sum.is_finite() || sum <= 0.0 { return Err(KernelError::NonFiniteInput); }
            for x in row.iter_mut() { *x /= sum; }
        }
        Self::new(self.rows, self.cols, out)
    }
    pub fn rms_norm_rows(&self, epsilon: f32) -> Result<Self, KernelError> {
        if !epsilon.is_finite() || epsilon <= 0.0 { return Err(KernelError::InvalidConfig); }
        let mut out = self.data.clone();
        for row in out.chunks_exact_mut(self.cols) {
            let mean_sq = row.iter().map(|x| x * x).sum::<f32>() / self.cols as f32;
            let inv = (mean_sq + epsilon).sqrt().recip();
            for x in row.iter_mut() { *x *= inv; }
        }
        Self::new(self.rows, self.cols, out)
    }
    fn add(&self, rhs: &Self) -> Result<Self, KernelError> {
        if self.rows != rhs.rows || self.cols != rhs.cols { return Err(KernelError::ShapeMismatch { expected: self.data.len(), actual: rhs.data.len() }); }
        Self::new(self.rows, self.cols, self.data.iter().zip(&rhs.data).map(|(a,b)| a+b).collect())
    }
    fn multiply(&self, rhs: &Self) -> Result<Self, KernelError> {
        if self.rows != rhs.rows || self.cols != rhs.cols { return Err(KernelError::ShapeMismatch { expected: self.data.len(), actual: rhs.data.len() }); }
        Self::new(self.rows, self.cols, self.data.iter().zip(&rhs.data).map(|(a,b)| a*b).collect())
    }
    fn map(&self, f: impl Fn(f32) -> f32) -> Result<Self, KernelError> {
        Self::new(self.rows, self.cols, self.data.iter().map(|x| f(*x)).collect())
    }
    fn apply_scale(&self, scale: &[f32]) -> Result<Self, KernelError> {
        if scale.len() != self.cols { return Err(KernelError::ShapeMismatch { expected: self.cols, actual: scale.len() }); }
        let mut out = self.data.clone();
        for row in out.chunks_exact_mut(self.cols) { for (x, s) in row.iter_mut().zip(scale) { *x *= *s; } }
        Self::new(self.rows, self.cols, out)
    }
}

/// Stable causal attention: softmax(Q K^T / sqrt(d_k)) V, with future keys masked.
pub fn causal_scaled_dot_product_attention(q: &Tensor2, k: &Tensor2, v: &Tensor2) -> Result<Tensor2, KernelError> {
    if q.cols != k.cols { return Err(KernelError::ShapeMismatch { expected: q.cols, actual: k.cols }); }
    if k.rows != v.rows { return Err(KernelError::ShapeMismatch { expected: k.rows, actual: v.rows }); }
    if q.rows > k.rows { return Err(KernelError::InvalidConfig); }
    let scores = q.matmul(&k.transpose()?)?.scale((q.cols as f32).sqrt().recip())?;
    let mut out = vec![0.0_f32; q.rows.checked_mul(v.cols).ok_or(KernelError::InvalidDimension)?];
    for i in 0..q.rows {
        let row = &scores.data[i * k.rows..(i + 1) * k.rows];
        let max = row[..=i].iter().copied().fold(f32::NEG_INFINITY, f32::max);
        let exps: Vec<f32> = row[..=i].iter().map(|s| (*s - max).exp()).collect();
        let denom: f32 = exps.iter().sum();
        if !denom.is_finite() || denom <= 0.0 { return Err(KernelError::NonFiniteInput); }
        for j in 0..=i {
            let p = exps[j] / denom;
            for d in 0..v.cols { out[i * v.cols + d] += p * v.data[j * v.cols + d]; }
        }
    }
    Tensor2::new(q.rows, v.cols, out)
}

/// Rotary position embeddings on adjacent channel pairs, independently per attention head.
pub fn apply_rope(x: &Tensor2, head_dim: usize, start_position: usize, theta: f32) -> Result<Tensor2, KernelError> {
    if head_dim == 0 || head_dim % 2 != 0 || x.cols % head_dim != 0 || !theta.is_finite() || theta <= 1.0 {
        return Err(KernelError::InvalidConfig);
    }
    let heads = x.cols / head_dim;
    let mut out = x.data.clone();
    for pos in 0..x.rows {
        let absolute_pos = start_position.checked_add(pos).ok_or(KernelError::InvalidDimension)?;
        for h in 0..heads { for pair in 0..(head_dim / 2) {
            let i0 = pos * x.cols + h * head_dim + pair * 2;
            let i1 = i0 + 1;
            let freq = 1.0 / theta.powf((2 * pair) as f32 / head_dim as f32);
            let (sin, cos) = ((absolute_pos as f32 * freq).sin(), (absolute_pos as f32 * freq).cos());
            let a = x.data[i0]; let b = x.data[i1];
            out[i0] = a * cos - b * sin;
            out[i1] = a * sin + b * cos;
        }}
    }
    Tensor2::new(x.rows, x.cols, out)
}

/// Token embedding lookup. Table layout is [vocabulary, hidden_size].
pub fn embed_tokens(table: &Tensor2, token_ids: &[usize]) -> Result<Tensor2, KernelError> {
    if token_ids.is_empty() { return Err(KernelError::EmptyTensor); }
    let capacity = token_ids.len().checked_mul(table.cols).ok_or(KernelError::InvalidDimension)?;
    let mut out = Vec::with_capacity(capacity);
    for &id in token_ids {
        if id >= table.rows { return Err(KernelError::InvalidToken { token: id, vocab_size: table.rows }); }
        out.extend_from_slice(&table.data[id * table.cols..(id + 1) * table.cols]);
    }
    Tensor2::new(token_ids.len(), table.cols, out)
}
fn linear(x: &Tensor2, w: &Tensor2) -> Result<Tensor2, KernelError> { x.matmul(w) }

/// One pre-norm, multi-head Transformer decoder block's weights.
/// Layouts: embedding [vocab,d], q/k/v/o [d,d], gate/up [d,ff], down [ff,d].
#[derive(Debug, Clone)]
pub struct DecoderWeights {
    pub token_embedding: Tensor2,
    pub q_proj: Tensor2, pub k_proj: Tensor2, pub v_proj: Tensor2, pub o_proj: Tensor2,
    pub norm1_scale: Vec<f32>, pub norm2_scale: Vec<f32>,
    pub gate_proj: Tensor2, pub up_proj: Tensor2, pub down_proj: Tensor2,
}
#[derive(Debug, Clone, Copy)]
pub struct DecoderConfig { pub num_heads: usize, pub rms_epsilon: f32, pub rope_theta: f32 }

/// Reference CPU decoder: embeddings -> RoPE multi-head causal attention -> residual,
/// RMSNorm -> SwiGLU feed-forward -> residual. No external crates required.
pub struct TransformerDecoder { pub config: DecoderConfig, pub weights: DecoderWeights }
impl TransformerDecoder {
    pub fn new(config: DecoderConfig, weights: DecoderWeights) -> Result<Self, KernelError> {
        let d = weights.token_embedding.cols;
        if config.num_heads == 0 || d % config.num_heads != 0 || (d / config.num_heads) % 2 != 0
            || !config.rms_epsilon.is_finite() || config.rms_epsilon <= 0.0
            || !config.rope_theta.is_finite() || config.rope_theta <= 1.0
            || weights.q_proj.rows != d || weights.q_proj.cols != d
            || weights.k_proj.rows != d || weights.k_proj.cols != d
            || weights.v_proj.rows != d || weights.v_proj.cols != d
            || weights.o_proj.rows != d || weights.o_proj.cols != d
            || weights.norm1_scale.len() != d || weights.norm2_scale.len() != d
            || weights.norm1_scale.iter().chain(&weights.norm2_scale).any(|x| !x.is_finite())
            || weights.gate_proj.rows != d || weights.up_proj.rows != d
            || weights.gate_proj.cols != weights.up_proj.cols
            || weights.down_proj.rows != weights.gate_proj.cols || weights.down_proj.cols != d {
            return Err(KernelError::InvalidConfig);
        }
        Ok(Self { config, weights })
    }
    /// Forward one non-empty token sequence; returns hidden states [sequence, hidden_size].
    pub fn forward(&self, token_ids: &[usize]) -> Result<Tensor2, KernelError> {
        let w = &self.weights;
        let d = w.token_embedding.cols;
        let seq = token_ids.len();
        let head_dim = d / self.config.num_heads;
        let x = embed_tokens(&w.token_embedding, token_ids)?;
        let n1 = x.rms_norm_rows(self.config.rms_epsilon)?.apply_scale(&w.norm1_scale)?;
        let q = apply_rope(&linear(&n1, &w.q_proj)?, head_dim, 0, self.config.rope_theta)?;
        let k = apply_rope(&linear(&n1, &w.k_proj)?, head_dim, 0, self.config.rope_theta)?;
        let v = linear(&n1, &w.v_proj)?;
        let mut joined = vec![0.0_f32; seq.checked_mul(d).ok_or(KernelError::InvalidDimension)?];
        for h in 0..self.config.num_heads {
            let start = h * head_dim;
            let mut qh = Vec::with_capacity(seq * head_dim);
            let mut kh = Vec::with_capacity(seq * head_dim);
            let mut vh = Vec::with_capacity(seq * head_dim);
            for row in 0..seq {
                qh.extend_from_slice(&q.data[row*d+start..row*d+start+head_dim]);
                kh.extend_from_slice(&k.data[row*d+start..row*d+start+head_dim]);
                vh.extend_from_slice(&v.data[row*d+start..row*d+start+head_dim]);
            }
            let qh = Tensor2::new(seq, head_dim, qh)?;
            let kh = Tensor2::new(seq, head_dim, kh)?;
            let vh = Tensor2::new(seq, head_dim, vh)?;
            let oh = causal_scaled_dot_product_attention(&qh, &kh, &vh)?;
            for row in 0..seq {
                joined[row*d+start..row*d+start+head_dim].copy_from_slice(&oh.data[row*head_dim..(row+1)*head_dim]);
            }
        }
        let attn = Tensor2::new(seq, d, joined)?.matmul(&w.o_proj)?;
        let residual = x.add(&attn)?;
        let n2 = residual.rms_norm_rows(self.config.rms_epsilon)?.apply_scale(&w.norm2_scale)?;
        let gate = linear(&n2, &w.gate_proj)?.map(|z| z / (1.0 + (-z).exp()))?;
        let up = linear(&n2, &w.up_proj)?;
        let mlp = gate.multiply(&up)?.matmul(&w.down_proj)?;
        residual.add(&mlp)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn matmul_and_transpose() {
        let a=Tensor2::new(2,2,vec![1.,2.,3.,4.]).unwrap();
        let b=Tensor2::new(2,1,vec![2.,1.]).unwrap();
        assert_eq!(a.matmul(&b).unwrap().as_slice(), &[4.,10.]);
        assert_eq!(a.transpose().unwrap().as_slice(), &[1.,3.,2.,4.]);
    }
    #[test] fn softmax_rows_sum_to_one() {
        let x=Tensor2::new(2,3,vec![1000.,1001.,999.,1.,1.,1.]).unwrap();
        for row in x.softmax_rows().unwrap().as_slice().chunks_exact(3) { assert!((row.iter().sum::<f32>()-1.).abs()<1e-5); }
    }
    #[test] fn embeddings_lookup_and_reject_bad_id() {
        let e=Tensor2::new(3,2,vec![1.,2.,3.,4.,5.,6.]).unwrap();
        assert_eq!(embed_tokens(&e,&[2,0]).unwrap().as_slice(), &[5.,6.,1.,2.]);
        assert!(embed_tokens(&e,&[3]).is_err());
    }
    #[test] fn rope_preserves_norm_and_rotates_nonzero_position() {
        let x=Tensor2::new(2,2,vec![1.,0.,1.,0.]).unwrap();
        let y=apply_rope(&x,2,0,10000.).unwrap();
        assert_eq!(&y.as_slice()[0..2], &[1.,0.]);
        assert!((y.as_slice()[2].powi(2)+y.as_slice()[3].powi(2)-1.).abs()<1e-5);
        assert!(y.as_slice()[3] != 0.);
    }
    #[test] fn causal_attention_cannot_see_future_values() {
        let q=Tensor2::new(3,2,vec![1.,0.,1.,0.,1.,0.]).unwrap();
        let k=Tensor2::new(3,2,vec![1.,0.,1.,0.,1.,0.]).unwrap();
        let v1=Tensor2::new(3,1,vec![2.,4.,6.]).unwrap();
        let v2=Tensor2::new(3,1,vec![2.,4.,999.]).unwrap();
        let a=causal_scaled_dot_product_attention(&q,&k,&v1).unwrap();
        let b=causal_scaled_dot_product_attention(&q,&k,&v2).unwrap();
        assert_eq!(a.as_slice()[0],b.as_slice()[0]); assert_eq!(a.as_slice()[1],b.as_slice()[1]);
        assert_ne!(a.as_slice()[2],b.as_slice()[2]);
    }
    fn identity(n:usize)->Tensor2 { let mut d=vec![0.;n*n]; for i in 0..n { d[i*n+i]=1.; } Tensor2::new(n,n,d).unwrap() }
    #[test] fn decoder_layer_runs_end_to_end() {
        let d=4; let ff=6;
        let weights=DecoderWeights {
            token_embedding:Tensor2::new(5,d,(0..5*d).map(|i|(i as f32+1.)/20.).collect()).unwrap(),
            q_proj:identity(d), k_proj:identity(d), v_proj:identity(d), o_proj:identity(d),
            norm1_scale:vec![1.;d], norm2_scale:vec![1.;d],
            gate_proj:Tensor2::new(d,ff,vec![0.05;d*ff]).unwrap(),
            up_proj:Tensor2::new(d,ff,vec![0.04;d*ff]).unwrap(),
            down_proj:Tensor2::new(ff,d,vec![0.03;ff*d]).unwrap(),
        };
        let model=TransformerDecoder::new(DecoderConfig{num_heads:2,rms_epsilon:1e-5,rope_theta:10000.},weights).unwrap();
        let y=model.forward(&[1,2,3]).unwrap();
        assert_eq!((y.rows(),y.cols()),(3,d)); assert!(y.as_slice().iter().all(|v|v.is_finite()));
    }
    #[test] fn rejects_invalid_tensor_values() { assert_eq!(Tensor2::new(1,1,vec![f32::NAN]).unwrap_err(),KernelError::NonFiniteInput); }
}
