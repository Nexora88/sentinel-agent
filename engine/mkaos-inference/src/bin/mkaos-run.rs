//! Load a hash-pinned MKAOSW1 checkpoint and run the owned Rust decoder locally.
use mkaos_inference::{
    checkpoint::load_checkpoint,
    generation::{generate_cached, GenerationConfig, Sampling},
    stacked_decoder::{GqaConfig, GqaDecoder},
    tokenizer::ByteTokenizer,
};
use std::{path::PathBuf, time::Instant};

fn usage() {
    eprintln!("Usage: mkaos-run --checkpoint FILE --sha256 HEX --prompt TEXT [--heads N] [--kv-heads N] [--max-new-tokens N] [--max-seq-len N]");
}
fn value(args: &[String], flag: &str, default: Option<&str>) -> Result<String, String> {
    match args.iter().position(|arg| arg == flag) {
        Some(index) => args.get(index + 1).cloned().ok_or_else(|| format!("{flag} requires a value")),
        None => default.map(str::to_owned).ok_or_else(|| format!("missing required argument {flag}")),
    }
}
fn parse_usize(args: &[String], flag: &str, default: usize) -> Result<usize, String> {
    value(args, flag, Some("")).and_then(|v| if v.is_empty() { Ok(default) } else { v.parse().map_err(|_| format!("{flag} must be a positive integer")) })
}
fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--help" || a == "-h") { usage(); return; }
    let result = run(&args);
    if let Err(error) = result { eprintln!("MKAOS Rust inference error: {error}"); std::process::exit(2); }
}
fn run(args: &[String]) -> Result<(), String> {
    let checkpoint_path = PathBuf::from(value(args, "--checkpoint", None)?);
    let expected_hash = value(args, "--sha256", None)?;
    let prompt = value(args, "--prompt", None)?;
    if prompt.trim().is_empty() { return Err("--prompt cannot be empty".into()); }
    let heads = parse_usize(args, "--heads", 4)?;
    let kv_heads = parse_usize(args, "--kv-heads", 2)?;
    let max_new_tokens = parse_usize(args, "--max-new-tokens", 64)?;
    let max_sequence_len = parse_usize(args, "--max-seq-len", 2048)?;
    if heads == 0 || kv_heads == 0 || max_new_tokens == 0 || max_sequence_len == 0 {
        return Err("head counts and token limits must be positive".into());
    }
    let checkpoint = load_checkpoint(&checkpoint_path, &expected_hash, 2 * 1024 * 1024 * 1024, 100_000_000)
        .map_err(|e| e.to_string())?;
    let config = GqaConfig {
        query_heads: heads,
        kv_heads,
        rms_epsilon: 1e-5,
        rope_theta: 10_000.0,
        max_sequence_len,
    };
    let model = GqaDecoder::from_checkpoint(config, &checkpoint)
        .map_err(|e| format!("checkpoint does not match the owned decoder contract: {e}"))?;
    let tokenizer = ByteTokenizer;
    let prompt_tokens = tokenizer.encode(&prompt);
    if prompt_tokens.len() >= max_sequence_len {
        return Err(format!("prompt has {} byte tokens; max sequence length is {max_sequence_len}", prompt_tokens.len()));
    }
    let started = Instant::now();
    let result = generate_cached(
        &model,
        &prompt_tokens,
        &GenerationConfig {
            max_new_tokens: max_new_tokens.min(max_sequence_len - prompt_tokens.len()),
            eos_token_ids: vec![ByteTokenizer::EOS_ID],
            stop_sequences: Vec::new(),
        },
        Sampling::Greedy,
        &[],
    ).map_err(|e| e.to_string())?;
    let elapsed = started.elapsed();
    let text = tokenizer.decode(&result.generated_tokens).map_err(|e| e.to_string())?;
    println!("{text}");
    eprintln!("checkpoint_sha256={}", checkpoint.sha256);
    eprintln!("prompt_byte_tokens={}", result.prompt_tokens.len());
    eprintln!("generated_tokens={}", result.generated_tokens.len());
    eprintln!("stopped_on_eos={}", result.stopped_on_eos);
    eprintln!("elapsed_ms={}", elapsed.as_millis());
    if elapsed.as_secs_f64() > 0.0 { eprintln!("tokens_per_second={:.3}", result.generated_tokens.len() as f64 / elapsed.as_secs_f64()); }
    eprintln!("decoder=owned-rust-gqa-kv-cache");
    Ok(())
}
