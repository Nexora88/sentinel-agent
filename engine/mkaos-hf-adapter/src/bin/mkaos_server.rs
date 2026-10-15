//! Resident, loopback-only MKAOS HTTP runtime with a small Ollama-compatible API surface.
//! Model weights and tokenizer are loaded once at startup; KV cache is per request.
use mkaos_hf_adapter::{
    model_loader::load_smollm2, policy::TURKISH_FIRST_SYSTEM_PROMPT, ChatMessage,
    HuggingFaceTokenizer,
};
use mkaos_inference::{sampling, stacked_decoder::GqaDecoder, stacked_decoder::KvCache};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    env, fs,
    io::{BufRead, BufReader, Read, Write},
    net::{SocketAddr, TcpListener, TcpStream},
    process,
    time::Instant,
};

const MAX_BODY_BYTES: usize = 1_048_576;
const DEFAULT_MAX_NEW_TOKENS: usize = 96;
const MAX_NEW_TOKENS: usize = 512;

fn token_text(value: &Value) -> Option<&str> {
    value.as_str().or_else(|| value.get("content").and_then(Value::as_str))
}

fn env_float(name: &str, default: f32) -> f32 {
    env::var(name).ok().and_then(|value| value.parse::<f32>().ok()).unwrap_or(default)
}

fn repetition_penalty_from_env() -> f32 {
    let value = env_float("MKAOS_REPETITION_PENALTY", 1.10);
    if !value.is_finite() || !(1.0..=2.0).contains(&value) {
        eprintln!("MKAOS_REPETITION_PENALTY must be between 1.0 and 2.0");
        process::exit(2);
    }
    value
}

fn send_response(stream: &mut TcpStream, status: &str, content_type: &str, body: &[u8]) -> std::io::Result<()> {
    write!(
        stream,
        "HTTP/1.1 {status}\r\nContent-Type: {content_type}\r\nContent-Length: {}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n",
        body.len()
    )?;
    stream.write_all(body)?;
    stream.flush()
}

fn send_json(stream: &mut TcpStream, status: &str, value: Value, ndjson: bool) -> std::io::Result<()> {
    let mut body = serde_json::to_vec(&value).unwrap_or_else(|_| b"{\"error\":\"serialization failed\"}".to_vec());
    let content_type = if ndjson { "application/x-ndjson" } else { "application/json" };
    if ndjson { body.push(b'\n'); }
    send_response(stream, status, content_type, &body)
}

fn read_request(stream: &TcpStream) -> Result<(String, String, Vec<u8>), String> {
    let cloned = stream.try_clone().map_err(|e| e.to_string())?;
    let mut reader = BufReader::new(cloned);
    let mut request_line = String::new();
    reader.read_line(&mut request_line).map_err(|e| e.to_string())?;
    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or("").to_string();
    let path = parts.next().unwrap_or("").to_string();
    if method.is_empty() || path.is_empty() {
        return Err("malformed HTTP request line".to_string());
    }
    let mut content_length = 0usize;
    let mut header_bytes = request_line.len();
    loop {
        let mut line = String::new();
        let count = reader.read_line(&mut line).map_err(|e| e.to_string())?;
        if count == 0 { return Err("incomplete HTTP headers".to_string()); }
        header_bytes += count;
        if header_bytes > 65_536 { return Err("HTTP headers exceed 64 KiB".to_string()); }
        if line == "\r\n" || line == "\n" { break; }
        if let Some((name, value)) = line.split_once(':') {
            if name.eq_ignore_ascii_case("content-length") {
                content_length = value.trim().parse().map_err(|_| "invalid Content-Length".to_string())?;
            }
        }
    }
    if content_length > MAX_BODY_BYTES {
        return Err(format!("request body exceeds {MAX_BODY_BYTES} bytes"));
    }
    let mut body = vec![0u8; content_length];
    reader.read_exact(&mut body).map_err(|e| e.to_string())?;
    Ok((method, path, body))
}

