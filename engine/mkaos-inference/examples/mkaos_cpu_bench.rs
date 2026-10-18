//! Reproducible synthetic CPU benchmark for the experimental MKAOS Rust decoder.
//! Run: cargo run --release --manifest-path engine/mkaos-inference/Cargo.toml --example mkaos_cpu_bench
//! This intentionally does not load external weights or claim SmolLM2 compatibility.
use mkaos_inference::stacked_decoder::{GqaConfig, GqaDecoder, GqaDecoderWeights, GqaLayerWeights, KvCache};
use mkaos_inference::Tensor2;
use std::{env, time::{Duration, Instant}};

fn matrix(rows: usize, cols: usize, seed: usize) -> Tensor2 {
    Tensor2::new(rows, cols, (0..rows * cols)
        .map(|i| (((i.wrapping_mul(17).wrapping_add(seed * 13)) % 101) as f32 - 50.0) * 0.0005)
        .collect()).expect("valid deterministic matrix")
}
fn make_model() -> GqaDecoder {
    let (vocab, d, layers, q_heads, kv_heads, ff) = (257, 64, 2, 4, 2, 128);
    let kv_width = d / q_heads * kv_heads;
    let mut blocks = Vec::with_capacity(layers);
    for i in 0..layers {
        let seed = 11 + i * 19;
        blocks.push(GqaLayerWeights {
            q_proj: matrix(d, d, seed), k_proj: matrix(d, kv_width, seed+1),
            v_proj: matrix(d, kv_width, seed+2), o_proj: matrix(d, d, seed+3),
            input_norm: vec![1.0; d], post_attention_norm: vec![1.0; d],
            gate_proj: matrix(d, ff, seed+4), up_proj: matrix(d, ff, seed+5),
            down_proj: matrix(ff, d, seed+6),
        });
    }
    GqaDecoder::new(
        GqaConfig { query_heads:q_heads, kv_heads, rms_epsilon:1e-5, rope_theta:10000.0, max_sequence_len:512 },
        GqaDecoderWeights { token_embedding:matrix(vocab,d,3), layers:blocks,
            final_norm:vec![1.0;d], lm_head:matrix(d,vocab,9) }
    ).expect("valid deterministic benchmark model")
}
fn percentile(sorted: &[Duration], p: f64) -> Duration {
    let idx = (((sorted.len().saturating_sub(1)) as f64) * p).ceil() as usize;
    sorted[idx.min(sorted.len()-1)]
}
fn report(label: &str, values: &mut [Duration]) {
    values.sort();
    let median = percentile(values, 0.5);
    let p95 = percentile(values, 0.95);
    println!("{label}_median_ms={:.3}", median.as_secs_f64()*1000.0);
    println!("{label}_p95_ms={:.3}", p95.as_secs_f64()*1000.0);
}
fn main() {
    let args: Vec<String> = env::args().collect();
    let warmups: usize = args.get(1).and_then(|x|x.parse().ok()).unwrap_or(2);
    let repetitions: usize = args.get(2).and_then(|x|x.parse().ok()).unwrap_or(7);
    if repetitions < 3 || warmups > 100 || repetitions > 100 {
        eprintln!("usage: mkaos_cpu_bench [warmups 0..100] [repetitions 3..100]");
        std::process::exit(2);
    }
    let model = make_model();
    let prompt: Vec<usize> = (0..32).map(|i| 32 + (i % 64)).collect();
    for _ in 0..warmups {
        let mut cache = KvCache::new(2);
        let _ = model.prefill(&prompt, &mut cache).expect("warmup prefill");
        let _ = model.step(42, &mut cache).expect("warmup decode");
    }
    let mut prefill = Vec::with_capacity(repetitions);
    let mut decode_per_token = Vec::with_capacity(repetitions);
    for _ in 0..repetitions {
        let mut cache = KvCache::new(2);
        let start = Instant::now();
        let _ = model.prefill(&prompt, &mut cache).expect("benchmark prefill");
        prefill.push(start.elapsed());
        let start = Instant::now();
        for token in 0..16 {
            let _ = model.step(40 + token, &mut cache).expect("benchmark decode");
        }
        decode_per_token.push(start.elapsed() / 16);
    }
    println!("benchmark=mkaos_synthetic_gqa_cpu_v1");
    println!("weights=deterministic_synthetic_not_pretrained");
    println!("profile=release_recommended");
    println!("prompt_tokens={}", prompt.len());
    println!("decode_tokens_per_repetition=16");
    println!("warmups={warmups}");
    println!("repetitions={repetitions}");
    println!("architecture=2_layers_hidden64_ff128_qheads4_kvheads2_vocab257");
    report("prefill", &mut prefill);
    report("decode_token", &mut decode_per_token);
    let median = percentile(&decode_per_token, 0.5).as_secs_f64();
    if median > 0.0 {
        println!("decode_tokens_per_second_median={:.3}", 1.0/median);
    }
}
