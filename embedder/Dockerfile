# Int8 embedder for production (PROPOSAL §12.3 option B). Model files are pinned to one
# repo revision and checked by SHA-256, so the build always serves the same weights.
FROM python:3.12-slim AS model
ARG REVISION=614241f622f53c4eeff9890bdc4f31cfecc418b3
ARG BASE=https://huggingface.co/intfloat/multilingual-e5-small/resolve/${REVISION}/onnx
ADD --checksum=sha256:dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88 \
    ${BASE}/model_qint8_avx512_vnni.onnx /model/model.onnx
ADD --checksum=sha256:cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865 \
    ${BASE}/sentencepiece.bpe.model /model/sentencepiece.bpe.model
# ADD from a URL saves files readable by root only; the server runs as a non-root user.
RUN chmod -R a+rX /model

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MODEL_DIR=/model
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
    && useradd --system --uid 10001 embedder
COPY --from=model /model /model
COPY server.py .
USER embedder
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
