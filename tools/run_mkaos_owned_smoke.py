#!/usr/bin/env python3
"""CI-only end-to-end smoke test: train, export, and compare one owned checkpoint.

The generated dataset is synthetic and deliberately tiny. A pass proves pipeline
and numerical compatibility only; it is not a Turkish capability or production claim.
"""
from __future__ import annotations
import hashlib, json, math, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT_IDS = list(b"MKAOS")

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)

def main() -> int:
    try:
        import torch
        from torch import nn
        import torch.nn.functional as F
    except ImportError:
        print("MKAOS smoke test requires PyTorch", file=sys.stderr)
        return 3

    with tempfile.TemporaryDirectory(prefix="mkaos-owned-smoke-") as td:
        work = Path(td)
        examples = [
            ("train-01", "train", "Merhaba dünya", "Merhaba! Türkçe yanıt ver."),
            ("train-02", "train", "Güneş doğdu", "Bugün yeni bir gün."),
            ("train-03", "train", "Bir iki üç", "Dört beş altı."),
            ("valid-01", "validation", "Küçük bir soru", "Bu bir doğrulama örneğidir."),
            ("valid-02", "validation", "Mavi gökyüzü", "Gökyüzü mavidir."),
            ("valid-03", "validation", "Sayı nedir", "Sayı üç."),
            ("test-01", "test", "Bağımsız test", "Bu kayıt eğitimde kullanılmaz."),
            ("test-02", "test", "Kırmızı elma", "Elma kırmızıdır."),
            ("test-03", "test", "Son örnek", "Bu yalnızca sentetik testtir."),
        ]
        records = []
        for rid, split, prompt, response in examples:
            payload = (prompt + "\n" + response).encode("utf-8")
            records.append({
                "prompt": prompt, "response": response, "source_id": "synthetic-ci-" + rid,
                "source_uri": "dataset://synthetic-ci/" + rid, "license_id": "CC0-1.0",
                "consent": True, "review_status": "approved", "personal_data": False,
                "sensitive_data": False, "content_sha256": digest(payload), "split": split,
            })
        manifest_payload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
        manifest = {"training_allowed": True, "summary": {"content_sha256": digest(manifest_payload)},
                    "purpose": "synthetic CI smoke only; not a quality benchmark", "records": records}
        manifest_path = work / "synthetic-ci-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        checkpoint_dir = work / "checkpoint"
        export_dir = work / "export"
        run([sys.executable, "tools/train_mkaos_rust_compatible.py", "--manifest", str(manifest_path),
             "--output-dir", str(checkpoint_dir), "--steps", "4", "--batch-size", "2",
             "--context-length", "16", "--width", "8", "--layers", "1", "--heads", "2",
             "--kv-heads", "1", "--intermediate-size", "16", "--min-records-per-split", "2",
             "--device", "cpu"])
        training_report = json.loads((checkpoint_dir / "training-report.json").read_text(encoding="utf-8"))
        if training_report.get("test_split_used_for_training") is not False:
            raise AssertionError("held-out test split was not explicitly excluded from training")
        heldout_loss = training_report.get("heldout_test_loss")
        if not isinstance(heldout_loss, (int, float)) or not math.isfinite(heldout_loss):
            raise AssertionError("finite held-out test loss was not recorded")
        if training_report.get("heldout_test_target_tokens", 0) <= 0:
            raise AssertionError("held-out test evaluation counted no target tokens")
        run([sys.executable, "tools/export_mkaos_rust_checkpoint.py", "--checkpoint",
             str(checkpoint_dir / "mkaos-rust-compatible.pt"), "--output-dir", str(export_dir)])
        sidecar = json.loads((export_dir / "mkaos-rust-gqa-v1.manifest.json").read_text(encoding="utf-8"))
        checkpoint = torch.load(checkpoint_dir / "mkaos-rust-compatible.pt", map_location="cpu", weights_only=True)
        cfg = checkpoint["config"]

        class RMSNorm(nn.Module):
            def __init__(self, width: int):
                super().__init__()
                self.weight = nn.Parameter(torch.ones(width))
            def forward(self, x):
                return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + 1e-5) * self.weight

        def rope(x, theta=10_000.0):
            seq, dim = x.shape[-2], x.shape[-1]
            inv = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=torch.float32) / dim))
            pos = torch.arange(seq, dtype=torch.float32)
            freqs = torch.outer(pos, inv)
            cos, sin = freqs.cos()[None, None, :, :], freqs.sin()[None, None, :, :]
            first, second = x[..., :dim//2], x[..., dim//2:]
            return torch.cat((first*cos - second*sin, second*cos + first*sin), dim=-1)

        class Block(nn.Module):
            def __init__(self):
                super().__init__()
                d, kvdim = cfg["hidden_size"], (cfg["hidden_size"] // cfg["query_heads"]) * cfg["kv_heads"]
                self.input_norm, self.post_attention_norm = RMSNorm(d), RMSNorm(d)
                self.q_proj = nn.Linear(d, d, bias=False)
                self.k_proj = nn.Linear(d, kvdim, bias=False)
                self.v_proj = nn.Linear(d, kvdim, bias=False)
                self.o_proj = nn.Linear(d, d, bias=False)
                self.gate_proj = nn.Linear(d, cfg["intermediate_size"], bias=False)
                self.up_proj = nn.Linear(d, cfg["intermediate_size"], bias=False)
                self.down_proj = nn.Linear(cfg["intermediate_size"], d, bias=False)
            def forward(self, x):
                b, n, d = x.shape
                hd = d // cfg["query_heads"]
                z = self.input_norm(x)
                q = rope(self.q_proj(z).view(b,n,cfg["query_heads"],hd).transpose(1,2))
                k = rope(self.k_proj(z).view(b,n,cfg["kv_heads"],hd).transpose(1,2))
                v = self.v_proj(z).view(b,n,cfg["kv_heads"],hd).transpose(1,2)
                repeat = cfg["query_heads"] // cfg["kv_heads"]
                k, v = k.repeat_interleave(repeat, dim=1), v.repeat_interleave(repeat, dim=1)
                attn = F.scaled_dot_product_attention(q,k,v,is_causal=True)
                attn = attn.transpose(1,2).contiguous().view(b,n,d)
                x = x + self.o_proj(attn)
                z = self.post_attention_norm(x)
                return x + self.down_proj(F.silu(self.gate_proj(z)) * self.up_proj(z))

        class Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.token_embedding = nn.Embedding(cfg["vocab_size"], cfg["hidden_size"])
                self.layers = nn.ModuleList([Block() for _ in range(cfg["num_layers"])])
                self.final_norm = RMSNorm(cfg["hidden_size"])
                self.lm_head = nn.Linear(cfg["hidden_size"], cfg["vocab_size"], bias=False)
                self.lm_head.weight = self.token_embedding.weight
            def forward(self, ids):
                x = self.token_embedding(ids)
                for layer in self.layers:
                    x = layer(x)
                return self.lm_head(self.final_norm(x))

        torch.manual_seed(0)
        model = Model()
        model.load_state_dict(checkpoint["state_dict"], strict=True)
        model.eval()
        with torch.no_grad():
            py_logits = model(torch.tensor([PROMPT_IDS], dtype=torch.long))[0, -1].tolist()
        rust_cmd = ["cargo", "run", "--quiet", "--manifest-path", "engine/mkaos-inference/Cargo.toml",
                    "--example", "mkaos_parity_probe", "--", str(export_dir / "mkaos-rust-gqa-v1.mkaosw"),
                    sidecar["checkpoint_sha256"], str(cfg["max_sequence_len"]), str(cfg["query_heads"]),
                    str(cfg["kv_heads"]), ",".join(map(str, PROMPT_IDS)), str(cfg["rms_epsilon"])]
        result = subprocess.run(rust_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
        rust_logits = json.loads(result.stdout.strip().splitlines()[-1])
        if len(py_logits) != len(rust_logits):
            raise AssertionError(f"logit count mismatch: Python={len(py_logits)} Rust={len(rust_logits)}")
        errors = [abs(float(a)-float(b)) for a,b in zip(py_logits, rust_logits)]
        max_abs = max(errors)
        if not math.isfinite(max_abs) or max_abs > 1e-3:
            raise AssertionError(f"Python/Rust logits parity failed: max_abs_error={max_abs}")
        report = {"status": "passed", "scope": "synthetic_ci_only", "production_ready": False,
                  "quality_claims_permitted": False, "test_split_used_for_training": False,
                  "checkpoint_sha256": sidecar["checkpoint_sha256"], "prefix_utf8": "MKAOS",
                  "vocab_size": len(py_logits), "max_absolute_logit_error": max_abs,
                  "tolerance": 1e-3, "training_steps": 4, "synthetic_heldout_test_loss": heldout_loss,
                  "note": "Pipeline and numerical parity smoke only; not an independent Turkish quality evaluation."}
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
