//! Small deterministic sampling helpers for logits from a language-model head.
use crate::KernelError;

/// Return the highest-logit token; ties resolve to the lowest token ID.
pub fn greedy_sample(logits: &[f32]) -> Result<usize, KernelError> {
    if logits.is_empty() { return Err(KernelError::EmptyTensor); }
    if logits.iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
    let mut best = 0;
    for i in 1..logits.len() { if logits[i] > logits[best] { best = i; } }
    Ok(best)
}

/// Sample from temperature-scaled logits after retaining the top-k candidates.
/// random_unit must be finite and in [0,1); callers provide their own seeded PRNG.
pub fn sample_top_k(logits: &[f32], temperature: f32, top_k: usize, random_unit: f32) -> Result<usize, KernelError> {
    if logits.is_empty() || top_k == 0 { return Err(KernelError::InvalidConfig); }
    if !temperature.is_finite() || temperature <= 0.0 || !random_unit.is_finite() || !(0.0..1.0).contains(&random_unit) {
        return Err(KernelError::InvalidConfig);
    }
    if logits.iter().any(|x| !x.is_finite()) { return Err(KernelError::NonFiniteInput); }
    let mut ranked: Vec<(usize, f32)> = logits.iter().copied().enumerate().collect();
    ranked.sort_by(|a,b| b.1.total_cmp(&a.1).then_with(|| a.0.cmp(&b.0)));
    ranked.truncate(top_k.min(ranked.len()));
    let max = ranked[0].1 / temperature;
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
    #[test] fn rejects_nan_logits() { assert!(greedy_sample(&[f32::NAN]).is_err()); }
}