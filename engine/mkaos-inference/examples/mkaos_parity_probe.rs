use mkaos_inference::{checkpoint::load_checkpoint, stacked_decoder::{GqaConfig, GqaDecoder}};
use std::{env, process};

fn main() {
    if let Err(error) = run() {
        eprintln!("parity probe failed: {error}");
        process::exit(2);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 8 {
        return Err("usage: mkaos_parity_probe <weights> <sha256> <max_seq> <query_heads> <kv_heads> <prefix_csv> <epsilon>".into());
    }
    let path = &args[1];
    let expected_hash = &args[2];
    let max_sequence_len: usize = args[3].parse()?;
    let query_heads: usize = args[4].parse()?;
    let kv_heads: usize = args[5].parse()?;
    let prefix: Vec<usize> = args[6].split(',').map(str::parse).collect::<Result<_, _>>()?;
    let rms_epsilon: f32 = args[7].parse()?;
    let checkpoint = load_checkpoint(path, expected_hash, 256 * 1024 * 1024, 100_000_000)?;
    let decoder = GqaDecoder::from_checkpoint(GqaConfig {
        query_heads, kv_heads, rms_epsilon, rope_theta: 10_000.0, max_sequence_len,
    }, &checkpoint)?;
    let logits = decoder.logits_for_prefix_reference(&prefix)?;
    print!("[");
    for (i, value) in logits.iter().enumerate() {
        if i > 0 { print!(","); }
        print!("{:.9}", value);
    }
    println!("]");
    Ok(())
}
