//! SafeTensors loader for the pinned LlamaForCausalLM / SmolLM2 tensor naming scheme.
use half::{bf16, f16};
use mkaos_inference::{stacked_decoder::{GqaConfig, GqaDecoder, GqaDecoderWeights, GqaLayerWeights}, Tensor2};
use safetensors::{Dtype, SafeTensors};
use serde_json::Value;
use std::{error::Error, fs, path::Path};

type LoadResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

fn required_usize(config: &Value, key: &str) -> LoadResult<usize> {
    config.get(key).and_then(Value::as_u64).map(|v| v as usize)
        .ok_or_else(|| format!("config.json missing positive integer {key}").into())
}
fn required_f32(config: &Value, key: &str, default: f32) -> LoadResult<f32> {
    match config.get(key).and_then(Value::as_f64) {
        Some(value) if value.is_finite() && value > 0.0 => Ok(value as f32),
        Some(_) => Err(format!("config.json has invalid {key}").into()),
        None => Ok(default),
    }
}
fn tensor_f32(view: safetensors::tensor::TensorView<'_>) -> LoadResult<Vec<f32>> {
    let bytes = view.data();
    let width = match view.dtype() {
        Dtype::F32 => 4,
        Dtype::F16 | Dtype::BF16 => 2,
        other => return Err(format!("unsupported tensor dtype {other:?}; expected F32/F16/BF16").into()),
    };
    if bytes.len() % width != 0 { return Err("tensor byte length is misaligned".into()); }
    let values = match view.dtype() {
        Dtype::F32 => bytes.chunks_exact(4).map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]])).collect(),
        Dtype::F16 => bytes.chunks_exact(2).map(|b| f16::from_bits(u16::from_le_bytes([b[0], b[1]])).to_f32()).collect(),
        Dtype::BF16 => bytes.chunks_exact(2).map(|b| bf16::from_bits(u16::from_le_bytes([b[0], b[1]])).to_f32()).collect(),
        _ => unreachable!(),
    };
    Ok(values)
}
fn matrix(tensors: &SafeTensors<'_>, name: &str, transpose: bool) -> LoadResult<Tensor2> {
    let view = tensors.tensor(name)?;
    let shape = view.shape();
    if shape.len() != 2 { return Err(format!("{name}: expected rank 2, got {shape:?}").into()); }
    let values = tensor_f32(view)?;
    let tensor = Tensor2::new(shape[0], shape[1], values)?;
    if transpose { Ok(tensor.transpose()?) } else { Ok(tensor) }
}
fn vector(tensors: &SafeTensors<'_>, name: &str) -> LoadResult<Vec<f32>> {
    let view = tensors.tensor(name)?;
    if view.shape().len() != 1 { return Err(format!("{name}: expected rank 1").into()); }
    tensor_f32(view)
}

/// Load the standard single-file SmolLM2 SafeTensors artifact and its config.json.
/// Linear weights are transposed from Hugging Face [out, in] to MKAOS [in, out].
pub fn load_smollm2(config_path: impl AsRef<Path>, weights_path: impl AsRef<Path>) -> LoadResult<GqaDecoder> {
    let config: Value = serde_json::from_slice(&fs::read(config_path)?)?;
    if config.get("model_type").and_then(Value::as_str) != Some("llama") {
        return Err("only LlamaForCausalLM config is supported by this loader".into());
    }
    let hidden = required_usize(&config, "hidden_size")?;
    let query_heads = required_usize(&config, "num_attention_heads")?;
    let kv_heads = config.get("num_key_value_heads").and_then(Value::as_u64).unwrap_or(query_heads as u64) as usize;
    let layer_count = required_usize(&config, "num_hidden_layers")?;
    let intermediate = required_usize(&config, "intermediate_size")?;
    let vocab = required_usize(&config, "vocab_size")?;
    let max_seq = config.get("max_position_embeddings").and_then(Value::as_u64).unwrap_or(2048) as usize;
    let epsilon = required_f32(&config, "rms_norm_eps", 1e-5)?;
    let theta = required_f32(&config, "rope_theta", 10000.0)?;
    if hidden == 0 || layer_count == 0 || intermediate == 0 || vocab == 0 || max_seq == 0 {
        return Err("config.json contains zero-sized model dimensions".into());
    }

    let bytes = fs::read(weights_path)?;
    let tensors = SafeTensors::deserialize(&bytes)?;
    let embedding = matrix(&tensors, "model.embed_tokens.weight", false)?;
    if embedding.rows() != vocab || embedding.cols() != hidden {
        return Err(format!("embedding shape mismatch: got [{},{}], config expects [{vocab},{hidden}]", embedding.rows(), embedding.cols()).into());
    }
    let mut layers = Vec::with_capacity(layer_count);
    for i in 0..layer_count {
        let p = format!("model.layers.{i}.");
        let attn = format!("{p}self_attn.");
        let norm1 = vector(&tensors, &format!("{p}input_layernorm.weight"))?;
        let norm2 = vector(&tensors, &format!("{p}post_attention_layernorm.weight"))?;
        layers.push(GqaLayerWeights {
            q_proj: matrix(&tensors, &format!("{attn}q_proj.weight"), true)?,
            k_proj: matrix(&tensors, &format!("{attn}k_proj.weight"), true)?,
            v_proj: matrix(&tensors, &format!("{attn}v_proj.weight"), true)?,
            o_proj: matrix(&tensors, &format!("{attn}o_proj.weight"), true)?,
            input_norm: norm1,
            post_attention_norm: norm2,
            gate_proj: matrix(&tensors, &format!("{p}mlp.gate_proj.weight"), true)?,
            up_proj: matrix(&tensors, &format!("{p}mlp.up_proj.weight"), true)?,
            down_proj: matrix(&tensors, &format!("{p}mlp.down_proj.weight"), true)?,
        });
    }
    let final_norm = vector(&tensors, "model.norm.weight")?;
    let lm_head = match matrix(&tensors, "lm_head.weight", true) {
        Ok(head) => head,
        Err(_) if config.get("tie_word_embeddings").and_then(Value::as_bool) == Some(true) => embedding.transpose()?,
        Err(error) => return Err(error),
    };
    GqaDecoder::new(GqaConfig {
        query_heads, kv_heads, rms_epsilon: epsilon, rope_theta: theta, max_sequence_len: max_seq,
    }, GqaDecoderWeights {
        token_embedding: embedding, layers, final_norm, lm_head,
    }).map_err(|e| e.into())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_non_llama_config_before_loading_weights() {
        let path = std::env::temp_dir().join(format!("mkaos-not-llama-{}.json", std::process::id()));
        fs::write(&path, r#"{"model_type":"gpt2"}"#).unwrap();
        let result = load_smollm2(&path, path.with_extension("missing.safetensors"));
        let _ = fs::remove_file(path);
        assert!(result.unwrap_err().to_string().contains("only LlamaForCausalLM"));
    }
}
