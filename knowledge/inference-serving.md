# Inference server failures: vLLM and Triton

## vLLM out of GPU memory

vLLM preallocates GPU memory for weights and the KV cache using `--gpu-memory-utilization` (0.9 by default). Startup fails with `CUDA out of memory` or `No available memory for the cache blocks` when the model weights plus the minimum cache do not fit. Lower `--max-model-len`, use a smaller or quantized model, raise `--gpu-memory-utilization` if nothing else uses the GPU, or add tensor parallelism across GPUs.

## vLLM startup and readiness

vLLM downloads and loads weights before serving, which can take minutes. Use a startup probe against `/health` sized for that time, and keep the Hugging Face cache on a persistent volume so restarts do not re-download. Gated models need an `HF_TOKEN` from a Secret. The OpenAI-compatible API listens on port 8000 by default.

## Triton model repository errors

Triton loads models from `--model-repository`. Each model needs `<model>/config.pbtxt` and a numbered version directory such as `<model>/1/model.onnx`. If a model fails to load, `/v2/health/ready` returns an error and the server logs show the model state as `UNAVAILABLE` with the reason, often a shape or data-type mismatch between `config.pbtxt` and the ONNX graph. `GET /v2/models/<model>` returns the loaded input and output metadata.

## Triton input mismatches

Inference requests must match configured input names, data types, and shapes. With `max_batch_size` greater than zero the first dimension is the batch and is omitted from `dims`. Sending INT32 tokens to an INT64 input or the wrong tensor name produces a 400 error that names the offending input.

## Embedding consistency

Queries and documents must use the same embedding model revision, tokenizer, pooling, and normalization. Mixing models produces vectors in different spaces, which silently ruins retrieval quality. Record the model identifier with the index and rebuild the index when the model changes.
