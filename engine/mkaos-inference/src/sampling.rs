//! Deterministic sampling primitives for language-model logits.
use crate::KernelError;

/// Apply the standard repetition penalty once per previously generated token.
/// A penalty of 1.0 disables the operation. Prompt tokens are deliberately not
/// included by the CLI so short answers do not suppress common prompt vocabulary.
pub fn apply_repetition_penalty(
    logits: &mut [f32],
    previous_tokens: &[usize],
    penalty: f32,
) -> Result<(), KernelError> {
    if !penalty.is_finite() || !(1.0..=2.0).contains(&penalty) {
        return Err(KernelError::InvalidConfig);
    }
    if logits.is_empty() {
        return Err(KernelError::EmptyTensor);
    }
    if logits.iter().any(|x| !x.is_finite()) {
        return Err(KernelError::NonFiniteInput);
    }
    if previous_tokens.iter().any(|&token| token >= logits.len()) {
        return Err(KernelError::InvalidConfig);
    }
    if penalty == 1.0 {
        return Ok(());
    }
    // Deduplicate only the short generated-token list; avoid allocating a
    // vocabulary-sized bitmap on every decode step.
    let mut seen_tokens = previous_tokens.to_vec();
    seen_tokens.sort_unstable();
    seen_tokens.dedup();
    for token in seen_tokens {
        if logits[token] > 0.0 {
            logits[token] /= penalty;
        } else {
            logits[token] *= penalty;
        }
    }
    Ok(())
}

pub fn greedy_sample(logits: &[f32]) -> Result<usize, KernelError> {
    if logits.is_empty() { return Err(KernelError::EmptyTensor); }
    if logits.iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
    let mut best = 0;
    for i in 1..logits.len() { if logits[i] > logits[best] { best = i; } }
    Ok(best)
}

pub fn sample_top_k(logits: &[f32], temperature: f32, top_k: usize, random_unit: f32) -> Result<usize, KernelError> {
    if logits.is_empty() || top_k == 0 { return Err(KernelError::InvalidConfig); }
    if !temperature.is_finite() || temperature <= 0.0 || !random_unit.is_finite() || !(0.0..1.0).contains(&random_unit) {
        return Err(KernelError::InvalidConfig);
    }
    if logits.iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
    let mut ranked: Vec<(usize, f32)> = logits.iter().copied().enumerate().collect();
    ranked.sort_by(|a,b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    ranked.truncate(top_k.min(ranked.len()));
    sample_ranked(ranked, temperature, random_unit)
}

/// Nucleus sampling retains the smallest descending-probability prefix reaching p.
pub fn sample_top_p(logits: &[f32], temperature: f32, p: f32, random_unit: f32) -> Result<usize, KernelError> {
    if logits.is_empty() || !temperature.is_finite() || temperature <= 0.0
        || !p.is_finite() || p <= 0.0 || p > 1.0
        || !random_unit.is_finite() || !(0.0..1.0).contains(&random_unit) {
        return Err(KernelError::InvalidConfig);
    }
    if logits.iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
    let mut ranked: Vec<(usize, f32)> = logits.iter().copied().enumerate().collect();
    ranked.sort_by(|a,b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    let max = ranked[0].1 / temperature;
    let weights: Vec<f32> = ranked.iter().map(|(_,v)| (v / temperature - max).exp()).collect();
    let total: f32 = weights.iter().sum();
    if !total.is_finite() || total <= 0.0 { return Err(KernelError::NonFiniteInput); }
    let mut cumulative = 0.0;
    let mut keep = 0;
    for weight in &weights {
        cumulative += *weight / total;
        keep += 1;
        if cumulative >= p { break; }
    }
    ranked.truncate(keep);
    sample_ranked(ranked, temperature, random_unit)
}

fn sample_ranked(ranked: Vec<(usize, f32)>, temperature: f32, random_unit: f32) -> Result<usize, KernelError> {
    let max = ranked.first().ok_or(KernelError::EmptyTensor)?.1 / temperature;
    let weights: Vec<f32> = ranked.iter().map(|(_,v)| (v / temperature - max).exp()).collect();
    let total: f32 = weights.iter().sum();
    if !total.is_finite() || total <= 0.0 { return Err(KernelError::NonFiniteInput); }
    let target = random_unit * total;
    let mut cumulative = 0.0;
    for ((id,_), weight) in ranked.iter().zip(weights) {
        cumulative += weight;
        if target < cumulative { return Ok(*id); }
    }
    Ok(ranked[0].0)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn greedy_ties_choose_lowest_id() { assert_eq!(greedy_sample(&[1.,3.,3.]).unwrap(),1); }
    #[test] fn top_k_never_returns_outside_candidate_set() {
        for r in [0.0,0.2,0.8,0.999] { assert!([1,2].contains(&sample_top_k(&[0.,2.,1.,-1.],1.,2,r).unwrap())); }
    }
    #[test] fn top_p_is_deterministic_and_validates_threshold() {
        assert_eq!(sample_top_p(&[3.,2.,1.],1.,1.,0.).unwrap(),0);
        assert!(sample_top_p(&[3.,2.,1.],1.,0.0,0.).is_err());
    }
    #[test] fn top_p_nucleus_excludes_low_probability_tail() {
        for r in [0.0, 0.2, 0.7, 0.999] {
            assert!([0,1].contains(&sample_top_p(&[10.,9.,-20.],1.,0.9,r).unwrap()));
        }
    }
    #[test] fn rejects_nan_logits() { assert!(greedy_sample(&[f32::NAN]).is_err()); }
    #[test] fn repetition_penalty_suppresses_positive_repeated_token() {
        let mut logits = [4.0, 3.0, -2.0];
        apply_repetition_penalty(&mut logits, &[0, 0, 2], 1.2).unwrap();
        assert!((logits[0] - (4.0 / 1.2)).abs() < 1e-6);
        assert_eq!(logits[1], 3.0);
        assert_eq!(logits[2], -2.4);
    }
    #[test] fn repetition_penalty_validates_bounds_and_token_ids() {
        assert!(apply_repetition_penalty(&mut [1.0, 2.0], &[2], 1.1).is_err());
        assert!(apply_repetition_penalty(&mut [1.0], &[0], 0.9).is_err());
        assert!(apply_repetition_penalty(&mut [1.0], &[0], f32::NAN).is_err());
    }
}