fn parse_messages(
    path: &str,
    body: &Value,
    default_system: &str,
    penalty_default: f32,
) -> Result<(Vec<ChatMessage>, usize, f32, f32, f32), String> {
    let options = body.get("options").unwrap_or(&Value::Null);
    let requested = options.get("num_predict").and_then(Value::as_u64)
        .map(|n| n as usize).unwrap_or(DEFAULT_MAX_NEW_TOKENS);
    if requested == 0 || requested > MAX_NEW_TOKENS {
        return Err(format!("num_predict must be between 1 and {MAX_NEW_TOKENS}"));
    }
    let penalty = options.get("repeat_penalty").and_then(Value::as_f64)
        .map(|v| v as f32).unwrap_or(penalty_default);
    let temperature = options.get("temperature").and_then(Value::as_f64).map(|v| v as f32)
        .unwrap_or_else(|| env_float("MKAOS_TEMPERATURE", 0.15));
    let top_p = options.get("top_p").and_then(Value::as_f64).map(|v| v as f32)
        .unwrap_or_else(|| env_float("MKAOS_TOP_P", 0.9));
    if !penalty.is_finite() || !(1.0..=2.0).contains(&penalty) {
        return Err("repeat_penalty must be between 1.0 and 2.0".to_string());
    }
    if !temperature.is_finite() || !(0.0..=2.0).contains(&temperature) {
        return Err("temperature must be between 0.0 and 2.0".to_string());
    }
    if !top_p.is_finite() || !(0.0..=1.0).contains(&top_p) || top_p == 0.0 {
        return Err("top_p must be greater than 0 and at most 1.0".to_string());
    }

    let mut messages = Vec::new();
    if path == "/api/chat" {
        if let Some(items) = body.get("messages").and_then(Value::as_array) {
            for item in items {
                let role = item.get("role").and_then(Value::as_str).unwrap_or("user");
                let content = item.get("content").and_then(Value::as_str)
                    .ok_or_else(|| "each message must have string content".to_string())?;
                if !matches!(role, "system" | "user" | "assistant") {
                    return Err(format!("unsupported role: {role}"));
                }
                messages.push(ChatMessage::new(role, content));
            }
        }
        if messages.is_empty() { return Err("/api/chat requires a non-empty messages array".to_string()); }
        if !messages.iter().any(|m| m.role == "system") {
            messages.insert(0, ChatMessage::new("system", default_system));
        }
    } else {
        let system = body.get("system").and_then(Value::as_str)
            .filter(|s| !s.trim().is_empty()).unwrap_or(default_system);
        let prompt = body.get("prompt").and_then(Value::as_str)
            .ok_or_else(|| "/api/generate requires a string prompt".to_string())?;
        messages.push(ChatMessage::new("system", system));
        messages.push(ChatMessage::new("user", prompt));
    }
    Ok((messages, requested, penalty, temperature, top_p))
}

fn next_random_unit(state: &mut u64) -> f32 {
    // Deterministic xorshift for repeatable sampling; not cryptographic randomness.
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    ((*state >> 40) as u32) as f32 / 16_777_216.0
}

