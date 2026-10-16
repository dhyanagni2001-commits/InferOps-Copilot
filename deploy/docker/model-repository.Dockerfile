# Packages an exported Triton model repository (see inference/triton/) so Kubernetes can
# copy it into Triton and the backend with an init container. Build from the repo root after export:
#   docker build -f deploy/docker/model-repository.Dockerfile -t inferops/model-repository:minilm .
FROM busybox:1.36
COPY model_repository /model_repository
