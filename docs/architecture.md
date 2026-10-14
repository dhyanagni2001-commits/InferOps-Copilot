# Architecture

```text
Browser -> nginx/Vite -> FastAPI SSE -> bounded workflow
                                  |-> read-only kubectl evidence
                                  |-> local documentation index
                                  `-> optional vLLM generation

Ingestion -> deterministic embeddings -> local JSON index -> optional Qdrant mirror
Tokenizer -> Triton embedding model (optional production path)
```

The deterministic workflow remains available when model or retrieval services fail. Evidence IDs originate in application code and are never accepted from generated text. Kubernetes commands use validated resource names and fixed argument lists; generated shell commands are not executed.