fn generate(
    model: &GqaDecoder,
    tokenizer: &HuggingFaceTokenizer,
    eos_ids: &[u32],
    messages: &[ChatMessage],
    max_new: usize,
    penalty: f32,
    temperature: f32,
    top_p: f32,
    prefix_cache: &mut HashMap<String, KvCache>,
) -> Result<(String, usize, usize, u128, u128, u128, bool), String> {
    let prompt_ids_u32 = tokenizer.encode_chat(messages, true).map_err(|e| e.to_string())?;
    let prompt_ids: Vec<usize> = prompt_ids_u32.iter().map(|&x| x as usize).collect();
    let request_start = Instant::now();
    let mut cache = KvCache::new(model.weights.layers.len());
    let mut prefix_len = 0usize;
    let mut prefix_cache_hit = false;
    let mut prefill_ns = 0u128;

    // Cache only the exact leading system-message prefix. A cache hit skips its
    // attention/MLP work; the user's current prompt and history are still evaluated.
    if let Some(system) = messages.first().filter(|message| message.role == "system") {
        let key = system.content.clone();
        let prefix_ids_u32 = tokenizer.encode_chat(std::slice::from_ref(system), false)
            .map_err(|e| e.to_string())?;
        let prefix_ids: Vec<usize> = prefix_ids_u32.iter().map(|&x| x as usize).collect();
        if !prefix_ids.is_empty() && prompt_ids.starts_with(&prefix_ids) && prefix_ids.len() < prompt_ids.len() {
            if let Some(saved_cache) = prefix_cache.get(&key) {
                cache = saved_cache.clone();
                prefix_cache_hit = true;
            } else {
                let prefix_start = Instant::now();
                model.prefill(&prefix_ids, &mut cache).map_err(|e| e.to_string())?;
                prefill_ns += prefix_start.elapsed().as_nanos();
                if prefix_cache.len() >= 8 {
                    if let Some(oldest_key) = prefix_cache.keys().next().cloned() {
                        prefix_cache.remove(&oldest_key);
                    }
                }
                prefix_cache.insert(key, cache.clone());
            }
            prefix_len = prefix_ids.len();
        }
    }

    let prefill_start = Instant::now();
    let mut random_state = prompt_ids.iter().fold(0xcbf29ce484222325_u64,
        |state, id| (state ^ (*id as u64)).wrapping_mul(0x100000001b3));
    if random_state == 0 { random_state = 0x9e3779b97f4a7c15; }
    let remaining = &prompt_ids[prefix_len..];
    let mut logits = model.prefill(remaining, &mut cache).map_err(|e| e.to_string())?;
    prefill_ns += prefill_start.elapsed().as_nanos();
    let decode_start = Instant::now();
    let mut generated = Vec::<u32>::new();
    // Penalize repeats against the prompt and generated answer, not just tokens
    // emitted in this response. Maintain the history incrementally to avoid a
    // per-token allocation/copy on the decode hot path.
    let mut repetition_context = prompt_ids.clone();
    for index in 0..max_new {
        let mut adjusted_logits = logits.clone();
        sampling::apply_repetition_penalty(&mut adjusted_logits, &repetition_context, penalty).map_err(|e| e.to_string())?;
        let sampled = if temperature <= 0.0 {
            sampling::greedy_sample(&adjusted_logits)
        } else {
            sampling::sample_top_p(&adjusted_logits, temperature, top_p, next_random_unit(&mut random_state))
        };
        let token = sampled.map_err(|e| e.to_string())? as u32;
        if eos_ids.contains(&token) { break; }
        generated.push(token);
        repetition_context.push(token as usize);
        if index + 1 < max_new {
            logits = model.step(token as usize, &mut cache).map_err(|e| e.to_string())?;
        }
    }
    let decode_ns = decode_start.elapsed().as_nanos();
    let total_ns = request_start.elapsed().as_nanos();
    let answer = tokenizer.decode(&generated, true).map_err(|e| e.to_string())?;
    Ok((answer, prompt_ids.len(), generated.len(), prefill_ns, decode_ns, total_ns, prefix_cache_hit))
}

