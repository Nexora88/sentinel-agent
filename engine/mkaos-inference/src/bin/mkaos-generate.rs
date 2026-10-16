//! Minimal native CLI for an MKAOSW1 checkpoint produced by train_mkaos_from_scratch.py.
//! No model hub, network client, or third-party runtime is used.
use mkaos_inference::{
    checkpoint::load_checkpoint,
    generation::{generate_cached, GenerationConfig, Sampling},
    stacked_decoder::{GqaConfig, GqaDecoder},
    tokenizer::ByteTokenizer,
};
use std::{env, process};

fn usage() -> &'static str {
    "Usage: mkaos-generate --checkpoint FILE --sha256 HEX --heads N --kv-heads N --max-seq N --max-new-tokens N --prompt TEXT"
}

fn value(args: &mut impl Iterator<Item = String>, flag: &str) -> String {
    args.next().unwrap_or_else(|| {
        eprintln!("Missing value for {flag}\n{}", usage());
        process::exit(2);
    })
}

fn main() {
    let mut checkpoint = None;
    let mut expected_hash = None;
    let mut prompt = None;
    let mut heads = None;
    let mut kv_heads = None;
    let mut max_seq = None;
    let mut max_new = None;
    let mut args = env::args().skip(1);
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--checkpoint" => checkpoint = Some(value(&mut args, "--checkpoint")),
            "--sha256" => expected_hash = Some(value(&mut args, "--sha256")),
            "--prompt" => prompt = Some(value(&mut args, "--prompt")),
            "--heads" => heads = value(&mut args, "--heads").parse::<usize>().ok(),
            "--kv-heads" => kv_heads = value(&mut args, "--kv-heads").parse::<usize>().ok(),
            "--max-seq" => max_seq = value(&mut args, "--max-seq").parse::<usize>().ok(),
            "--max-new-tokens" => max_new = value(&mut args, "--max-new-tokens").parse::<usize>().ok(),
            "--help" | "-h" => { println!("{}", usage()); return; }
            other => { eprintln!("Unknown argument: {other}\n{}", usage()); process::exit(2); }
        }
    }
    let checkpoint = checkpoint.unwrap_or_else(|| { eprintln!("{}", usage()); process::exit(2) });
    let expected_hash = expected_hash.unwrap_or_else(|| { eprintln!("{}", usage()); process::exit(2) });
    let prompt = prompt.unwrap_or_else(|| { eprintln!("{}", usage()); process::exit(2) });
    let heads = heads.unwrap_or(0);
    let kv_heads = kv_heads.unwrap_or(0);
    let max_seq = max_seq.unwrap_or(0);
    let max_new = max_new.unwrap_or(0);
    let tokenizer = ByteTokenizer;
    let prompt_tokens = tokenizer.encode(&prompt);
    if prompt_tokens.is_empty() || heads == 0 || kv_heads == 0 || max_seq == 0 || max_new == 0
        || prompt_tokens.len().saturating_add(max_new) > max_seq {
        eprintln!("Invalid dimensions or token budget: prompt + max-new-tokens must not exceed max-seq.");
        process::exit(2);
    }
    let checkpoint = match load_checkpoint(checkpoint, &expected_hash, 1_073_741_824, 100_000_000) {
        Ok(cp) => cp,
        Err(err) => { eprintln!("Checkpoint rejected: {err}"); process::exit(1); }
    };
    let model = match GqaDecoder::from_checkpoint(
        GqaConfig {
            query_heads: heads,
            kv_heads,
            rms_epsilon: 1e-5,
            rope_theta: 10000.0,
            max_sequence_len: max_seq,
        },
        &checkpoint,
    ) {
        Ok(model) => model,
        Err(err) => { eprintln!("Checkpoint/model contract rejected: {err}"); process::exit(1); }
    };
    let generation = GenerationConfig {
        max_new_tokens: max_new,
        eos_token_ids: vec![ByteTokenizer::EOS_ID],
        stop_sequences: Vec::new(),
    };
    match generate_cached(&model, &prompt_tokens, &generation, Sampling::Greedy, &[]) {
        Ok(result) => match tokenizer.decode(&result.generated_tokens) {
            Ok(text) => println!("{text}"),
            Err(err) => { eprintln!("Decode failed: {err}"); process::exit(1); }
        },
        Err(err) => { eprintln!("Generation failed: {err}"); process::exit(1); }
    }
}
