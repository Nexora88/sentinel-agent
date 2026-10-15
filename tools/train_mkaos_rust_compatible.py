#!/usr/bin/env python3
"""Train an offline byte-tokenized MKAOS research LM with the Rust GqaDecoder architecture.

Architecture contract: tools/mkaos-rust-model-contract.json. This remains a tiny
research model; matching tensor shapes is not a claim of useful general intelligence.
"""
from __future__ import annotations
import argparse, hashlib, json, random, time
from pathlib import Path

VOCAB_SIZE = 257
EOS_ID = 256
ALLOWED_LICENSES = {"CC0-1.0", "CC-BY-4.0", "MIT", "Apache-2.0"}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_manifest(path: Path, minimum: int):
    raw = path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict) or manifest.get("training_allowed") is not True:
        raise ValueError("manifest is not explicitly approved for training")
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("manifest has no records")
    splits = {"train": [], "validation": [], "test": []}
    source_splits = {}
    for i, rec in enumerate(records):
        if not isinstance(rec, dict) or rec.get("split") not in splits:
            raise ValueError(f"record {i} has invalid shape/split")
        for field in ("prompt", "response", "source_id", "source_uri", "license_id", "content_sha256"):
            if not isinstance(rec.get(field), str) or not rec[field].strip():
                raise ValueError(f"record {i} missing {field}")
        if rec["license_id"] not in ALLOWED_LICENSES:
            raise ValueError(f"record {i} license is not allowlisted")
        if not rec["source_uri"].startswith(("https://", "file://", "dataset://")):
            raise ValueError(f"record {i} source URI is not auditable")
        if rec.get("consent") is not True or rec.get("review_status", "approved") != "approved":
            raise ValueError(f"record {i} lacks consent or human approval")
        if rec.get("personal_data") is True or rec.get("sensitive_data") is True:
            raise ValueError(f"record {i} is marked personal/sensitive")
        source_splits.setdefault(rec["source_id"], set()).add(rec["split"])
        splits[rec["split"]].append("Kullanıcı: " + rec["prompt"].strip() + "\nMKAOS: " + rec["response"].strip())
    if any(len(v) < minimum for v in splits.values()):
        raise ValueError(f"each split must have at least {minimum} records: " + str({k: len(v) for k,v in splits.items()}))
    if any(len(v) > 1 for v in source_splits.values()):
        raise ValueError("source leakage across train/validation/test splits")
    return manifest, splits

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--context-length", type=int, default=128)
    p.add_argument("--width", type=int, default=128)
    p.add_argument("--layers", type=int, default=2)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--kv-heads", type=int, default=2)
    p.add_argument("--intermediate-size", type=int, default=256)
    p.add_argument("--learning-rate", type=float, default=3e-4)
    p.add_argument("--seed", type=int, default=20261015)
    p.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    p.add_argument("--min-records-per-split", type=int, default=2)
    a = p.parse_args()
    if min(a.steps,a.batch_size,a.context_length,a.width,a.layers,a.heads,a.kv_heads,a.intermediate_size) < 1:
        p.error("all dimensions and steps must be positive")
    if a.width % a.heads or a.heads % a.kv_heads or (a.width // a.heads) % 2:
        p.error("width must divide by heads; heads by kv-heads; head dimension must be even")
    if not 0 < a.learning_rate <= .1:
        p.error("learning rate must be in (0, 0.1]")
    try:
        manifest, splits = load_manifest(a.manifest, a.min_records_per_split)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        p.exit(2, f"Training blocked: {e}\n")
    try:
        import torch
        from torch import nn
        import torch.nn.functional as F
    except ImportError:
        p.exit(3, "Training requires optional PyTorch in the development environment.\n")
    if a.device == "cuda" and not torch.cuda.is_available():
        p.exit(2, "CUDA requested but unavailable.\n")
    device = ("cuda" if torch.cuda.is_available() else "cpu") if a.device == "auto" else a.device
    random.seed(a.seed); torch.manual_seed(a.seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(a.seed)
    def stream(records):
        # EOS=256 is outside bytearray's 0..255 range; keep token IDs as integers.
        out = []
        for record in records:
            out.extend(record.encode("utf-8")); out.append(EOS_ID)
        return torch.tensor(out, dtype=torch.long)
    train = stream(splits["train"]); valid = stream(splits["validation"]); test = stream(splits["test"])
    if min(len(train), len(valid), len(test)) <= a.context_length:
        p.exit(2, "Train, validation, and held-out test streams must exceed context-length.\n")

    class RMSNorm(nn.Module):
        def __init__(self, width):
            super().__init__(); self.weight = nn.Parameter(torch.ones(width))
        def forward(self, x):
            return x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + 1e-5) * self.weight

    def rope(x, theta=10000.0):
        # x [batch, heads, sequence, head_dim], split-half layout matching Rust apply_rope.
        seq, dim = x.shape[-2], x.shape[-1]
        inv = 1.0 / (theta ** (torch.arange(0, dim, 2, device=x.device, dtype=torch.float32) / dim))
        pos = torch.arange(seq, device=x.device, dtype=torch.float32)
        freqs = torch.outer(pos, inv)
        cos, sin = freqs.cos()[None,None,:,:], freqs.sin()[None,None,:,:]
        first, second = x[..., :dim//2], x[..., dim//2:]
        return torch.cat((first*cos - second*sin, second*cos + first*sin), dim=-1)

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            d, kvdim = a.width, (a.width // a.heads) * a.kv_heads
            self.input_norm = RMSNorm(d); self.post_attention_norm = RMSNorm(d)
            self.q_proj = nn.Linear(d, d, bias=False)
            self.k_proj = nn.Linear(d, kvdim, bias=False)
            self.v_proj = nn.Linear(d, kvdim, bias=False)
            self.o_proj = nn.Linear(d, d, bias=False)
            self.gate_proj = nn.Linear(d, a.intermediate_size, bias=False)
            self.up_proj = nn.Linear(d, a.intermediate_size, bias=False)
            self.down_proj = nn.Linear(a.intermediate_size, d, bias=False)
        def forward(self, x):
            b, n, d = x.shape; hd = d // a.heads
            z = self.input_norm(x)
            q = rope(self.q_proj(z).view(b,n,a.heads,hd).transpose(1,2))
            k = rope(self.k_proj(z).view(b,n,a.kv_heads,hd).transpose(1,2))
            v = self.v_proj(z).view(b,n,a.kv_heads,hd).transpose(1,2)
            repeat = a.heads // a.kv_heads
            k = k.repeat_interleave(repeat, dim=1); v = v.repeat_interleave(repeat, dim=1)
            attn = F.scaled_dot_product_attention(q,k,v,is_causal=True)
            attn = attn.transpose(1,2).contiguous().view(b,n,d)
            x = x + self.o_proj(attn)
            z = self.post_attention_norm(x)
            return x + self.down_proj(F.silu(self.gate_proj(z)) * self.up_proj(z))

    class Model(nn.Module):
        def __init__(self):
            super().__init__()
            self.token_embedding = nn.Embedding(VOCAB_SIZE, a.width)
            self.layers = nn.ModuleList([Block() for _ in range(a.layers)])
            self.final_norm = RMSNorm(a.width)
            self.lm_head = nn.Linear(a.width, VOCAB_SIZE, bias=False)
            self.lm_head.weight = self.token_embedding.weight
        def forward(self, ids):
            x = self.token_embedding(ids)
            for block in self.layers: x = block(x)
            return self.lm_head(self.final_norm(x))

    def batch(stream_tensor):
        max_start = len(stream_tensor) - a.context_length - 1
        starts = torch.randint(0, max_start + 1, (a.batch_size,))
        x = torch.stack([stream_tensor[int(s):int(s)+a.context_length] for s in starts])
        y = torch.stack([stream_tensor[int(s)+1:int(s)+a.context_length+1] for s in starts])
        return x.to(device), y.to(device)

    model = Model().to(device); opt = torch.optim.AdamW(model.parameters(), lr=a.learning_rate)
    first_loss = last_loss = valid_loss = None; started = time.time()
    for step in range(1, a.steps + 1):
        model.train(); x,y = batch(train); logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1,VOCAB_SIZE), y.reshape(-1))
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
        if first_loss is None: first_loss = float(loss.detach().cpu())
        last_loss = float(loss.detach().cpu())
        if step == 1 or step % max(1,a.steps//10) == 0 or step == a.steps:
            model.eval()
            with torch.no_grad():
                vx,vy = batch(valid); valid_loss = float(F.cross_entropy(model(vx).reshape(-1,VOCAB_SIZE),vy.reshape(-1)).cpu())
            print(json.dumps({"step":step,"train_loss":round(last_loss,5),"validation_loss":round(valid_loss,5)}))
    # Deterministic, full-stream held-out next-token loss; test records never enter optimizer batches.
    model.eval(); test_loss_sum = 0.0; test_token_count = 0
    with torch.no_grad():
        for start in range(0, len(test) - 1, a.context_length):
            count = min(a.context_length, len(test) - start - 1)
            if count <= 0: break
            tx = test[start:start + count].unsqueeze(0).to(device)
            ty = test[start + 1:start + count + 1].unsqueeze(0).to(device)
            tl = model(tx)
            test_loss_sum += float(F.cross_entropy(tl.reshape(-1, VOCAB_SIZE), ty.reshape(-1), reduction="sum").cpu())
            test_token_count += count
    test_loss = test_loss_sum / max(1, test_token_count)

    a.output_dir.mkdir(parents=True, exist_ok=False)
    ckpt = a.output_dir / "mkaos-rust-compatible.pt"
    cfg = {"vocab_size":VOCAB_SIZE,"eos_token_id":EOS_ID,"hidden_size":a.width,"num_layers":a.layers,
           "query_heads":a.heads,"kv_heads":a.kv_heads,"intermediate_size":a.intermediate_size,
           "max_sequence_len":a.context_length,"rms_epsilon":1e-5,"rope_theta":10000.0}
    torch.save({"schema_version":"mkaos-rust-gqa-v1","config":cfg,"state_dict":model.cpu().state_dict()}, ckpt)
    report = {"schema_version":"mkaos-rust-gqa-v1","status":"experimental_trained_checkpoint",
      "checkpoint_file":ckpt.name,"checkpoint_sha256":sha256(ckpt.read_bytes()),
      "dataset_manifest_sha256":sha256(a.manifest.read_bytes()),
      "dataset_content_sha256":manifest.get("summary",{}).get("content_sha256"),
      "split_counts":{k:len(v) for k,v in splits.items()},"test_split_used_for_training":False,
      "tokenizer":{"kind":"project-owned-utf8-byte","vocab_size":VOCAB_SIZE,"eos_token_id":EOS_ID},
      "architecture":cfg,"optimizer":"AdamW","learning_rate":a.learning_rate,"seed":a.seed,"steps":a.steps,
      "device":device,"train_loss_first":round(first_loss,6),"train_loss_last":round(last_loss,6),
      "validation_loss_last":round(valid_loss,6) if valid_loss is not None else None,
      "heldout_test_loss":round(test_loss,6),"heldout_test_target_tokens":test_token_count,
      "elapsed_seconds":round(time.time()-started,3),"torch_version":torch.__version__,
      "rust_tensor_contract":"mkaos-rust-gqa-v1","production_ready":False,
      "note":"Architecture-compatible training checkpoint; run exporter, Rust shape validation, and held-out evaluation before use."}
    (a.output_dir/"training-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__ == "__main__": main()
