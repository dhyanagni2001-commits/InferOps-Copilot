# Triton embeddings

`export_embedding_model.py` exports a sentence-transformer compatible model to the expected repository layout. Install PyTorch, Transformers, and ONNX in a separate model-build environment, then run:

```bash
python inference/triton/export_embedding_model.py --model sentence-transformers/all-MiniLM-L6-v2 --output model_repository/embedding
tritonserver --model-repository model_repository
```

The backend HTTP client expects `input_ids` and `attention_mask` INT64 tensors and an `embeddings` FP32 output.
