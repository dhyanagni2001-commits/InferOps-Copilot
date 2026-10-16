FROM python:3.12-slim AS kubectl
ARG KUBECTL_VERSION=v1.37.0
# Download a pinned kubectl for the build platform and verify the published checksum.
RUN arch="$(dpkg --print-architecture)" && python -c "import hashlib, sys, urllib.request; \
url = f'https://dl.k8s.io/release/{sys.argv[1]}/bin/linux/{sys.argv[2]}/kubectl'; \
binary = urllib.request.urlopen(url).read(); \
expected = urllib.request.urlopen(url + '.sha256').read().decode().split()[0]; \
assert hashlib.sha256(binary).hexdigest() == expected, 'kubectl checksum mismatch'; \
open('/kubectl', 'wb').write(binary)" "${KUBECTL_VERSION}" "$arch" && chmod 0755 /kubectl

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
RUN pip install "./backend[triton]"
COPY ingestion ingestion
COPY knowledge knowledge
# Bake the offline (hash-embedding) docs index so retrieval works without external services.
RUN python -m ingestion.build_index --output /app/data/docs-index.json
COPY --from=kubectl /kubectl /usr/local/bin/kubectl
ENV DOCS_INDEX_PATH=/app/data/docs-index.json
USER 65532:65532
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--timeout-graceful-shutdown", "10"]
