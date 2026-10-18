# MKAOS Hugging Face compatibility matrix

Status date: 2026-10-18. This is a validation plan, not a claim that any external checkpoint has been converted into MKAOSW1.

| Model / family | HF architecture | License metadata | Preflight status | Numerical parity to MKAOSW1 | Decision |
|---|---|---|---|---|---|
| HuggingFaceTB/SmolLM2-135M-Instruct | LlamaForCausalLM, model_type=llama, 134.5M parameters | Apache-2.0 metadata at pinned revision 12fd25f77366fa6b3b4b768ec3050bf629380bac | CPU reference smoke scheduled in GitHub Actions | NOT RUN: no Llama adapter/exporter exists yet | Best first CPU reference; do not convert yet |
| Meta Llama 3.2 | LlamaForCausalLM family; exact variant/config must be recorded | Model-specific Meta Llama license, not automatically Apache | NOT RUN | NOT RUN | Block until license acceptance and architecture-specific mapping |
| Qwen2.5-Coder | Qwen2ForCausalLM; exact size/config must be recorded | Check the selected repository revision and license metadata | NOT RUN | NOT RUN | Separate adapter path; do not assume Llama tensor layout |

## Required parity protocol before a converter can be approved

1. Pin model ID, immutable Hub commit SHA, config/tokenizer hashes, library versions, dtype, and fixed prompt/token-ID fixtures.
2. Load the original model on CPU in evaluation mode; capture logits for every token position, not just generated text.
3. Run the candidate adapter/runtime on identical token IDs and compare every logit using tools/mkaos_numerical_parity.py. Start with FP32 reference outputs and document tolerances for BF16/FP16/quantized candidates.
4. Require matching tokenizer IDs and special-token behavior, tensor-name/shape mapping, RoPE parameters, attention/GQA layout, normalization, activation, tied embeddings, KV cache, and stop-token behavior.
5. Store a JSON report with reference/candidate revisions, hashes, max absolute and relative error, cosine similarity, tolerances, and pass/fail. Any missing tensor, tokenizer mismatch, NaN/Inf, or out-of-tolerance output blocks conversion.
6. Only after parity passes should a model-specific exporter or separate compatible inference runtime be proposed.

The first CPU smoke is a reference-runtime baseline and determinism check only. It does NOT compare MKAOSW1 with Hugging Face and cannot establish conversion parity. A cloud-hosted GitHub runner is not the user's physical PC. Model-card license metadata is not a legal review of all training data or a grant of rights beyond that license.
