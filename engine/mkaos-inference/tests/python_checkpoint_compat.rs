//! End-to-end format compatibility test: Python trainer's MKAOSW1 layout -> Rust loader -> GQA decoder.
//! The deterministic weights here are synthetic test fixtures, not a trained MKAOS checkpoint.
use mkaos_inference::{
    checkpoint::load_checkpoint,
    stacked_decoder::{GqaConfig, GqaDecoder},
};
use std::{collections::BTreeMap, fs, path::PathBuf};

fn append_tensor(out: &mut Vec<u8>, name: &str, rows: u32, cols: u32, values: &[f32]) {
    let name_bytes = name.as_bytes();
    assert_eq!(values.len(), rows as usize * cols as usize);
    out.extend_from_slice(&(name_bytes.len() as u16).to_le_bytes());
    out.extend_from_slice(name_bytes);
    out.extend_from_slice(&rows.to_le_bytes());
    out.extend_from_slice(&cols.to_le_bytes());
    for value in values {
        out.extend_from_slice(&value.to_le_bytes());
    }
}

fn synthetic_python_format_checkpoint() -> Vec<u8> {
    let (vocab, d, kv_width, ff) = (257usize, 8usize, 4usize, 12usize);
    let mut tensors: BTreeMap<String, (usize, usize, Vec<f32>)> = BTreeMap::new();
    let mut insert = |name: String, rows: usize, cols: usize| {
        let values = (0..rows * cols)
            .map(|i| (((i * 7 + name.len()) % 19) as f32 - 9.0) * 0.002)
            .collect();
        tensors.insert(name, (rows, cols, values));
    };
    insert("token_embedding.weight".into(), vocab, d);
    insert("final_norm.weight".into(), 1, d);
    insert("lm_head.weight".into(), d, vocab);
    insert("layers.0.input_norm.weight".into(), 1, d);
    insert("layers.0.q_proj.weight".into(), d, d);
    insert("layers.0.k_proj.weight".into(), d, kv_width);
    insert("layers.0.v_proj.weight".into(), d, kv_width);
    insert("layers.0.o_proj.weight".into(), d, d);
    insert("layers.0.post_attention_norm.weight".into(), 1, d);
    insert("layers.0.gate_proj.weight".into(), d, ff);
    insert("layers.0.up_proj.weight".into(), d, ff);
    insert("layers.0.down_proj.weight".into(), ff, d);

    let mut out = b"MKAOSW1\0".to_vec();
    out.extend_from_slice(&(tensors.len() as u32).to_le_bytes());
    for (name, (rows, cols, values)) in tensors {
        append_tensor(&mut out, &name, rows as u32, cols as u32, &values);
    }
    out
}

fn temporary_checkpoint_path() -> PathBuf {
    std::env::temp_dir().join(format!("mkaos-python-rust-compat-{}.mkaosw", std::process::id()))
}

#[test]
fn python_layout_loads_in_rust_and_produces_finite_logits() {
    let bytes = synthetic_python_format_checkpoint();
    let hash = mkaos_inference::sha256::to_hex(&mkaos_inference::sha256::sha256(&bytes));
    let path = temporary_checkpoint_path();
    fs::write(&path, &bytes).expect("write synthetic checkpoint");
    let loaded = load_checkpoint(&path, &hash, 1_000_000, 1_000_000)
        .expect("Rust loader must accept the Python trainer's MKAOSW1 layout");
    let _ = fs::remove_file(&path);

    assert_eq!(loaded.sha256, hash);
    let model = GqaDecoder::from_checkpoint(
        GqaConfig {
            query_heads: 4,
            kv_heads: 2,
            rms_epsilon: 1e-5,
            rope_theta: 10_000.0,
            max_sequence_len: 32,
        },
        &loaded,
    )
    .expect("tensor names and shapes must match the owned GQA decoder contract");
    let logits = model.logits_for_prefix_reference(&[77, 75, 256])
        .expect("synthetic token sequence should run through the decoder");
    assert_eq!(logits.len(), 257);
    assert!(logits.iter().all(|value| value.is_finite()));
}
