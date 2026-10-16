"""Export a mean-pooled, L2-normalized sentence encoder to ONNX for Triton, then validate it.

Pooling and normalization live inside the ONNX graph, so Triton returns final embeddings and
clients only tokenize. Run in a separate model-build environment:

    pip install torch transformers onnx onnxruntime onnxscript
    python inference/triton/export_embedding_model.py \
        --model sentence-transformers/all-MiniLM-L6-v2 --revision <commit> --output model_repository/embedding
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

VALIDATION_TEXTS = [
    "Container was OOMKilled after exceeding its memory limit.",
    "Readiness probe failed: HTTP probe failed with statuscode: 404",
    "kube",
    "Service targetPort 9999 does not match containerPort 80, so connections are refused by every backend pod.",
]


def export(model_name: str, revision: str, output: str, max_batch: int) -> dict:
    import numpy as np
    import onnxruntime
    import torch
    from transformers import AutoModel, AutoTokenizer

    class Encoder(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, input_ids, attention_mask):
            hidden = self.model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
            mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            return torch.nn.functional.normalize(pooled, p=2, dim=1)

    target = Path(output)
    version_dir = target / "1"
    version_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name, revision=revision)
    model = Encoder(AutoModel.from_pretrained(model_name, revision=revision)).eval()
    sample = tokenizer(VALIDATION_TEXTS[:2], padding=True, return_tensors="pt")
    torch.onnx.export(
        model, (sample["input_ids"], sample["attention_mask"]), str(version_dir / "model.onnx"),
        input_names=["input_ids", "attention_mask"], output_names=["embeddings"],
        dynamic_axes={"input_ids": {0: "batch", 1: "tokens"}, "attention_mask": {0: "batch", 1: "tokens"}, "embeddings": {0: "batch"}},
        opset_version=17, dynamo=False,
    )
    tokenizer.save_pretrained(target / "tokenizer")
    hidden = model.model.config.hidden_size
    (target / "config.pbtxt").write_text(f"""name: "{target.name}"
backend: "onnxruntime"
max_batch_size: {max_batch}
input [
  {{ name: "input_ids" data_type: TYPE_INT64 dims: [ -1 ] }},
  {{ name: "attention_mask" data_type: TYPE_INT64 dims: [ -1 ] }}
]
output [
  {{ name: "embeddings" data_type: TYPE_FP32 dims: [ {hidden} ] }}
]
dynamic_batching {{ max_queue_delay_microseconds: 2000 }}
instance_group [ {{ kind: KIND_CPU count: 1 }} ]
""")

    # Validate: ONNX Runtime output must match the PyTorch source model.
    batch = tokenizer(VALIDATION_TEXTS, padding=True, truncation=True, max_length=256, return_tensors="pt")
    with torch.no_grad():
        reference = model(batch["input_ids"], batch["attention_mask"]).numpy()
    session = onnxruntime.InferenceSession(str(version_dir / "model.onnx"), providers=["CPUExecutionProvider"])
    exported = session.run(None, {"input_ids": batch["input_ids"].numpy(), "attention_mask": batch["attention_mask"].numpy()})[0]
    cosine = (reference * exported).sum(1) / (np.linalg.norm(reference, axis=1) * np.linalg.norm(exported, axis=1))
    report = {
        "model": model_name, "revision": revision, "hidden_size": hidden,
        "max_abs_diff": float(np.abs(reference - exported).max()), "min_cosine": float(cosine.min()),
        "torch": torch.__version__, "onnxruntime": onnxruntime.__version__,
    }
    (target / "export-report.json").write_text(json.dumps(report, indent=2))
    if report["min_cosine"] < 0.9999:
        raise SystemExit(f"exported model diverges from source: {report}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
    parser.add_argument("--revision", default="c9745ed1d9f207416be6d2e6f8de32d1f16199bf")
    parser.add_argument("--output", default="model_repository/embedding")
    parser.add_argument("--max-batch", type=int, default=32)
    args = parser.parse_args()
    print(json.dumps(export(args.model, args.revision, args.output, args.max_batch), indent=2))
