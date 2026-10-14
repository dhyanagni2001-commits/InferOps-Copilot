"""Export a mean-pooled Transformer encoder for Triton ONNX Runtime."""

import argparse
from pathlib import Path


def export(model_name: str, output: str) -> None:
    import torch
    from transformers import AutoModel, AutoTokenizer

    class Encoder(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def forward(self, input_ids, attention_mask):
            hidden = self.model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
            mask = attention_mask.unsqueeze(-1).float()
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            return torch.nn.functional.normalize(pooled, p=2, dim=1)

    target = Path(output)
    version = target / "1"
    version.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = Encoder(AutoModel.from_pretrained(model_name)).eval()
    sample = tokenizer(["sample text"], padding="max_length", max_length=32, return_tensors="pt")
    torch.onnx.export(
        model, (sample["input_ids"], sample["attention_mask"]), version / "model.onnx",
        input_names=["input_ids", "attention_mask"], output_names=["embeddings"],
        dynamic_axes={"input_ids": {0: "batch", 1: "tokens"}, "attention_mask": {0: "batch", 1: "tokens"}, "embeddings": {0: "batch"}},
        opset_version=17,
    )
    tokenizer.save_pretrained(target / "tokenizer")
    hidden = model.model.config.hidden_size
    (target / "config.pbtxt").write_text(
        f'name: "embedding"\nplatform: "onnxruntime_onnx"\nmax_batch_size: 32\n'
        f'input [{{ name: "input_ids" data_type: TYPE_INT64 dims: [-1] }}, {{ name: "attention_mask" data_type: TYPE_INT64 dims: [-1] }}]\n'
        f'output [{{ name: "embeddings" data_type: TYPE_FP32 dims: [{hidden}] }}]\n'
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    export(args.model, args.output)
