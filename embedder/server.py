"""A small embedding server for production (PROPOSAL §12.3, option B).

Serves the official int8 ONNX build of intfloat/multilingual-e5-small (118 MB instead of
470 MB, so it fits a 512 MB free Render instance) with the same API as Hugging Face TEI:
POST /embed {"inputs": [...]} -> [[384 floats], ...] and GET /health. The app's TEI client
therefore works unchanged; only EMBEDDINGS_URL points here.

e5 is used the documented way: mean pooling over real tokens, then L2 normalisation.
The caller adds the "query: " / "passage: " prefixes, exactly as with TEI.

Tokenizing uses the model's own SentencePiece file, not tokenizer.json: the `tokenizers`
library needs about 315 MB for this 250k-piece vocabulary, sentencepiece under 100 MB.
Both give identical ids (checked on Bangla, English, mixed text and 512-token truncation).
"""

import hmac
import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
import sentencepiece as spm
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/model"))
MAX_TOKENS = 512  # the model's limit; longer text is truncated, as TEI does
MAX_INPUTS = 32  # per request (the app's ingest batch size)
# Required on Render, where this service is public: the app sends "Authorization: Bearer <key>"
# (the same scheme as TEI's --api-key). Unset locally, so no key is needed there.
API_KEY = os.environ.get("EMBEDDER_API_KEY", "")
CHUNK = 2  # run the model on a few texts at a time to keep memory flat

options = ort.SessionOptions()
options.intra_op_num_threads = 1  # a free instance has 0.1 CPU
options.inter_op_num_threads = 1
options.enable_cpu_mem_arena = False  # return memory after each run instead of keeping a pool
session = ort.InferenceSession(
    str(MODEL_DIR / "model.onnx"), options, providers=["CPUExecutionProvider"]
)
INPUT_NAMES = {i.name for i in session.get_inputs()}

sentencepiece = spm.SentencePieceProcessor(model_file=str(MODEL_DIR / "sentencepiece.bpe.model"))
BOS, PAD, EOS, UNK = 0, 1, 2, 3  # XLM-R (fairseq) special ids


def token_ids(text: str) -> list[int]:
    """XLM-R ids: SentencePiece ids shifted by one (fairseq offset), its unknown id 0
    mapped to <unk>, cut to fit 512 with <s> ... </s> around."""
    pieces = [UNK if i == 0 else i + 1 for i in sentencepiece.encode(text)]
    return [BOS, *pieces[: MAX_TOKENS - 2], EOS]


def embed(texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for start in range(0, len(texts), CHUNK):
        rows = [token_ids(t) for t in texts[start : start + CHUNK]]
        width = max(len(r) for r in rows)
        ids = np.array([r + [PAD] * (width - len(r)) for r in rows], dtype=np.int64)
        mask = np.array([[1] * len(r) + [0] * (width - len(r)) for r in rows], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in INPUT_NAMES:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = session.run(None, feeds)[0]  # (batch, tokens, 384)
        weights = mask[..., None].astype(np.float32)
        pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
        pooled /= np.linalg.norm(pooled, axis=1, keepdims=True)
        out.extend(pooled.tolist())
    return out


async def embed_route(request: Request) -> Response:
    sent = request.headers.get("authorization", "")
    if API_KEY and not hmac.compare_digest(sent, f"Bearer {API_KEY}"):
        return JSONResponse({"error": "missing or wrong API key"}, status_code=401)
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"error": "body must be JSON"}, status_code=422)
    inputs = body.get("inputs") if isinstance(body, dict) else None
    if isinstance(inputs, str):
        inputs = [inputs]
    if not isinstance(inputs, list) or not inputs or not all(isinstance(t, str) for t in inputs):
        return JSONResponse({"error": "inputs must be a string or a list of strings"}, 422)
    if len(inputs) > MAX_INPUTS:
        return JSONResponse({"error": f"at most {MAX_INPUTS} inputs"}, status_code=413)
    return JSONResponse(await run_in_threadpool(embed, inputs))


async def health(request: Request) -> Response:
    return Response(status_code=200)


app = Starlette(routes=[Route("/embed", embed_route, methods=["POST"]), Route("/health", health)])
