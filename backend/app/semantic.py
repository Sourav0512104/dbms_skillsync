
import os
import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer, CrossEncoder

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "BAAI/bge-small-en-v1.5"
)

RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL",
    "cross-encoder/ms-marco-MiniLM-L6-v2"
)

# Explicitly run both models on CPU.
DEVICE = "cpu"


@lru_cache(maxsize=1)
def embedding_model():
    return SentenceTransformer(
        EMBEDDING_MODEL,
        device=DEVICE
    )


@lru_cache(maxsize=1)
def reranker():
    return CrossEncoder(
        RERANKER_MODEL,
        device=DEVICE
    )


def embed(texts):
    if isinstance(texts, str):
        texts = [texts]

    return np.asarray(
        embedding_model().encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        ),
        dtype=np.float32
    )


def cosine(a, b):
    a = np.asarray(a)
    b = np.asarray(b)

    return float(
        np.dot(a, b) /
        (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
    )


def rerank(query, docs):
    return [
        float(x)
        for x in reranker().predict(
            [(query, d) for d in docs]
        )
    ]
