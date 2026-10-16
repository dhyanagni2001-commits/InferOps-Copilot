# Triton embeddings

The exported model is `sentence-transformers/all-MiniLM-L6-v2` at a pinned revision. Mean pooling and L2 normalization are part of the ONNX graph; the backend tokenizes with the saved `tokenizer.json` (Rust `tokenizers`, 256-token truncation) and sends `input_ids` and `attention_mask` (INT64). Triton returns `embeddings` (FP32, 384).

```bash
# Model-build environment (kept separate from the backend):
pip install torch transformers onnx onnxruntime onnxscript sentence-transformers
python inference/triton/export_embedding_model.py           # exports and fails if ONNX != PyTorch
docker run --rm -p 8002:8000 -v "$PWD/model_repository:/models:ro" nvcr.io/nvidia/tritonserver:25.08-py3 \
  tritonserver --model-repository=/models
PYTHONPATH=backend TRITON_HTTP_URL=http://127.0.0.1:8002 python inference/triton/validate_triton.py
```

Layout written by the export:

```text
model_repository/embedding/
  config.pbtxt            # onnxruntime backend, max_batch_size 32, dynamic batching, KIND_CPU
  1/model.onnx
  tokenizer/tokenizer.json
  export-report.json      # model, revision, numerical comparison
```

Then build the index with `python -m ingestion.build_index --embedding-backend triton` (add `--qdrant-url`), and run the backend with `EMBEDDING_BACKEND=triton`.
