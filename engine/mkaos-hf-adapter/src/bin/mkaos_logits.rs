use mkaos_hf_adapter::model_loader::load_smollm2;
use std::{env, process};

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 3 {
        eprintln!("usage: mkaos_logits <config.json> <model.safetensors> <comma-separated-token-ids>");
        process::exit(2);
    }
    let ids: Result<Vec<usize>, _> = args[2].split(',').map(str::parse).collect();
    let ids = match ids { Ok(ids) if !ids.is_empty() => ids, _ => { eprintln!("invalid/empty token IDs"); process::exit(2); } };
    let model = match load_smollm2(&args[0], &args[1]) {
        Ok(model) => model,
        Err(error) => { eprintln!("model load failed: {error}"); process::exit(1); }
    };
    let mut cache = mkaos_inference::stacked_decoder::KvCache::new(model.weights.layers.len());
    match model.prefill(&ids, &mut cache) {
        Ok(logits) => println!("{}", serde_json::to_string(&logits).expect("finite logits serialize")),
        Err(error) => { eprintln!("inference failed: {error}"); process::exit(1); }
    }
}