fn handle(
    mut stream: TcpStream,
    model: &GqaDecoder,
    tokenizer: &HuggingFaceTokenizer,
    eos_ids: &[u32],
    default_system: &str,
    penalty_default: f32,
    prefix_cache: &mut HashMap<String, KvCache>,
) {
    let _ = stream.set_read_timeout(Some(std::time::Duration::from_secs(30)));
    let _ = stream.set_write_timeout(Some(std::time::Duration::from_secs(900)));
    let (method, path, body_bytes) = match read_request(&stream) {
        Ok(request) => request,
        Err(error) => {
            let _ = send_json(&mut stream, "400 Bad Request", json!({"error":error}), false);
            return;
        }
    };
    if method == "GET" && (path == "/" || path == "/health") {
        let _ = send_json(&mut stream, "200 OK", json!({"status":"ok","engine":"MKAOS","model_loaded":true}), false);
        return;
    }
    if method == "GET" && path == "/api/tags" {
        let _ = send_json(&mut stream, "200 OK", json!({"models":[{"name":"mkaos-local","model":"mkaos-local","details":{"family":"smollm2","parameter_size":"135M"}}]}), false);
        return;
    }
    if method != "POST" || !matches!(path.as_str(), "/api/chat" | "/api/generate") {
        let _ = send_json(&mut stream, "404 Not Found", json!({"error":"unsupported endpoint"}), false);
        return;
    }
    let body: Value = match serde_json::from_slice(&body_bytes) {
        Ok(value) => value,
        Err(error) => {
            let _ = send_json(&mut stream, "400 Bad Request", json!({"error":format!("invalid JSON: {error}")}), false);
            return;
        }
    };
    let (messages, max_new, penalty, temperature, top_p) =
        match parse_messages(&path, &body, default_system, penalty_default) {
            Ok(value) => value,
            Err(error) => {
                let _ = send_json(&mut stream, "400 Bad Request", json!({"error":error}), false);
                return;
            }
        };
    let started = Instant::now();
    match generate(model, tokenizer, eos_ids, &messages, max_new, penalty, temperature, top_p, prefix_cache) {
        Ok((answer, prompt_count, generated_count, prefill_ns, decode_ns, total_ns, prefix_cache_hit)) => {
            let total_ns = total_ns.max(started.elapsed().as_nanos());
            let payload = if path == "/api/chat" {
                json!({
                    "model":"mkaos-local",
                    "message":{"role":"assistant","content":answer},
                    "done":true,
                    "total_duration":total_ns,
                    "load_duration":0,
                    "prompt_eval_count":prompt_count,
                    "prompt_eval_duration":prefill_ns,
                    "eval_count":generated_count,
                    "eval_duration":decode_ns,
                    "mkaos_prefix_cache_hit":prefix_cache_hit
                })
            } else {
                json!({
                    "model":"mkaos-local","response":answer,"done":true,
                    "total_duration":total_ns,"load_duration":0,
                    "prompt_eval_count":prompt_count,"prompt_eval_duration":prefill_ns,
                    "eval_count":generated_count,"eval_duration":decode_ns,
                    "mkaos_prefix_cache_hit":prefix_cache_hit
                })
            };
            let _ = send_json(&mut stream, "200 OK", payload, true);
            eprintln!("request path={path} prompt_tokens={prompt_count} generated_tokens={generated_count} prefix_cache_hit={prefix_cache_hit} temperature={temperature:.2} top_p={top_p:.2} prefill_ms={:.2} decode_ms={:.2} total_ms={:.2}",
                prefill_ns as f64 / 1e6, decode_ns as f64 / 1e6, total_ns as f64 / 1e6);
        }
        Err(error) => {
            let _ = send_json(&mut stream, "500 Internal Server Error", json!({"error":error}), false);
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() < 1 || args.len() > 2 {
        eprintln!("usage: mkaos_server <model-dir> [127.0.0.1:11435]");
        process::exit(2);
    }
    let bind: SocketAddr = args.get(1).map(String::as_str).unwrap_or("127.0.0.1:11435")
        .parse().unwrap_or_else(|_| { eprintln!("invalid bind address"); process::exit(2) });
    // Default is loopback-only. Container deployments may opt in to a private,
    // non-published Docker network using MKAOS_ALLOW_PRIVATE_BIND=true.
    let allow_private_bind = env::var("MKAOS_ALLOW_PRIVATE_BIND")
        .map(|value| matches!(value.trim().to_ascii_lowercase().as_str(), "1" | "true" | "yes" | "on"))
        .unwrap_or(false);
    if !bind.ip().is_loopback() && !(allow_private_bind && bind.ip().is_unspecified()) {
        eprintln!("MKAOS server binds only to loopback by default; non-loopback bind requires MKAOS_ALLOW_PRIVATE_BIND=true");
        process::exit(2);
    }
    if !bind.ip().is_loopback() {
        eprintln!("WARNING: MKAOS is bound to a container interface. Do not publish its port; use only on a trusted private Docker network.");
    }
    let model_dir = &args[0];
    let load_start = Instant::now();
    let model = load_smollm2(
        format!("{model_dir}/config.json"), format!("{model_dir}/model.safetensors")
    ).unwrap_or_else(|error| { eprintln!("model load failed: {error}"); process::exit(1) });
    let tokenizer = HuggingFaceTokenizer::from_file(format!("{model_dir}/tokenizer.json"))
        .unwrap_or_else(|error| { eprintln!("tokenizer load failed: {error}"); process::exit(1) });
    let token_config: Value = fs::read(format!("{model_dir}/tokenizer_config.json"))
        .and_then(|bytes| serde_json::from_slice(&bytes).map_err(std::io::Error::other))
        .unwrap_or_else(|error| { eprintln!("tokenizer config load failed: {error}"); process::exit(1) });
    let eos_text = token_config.get("eos_token").and_then(token_text).unwrap_or("<|im_end|>");
    let eos_ids = tokenizer.encode(eos_text).unwrap_or_else(|error| { eprintln!("EOS tokenization failed: {error}"); process::exit(1) });
    if eos_ids.len() != 1 {
        eprintln!("EOS token must resolve to one ID");
        process::exit(1);
    }
    let default_system = env::var("MKAOS_SYSTEM_PROMPT").ok()
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| TURKISH_FIRST_SYSTEM_PROMPT.to_string());
    let penalty = repetition_penalty_from_env();
    let listener = TcpListener::bind(bind).unwrap_or_else(|error| { eprintln!("bind failed: {error}"); process::exit(1) });
    eprintln!("MKAOS resident server listening on http://{bind}; model loaded once in {:.2}s", load_start.elapsed().as_secs_f64());
    let mut prefix_cache = HashMap::<String, KvCache>::new();
    for connection in listener.incoming() {
        match connection {
            Ok(stream) => handle(stream, &model, &tokenizer, &eos_ids, &default_system, penalty, &mut prefix_cache),
            Err(error) => eprintln!("accept failed: {error}"),
        }
    }
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_chat_sampling_options_with_bounds() {
        let body = json!({
            "messages": [{"role":"user","content":"Merhaba"}],
            "options": {
                "num_predict": 24,
                "repeat_penalty": 1.2,
                "temperature": 0.15,
                "top_p": 0.9
            }
        });
        let (messages, max_new, penalty, temperature, top_p) =
            parse_messages("/api/chat", &body, "Kısa yanıt ver.", 1.1).unwrap();
        assert_eq!(messages.len(), 2);
        assert_eq!(messages[0].role, "system");
        assert_eq!(max_new, 24);
        assert!((penalty - 1.2).abs() < 1e-6);
        assert!((temperature - 0.15).abs() < 1e-6);
        assert!((top_p - 0.9).abs() < 1e-6);
    }

    #[test]
    fn rejects_unsafe_generation_bounds_and_invalid_sampling_values() {
        for options in [
            json!({"num_predict": 0}),
            json!({"num_predict": 513}),
            json!({"temperature": 3.0}),
            json!({"top_p": 0.0}),
            json!({"repeat_penalty": 0.5})
        ] {
            let body = json!({
                "messages": [{"role":"user","content":"test"}],
                "options": options
            });
            assert!(parse_messages("/api/chat", &body, "system", 1.1).is_err());
        }
    }

    #[test]
    fn deterministic_sampling_rng_is_bounded_and_repeatable() {
        let mut first = 123456789_u64;
        let mut second = 123456789_u64;
        for _ in 0..16 {
            let a = next_random_unit(&mut first);
            let b = next_random_unit(&mut second);
            assert!((0.0..1.0).contains(&a));
            assert_eq!(a, b);
        }
    }
}
