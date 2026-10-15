//! Full-prefix generation driver. A model implementation supplies next-token logits.
use crate::{sampling, KernelError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationConfig {
    pub max_new_tokens: usize,
    pub eos_token_ids: Vec<usize>,
    pub stop_sequences: Vec<Vec<usize>>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Sampling {
    Greedy,
    TopK { k: usize, temperature_milli: u32 },
    TopP { p_milli: u16, temperature_milli: u32 },
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationResult {
    pub prompt_tokens: Vec<usize>,
    pub generated_tokens: Vec<usize>,
    pub stopped_on_eos: bool,
    pub stopped_on_sequence: bool,
}
pub trait LogitsProvider {
    fn next_logits(&mut self, prefix: &[usize]) -> Result<Vec<f32>, KernelError>;
}

/// Reference loop recomputes the whole prefix each step. It is not KV-cache decoding.
pub fn generate<P: LogitsProvider>(
    provider: &mut P,
    prompt: &[usize],
    config: &GenerationConfig,
    sampling_mode: Sampling,
    random_draws: &[f32],
) -> Result<GenerationResult, KernelError> {
    if prompt.is_empty() || config.max_new_tokens == 0 { return Err(KernelError::InvalidConfig); }
    if matches!(sampling_mode, Sampling::TopK { k: 0, .. }) { return Err(KernelError::InvalidConfig); }
    if matches!(sampling_mode, Sampling::TopK { temperature_milli: 0, .. } | Sampling::TopP { temperature_milli: 0, .. }) {
        return Err(KernelError::InvalidConfig);
    }
    if matches!(sampling_mode, Sampling::TopP { p_milli: 0, .. } | Sampling::TopP { p_milli: 1001.., .. }) {
        return Err(KernelError::InvalidConfig);
    }
    if !matches!(sampling_mode, Sampling::Greedy) && random_draws.len() < config.max_new_tokens {
        return Err(KernelError::InvalidConfig);
    }
    if config.stop_sequences.iter().any(Vec::is_empty) { return Err(KernelError::InvalidConfig); }

    let mut prefix = prompt.to_vec();
    let mut generated = Vec::new();
    let mut stopped_on_eos = false;
    let mut stopped_on_sequence = false;
    for step in 0..config.max_new_tokens {
        let logits = provider.next_logits(&prefix)?;
        let token = match sampling_mode {
            Sampling::Greedy => sampling::greedy_sample(&logits)?,
            Sampling::TopK { k, temperature_milli } =>
                sampling::sample_top_k(&logits, temperature_milli as f32 / 1000.0, k, random_draws[step])?,
            Sampling::TopP { p_milli, temperature_milli } =>
                sampling::sample_top_p(&logits, temperature_milli as f32 / 1000.0, p_milli as f32 / 1000.0, random_draws[step])?,
        };
        prefix.push(token);
        if config.eos_token_ids.contains(&token) {
            stopped_on_eos = true;
            break;
        }
        generated.push(token);
        if config.stop_sequences.iter().any(|seq| generated.ends_with(seq)) {
            stopped_on_sequence = true;
            break;
        }
    }
    Ok(GenerationResult { prompt_tokens: prompt.to_vec(), generated_tokens: generated, stopped_on_eos, stopped_on_sequence })
}


/// Generate directly with the multi-layer decoder's incremental per-layer KV cache.
/// The prompt is prefetched once; after each emitted token only that token is evaluated.
pub fn generate_cached(
    model: &crate::stacked_decoder::GqaDecoder,
    prompt: &[usize],
    config: &GenerationConfig,
    sampling_mode: Sampling,
    random_draws: &[f32],
) -> Result<GenerationResult, KernelError> {
    if prompt.is_empty() || config.max_new_tokens == 0 { return Err(KernelError::InvalidConfig); }
    if matches!(sampling_mode, Sampling::TopK { k: 0, .. }) { return Err(KernelError::InvalidConfig); }
    if matches!(sampling_mode, Sampling::TopK { temperature_milli: 0, .. } | Sampling::TopP { temperature_milli: 0, .. }) {
        return Err(KernelError::InvalidConfig);
    }
    if matches!(sampling_mode, Sampling::TopP { p_milli: 0, .. } | Sampling::TopP { p_milli: 1001.., .. }) {
        return Err(KernelError::InvalidConfig);
    }
    if !matches!(sampling_mode, Sampling::Greedy) && random_draws.len() < config.max_new_tokens {
        return Err(KernelError::InvalidConfig);
    }
    if config.stop_sequences.iter().any(Vec::is_empty) { return Err(KernelError::InvalidConfig); }

    let mut cache = crate::stacked_decoder::KvCache::new(model.weights.layers.len());
    let mut logits = model.prefill(prompt, &mut cache)?;
    let mut generated = Vec::new();
    let mut stopped_on_eos = false;
    let mut stopped_on_sequence = false;
    for step in 0..config.max_new_tokens {
        let token = match sampling_mode {
            Sampling::Greedy => sampling::greedy_sample(&logits)?,
            Sampling::TopK { k, temperature_milli } =>
                sampling::sample_top_k(&logits, temperature_milli as f32 / 1000.0, k, random_draws[step])?,
            Sampling::TopP { p_milli, temperature_milli } =>
                sampling::sample_top_p(&logits, temperature_milli as f32 / 1000.0, p_milli as f32 / 1000.0, random_draws[step])?,
        };
        if config.eos_token_ids.contains(&token) {
            stopped_on_eos = true;
            break;
        }
        generated.push(token);
        if config.stop_sequences.iter().any(|seq| generated.ends_with(seq)) {
            stopped_on_sequence = true;
            break;
        }
        if step + 1 < config.max_new_tokens {
            logits = model.step(token, &mut cache)?;
        }
    }
    Ok(GenerationResult {
        prompt_tokens: prompt.to_vec(), generated_tokens: generated,
        stopped_on_eos, stopped_on_sequence,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    struct FixedModel { logits: Vec<Vec<f32>>, calls: usize }
    impl LogitsProvider for FixedModel {
        fn next_logits(&mut self, _: &[usize]) -> Result<Vec<f32>, KernelError> {
            let out = self.logits[self.calls.min(self.logits.len()-1)].clone();
            self.calls += 1;
            Ok(out)
        }
    }
    #[test] fn stops_at_eos_and_does_not_emit_eos() {
        let mut m = FixedModel { logits: vec![vec![0., 2., 0.], vec![0., 0., 3.]], calls: 0 };
        let cfg = GenerationConfig { max_new_tokens: 5, eos_token_ids: vec![2], stop_sequences: vec![] };
        let out = generate(&mut m, &[0], &cfg, Sampling::Greedy, &[]).unwrap();
        assert_eq!(out.generated_tokens, vec![1]); assert!(out.stopped_on_eos);
    }
    #[test] fn stops_on_suffix_sequence() {
        let mut m = FixedModel { logits: vec![vec![0., 2., 0.], vec![0., 0., 3.]], calls: 0 };
        let cfg = GenerationConfig { max_new_tokens: 5, eos_token_ids: vec![], stop_sequences: vec![vec![1,2]] };
        let out = generate(&mut m, &[0], &cfg, Sampling::Greedy, &[]).unwrap();
        assert_eq!(out.generated_tokens, vec![1,2]); assert!(out.stopped_on_sequence);
    }
}
