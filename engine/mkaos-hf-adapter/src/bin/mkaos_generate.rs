use mkaos_hf_adapter::{model_loader::load_smollm2, HuggingFaceTokenizer, ChatMessage};
use mkaos_inference::{sampling, stacked_decoder::KvCache};
use serde_json::{json, Value};
use std::{env, fs, process, time::Instant};

fn token_text(value: &Value) -> Option<&str> {
    value.as_str().or_else(|| value.get("content").and_then(Value::as_str))
}
fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 3 {
        eprintln!("usage: mkaos_generate <model-dir> <prompt> <max-new-tokens>");
        process::exit(2);
    }
    let model_dir = &args[0];
    let prompt = &args[1];
    let max_new: usize = args[2].parse().unwrap_or(0);
    if max_new == 0 { eprintln!("max-new-tokens must be positive"); process::exit(2); }
    let model_load_start = Instant::now();
    let model = match load_smollm2(
        format!("{model_dir}/config.json"), format!("{model_dir}/model.safetensors")
    ) {
        Ok(model) => model,
        Err(error) => { eprintln!("model load failed: {error}"); process::exit(1); }
    };
    let tokenizer = match HuggingFaceTokenizer::from_file(format!("{model_dir}/tokenizer.json")) {
        Ok(tokenizer) => tokenizer,
        Err(error) => { eprintln!("tokenizer load failed: {error}"); process::exit(1); }
    };
    let token_config: Value = match fs::read(format!("{model_dir}/tokenizer_config.json"))
        .map_err(|e| e.to_string()).and_then(|b| serde_json::from_slice(&b).map_err(|e| e.to_string())) {
        Ok(value) => value,
        Err(error) => { eprintln!("tokenizer config load failed: {error}"); process::exit(1); }
    };
    let eos_text = token_config.get("eos_token").and_then(token_text).unwrap_or("<|im_end|>");
    let eos_ids = match tokenizer.encode(eos_text) {
        Ok(ids) if ids.len() == 1 => ids,
        Ok(ids) => { eprintln!("EOS token must resolve to one ID, got {ids:?}"); process::exit(1); }
        Err(error) => { eprintln!("EOS tokenization failed: {error}"); process::exit(1); }
    };
    let model_load_ms = model_load_start.elapsed().as_secs_f64() * 1000.0;
    let messages = [
        ChatMessage::new("system", "Answer accurately and concisely."),
        ChatMessage::new("user", prompt.as_str()),
    ];
    let prompt_ids_u32 = match tokenizer.encode_chat(&messages, true) {
        Ok(ids) => ids,
        Err(error) => { eprintln!("prompt tokenization failed: {error}"); process::exit(1); }
    };
    let prompt_ids: Vec<usize> = prompt_ids_u32.iter().map(|&x| x as usize).collect();
    let mut cache = KvCache::new(model.weights.layers.len());
    let inference_start = Instant::now();
    let prefill_start = Instant::now();
    let mut logits = match model.prefill(&prompt_ids, &mut cache) {
        Ok(logits) => logits,
        Err(error) => { eprintln!("prefill failed: {error}"); process::exit(1); }
    };
    let prefill_ms = prefill_start.elapsed().as_secs_f64() * 1000.0;
    let mut generated = Vec::<u32>::new();
    let mut first_token_ms = 0.0;
    for index in 0..max_new {
        let token = match sampling::greedy_sample(&logits) {
            Ok(token) => token as u32,
            Err(error) => { eprintln!("sampling failed: {error}"); process::exit(1); }
        };
        if index == 0 { first_token_ms = inference_start.elapsed().as_secs_f64() * 1000.0; }
        if eos_ids.contains(&token) { break; }
        generated.push(token);
        if index + 1 < max_new {
            logits = match model.step(token as usize, &mut cache) {
                Ok(logits) => logits,
                Err(error) => { eprintln!("decode failed: {error}"); process::exit(1); }
            };
        }
    }
    let inference_ms = inference_start.elapsed().as_secs_f64() * 1000.0;
    let text = match tokenizer.decode(&generated, true) {
        Ok(text) => text,
        Err(error) => { eprintln!("decode text failed: {error}"); process::exit(1); }
    };
    let tps = if inference_ms > 0.0 { generated.len() as f64 / (inference_ms / 1000.0) } else { 0.0 };
    println!("{}", json!({
        "engine": "MKAOS", "prompt": prompt, "text": text,
        "prompt_token_count": prompt_ids.len(), "generated_token_count": generated.len(),
        "model_load_ms": model_load_ms, "prefill_ms": prefill_ms,
        "first_token_ms": first_token_ms, "inference_total_ms": inference_ms,
        "tokens_per_second": tps, "sampling": "greedy",
        "note": "Only report as model-compatible after validate_tokenizer.py and validate_model_logits.py pass."
    }));
}
