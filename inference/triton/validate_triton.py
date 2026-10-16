"""Compare the deployed Triton embedding path with the reference sentence-transformers model.

This checks the full client path the backend uses: Rust `tokenizers` tokenization, Triton
inference, and in-graph pooling. Run in the model-build environment with the backend on the path:

    PYTHONPATH=backend TRITON_HTTP_URL=http://127.0.0.1:8002 \
        python inference/triton/validate_triton.py --repository model_repository/embedding
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

TEXTS = [
    "Container was OOMKilled after exceeding its memory limit.",
    "Readiness probe failed: HTTP probe failed with statuscode: 404",
    "Back-off pulling image example.invalid/inferops/missing:never",
    "ok",
    # Longer than the 256-token window, so truncation must match too.
    " ".join(["The kubelet restarted the inference container after a liveness probe timeout."] * 40),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default="model_repository/embedding")
    parser.add_argument("--output", default="evaluation/results/triton-validation.json")
    args = parser.parse_args()

    import numpy as np
    from sentence_transformers import SentenceTransformer

    from app.retrieval.embeddings import TritonEmbedder

    report = json.loads((Path(args.repository) / "export-report.json").read_text())
    reference_model = SentenceTransformer(report["model"], revision=report["revision"], device="cpu")
    reference = reference_model.encode(TEXTS, normalize_embeddings=True)
    embedder = TritonEmbedder(tokenizer_path=str(Path(args.repository) / "tokenizer" / "tokenizer.json"),
                              max_tokens=reference_model.max_seq_length)
    served = np.array(embedder.embed(TEXTS))
    cosine = (reference * served).sum(1) / (np.linalg.norm(reference, axis=1) * np.linalg.norm(served, axis=1))
    result = {
        "model": report["model"], "revision": report["revision"], "triton_model_id": embedder.model_id,
        "texts": len(TEXTS), "max_seq_length": reference_model.max_seq_length,
        "min_cosine": float(cosine.min()), "max_abs_diff": float(np.abs(reference - served).max()),
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["min_cosine"] < 0.999:
        raise SystemExit("Triton embeddings diverge from the reference model")


if __name__ == "__main__":
    main()
