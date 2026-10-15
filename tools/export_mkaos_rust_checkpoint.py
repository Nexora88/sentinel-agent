#!/usr/bin/env python3
"""Export a compatible MKAOS PyTorch checkpoint into the Rust MKAOSW1 tensor container."""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path

MAGIC = b"MKAOSW1\0"
SCHEMA = "mkaos-rust-gqa-v1"

def sha256(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint",required=True,type=Path)
    p.add_argument("--output-dir",required=True,type=Path)
    a=p.parse_args()
    try:
        import torch
    except ImportError:
        p.exit(3,"Exporter requires optional PyTorch.\n")
    try:
        blob=torch.load(a.checkpoint,map_location="cpu",weights_only=True)
    except TypeError:
        blob=torch.load(a.checkpoint,map_location="cpu")
    if not isinstance(blob,dict) or blob.get("schema_version") != SCHEMA:
        p.exit(2,"Refusing checkpoint: schema is not mkaos-rust-gqa-v1; do not convert the older GELU/absolute-position model.\n")
    cfg=blob.get("config",{}); sd=blob.get("state_dict",{})
    required=("vocab_size","eos_token_id","hidden_size","num_layers","query_heads","kv_heads","intermediate_size","max_sequence_len","rms_epsilon","rope_theta")
    if any(k not in cfg for k in required): p.exit(2,"Checkpoint config missing required architecture fields.\n")
    v,d,n,qh,kh,ff=(cfg["vocab_size"],cfg["hidden_size"],cfg["num_layers"],cfg["query_heads"],cfg["kv_heads"],cfg["intermediate_size"])
    if v != 257 or cfg["eos_token_id"] != 256 or d % qh or qh % kh or (d//qh)%2:
        p.exit(2,"Tokenizer/head dimensions violate the Rust architecture contract.\n")
    hd=d//qh; kvw=kh*hd
    tensors={}
    def get(name,shape):
        value=sd.get(name)
        if value is None: raise ValueError("missing state tensor: "+name)
        if tuple(value.shape)!=tuple(shape): raise ValueError(f"shape mismatch for {name}: expected {shape}, got {tuple(value.shape)}")
        value=value.detach().to(dtype=torch.float32,device="cpu").contiguous()
        if not torch.isfinite(value).all(): raise ValueError("non-finite tensor: "+name)
        return value
    def matrix(out_name,src_name,shape,transpose=True):
        t=get(src_name,shape)
        if transpose: t=t.T.contiguous()
        tensors[out_name]=(tuple(t.shape),t.reshape(-1).tolist())
    def norm(out_name,src_name):
        t=get(src_name,(d,))
        tensors[out_name]=((1,d),t.reshape(-1).tolist())
    try:
        matrix("token_embedding.weight","token_embedding.weight",(v,d),False)
        for i in range(n):
            pre=f"layers.{i}."
            norm(pre+"input_norm.weight",pre+"input_norm.weight")
            matrix(pre+"q_proj.weight",pre+"q_proj.weight",(d,d))
            matrix(pre+"k_proj.weight",pre+"k_proj.weight",(kvw,d))
            matrix(pre+"v_proj.weight",pre+"v_proj.weight",(kvw,d))
            matrix(pre+"o_proj.weight",pre+"o_proj.weight",(d,d))
            norm(pre+"post_attention_norm.weight",pre+"post_attention_norm.weight")
            matrix(pre+"gate_proj.weight",pre+"gate_proj.weight",(ff,d))
            matrix(pre+"up_proj.weight",pre+"up_proj.weight",(ff,d))
            matrix(pre+"down_proj.weight",pre+"down_proj.weight",(d,ff))
        norm("final_norm.weight","final_norm.weight")
        matrix("lm_head.weight","lm_head.weight",(v,d))
    except (ValueError,RuntimeError) as e:
        p.exit(2,f"Checkpoint rejected: {e}\n")
    if len(tensors) != 2 + 9*n: p.exit(2,"Internal tensor-set count mismatch.\n")
    out=bytearray(MAGIC); out.extend(struct.pack("<I",len(tensors)))
    for name in sorted(tensors):
        shape,values=tensors[name]; encoded=name.encode("utf-8")
        if not encoded or len(encoded)>256: p.exit(2,"Tensor name too long.\n")
        rows,cols=shape
        out.extend(struct.pack("<H",len(encoded))); out.extend(encoded)
        out.extend(struct.pack("<II",rows,cols))
        for value in values: out.extend(struct.pack("<f",value))
    a.output_dir.mkdir(parents=True,exist_ok=False)
    target=a.output_dir/"mkaos-rust-gqa-v1.mkaosw"
    target.write_bytes(out)
    report={"contract_version":SCHEMA,"checkpoint_file":target.name,"checkpoint_sha256":sha256(bytes(out)),
      "source_checkpoint_sha256":sha256(a.checkpoint.read_bytes()),"tensor_count":len(tensors),
      "config":cfg,"tokenizer":{"kind":"utf8-byte","vocab_size":257,"eos_token_id":256},
      "container":"MKAOSW1","tensor_dtype":"float32","layout":"row-major","shape_validation":"passed",
      "weights_transposed_for_rust_matmul":True,"production_ready":False,
      "note":"Serialization/shape contract only; a Rust model assembly loader and numerical parity tests are still required."}
    (a.output_dir/"mkaos-rust-gqa-v1.manifest.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
