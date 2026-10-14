# GPU deployment

The base manifest requests one GPU for vLLM. Triton starts on CPU by default so a single-GPU cluster can run the stack. Before deployment:

1. Install the NVIDIA device plugin and confirm `nvidia.com/gpu` capacity.
2. Pin container image digests and the model revision.
3. Confirm the model license and registry credentials.
4. Export and mount the Triton model repository; the base `emptyDir` is only a wiring placeholder.
5. Measure memory with the chosen precision and context length.

Do not enable `USE_LLM=true` until the vLLM readiness endpoint responds and its chat template produces valid JSON.
