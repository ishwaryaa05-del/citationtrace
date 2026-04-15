"""
Citation verification module using sentence-transformers cosine similarity.
Determines whether a claim is supported by its cited paper abstract.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple

# Lazy-loaded model to avoid loading at import time in tests
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two 1-D vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def verify_citation(claim_text: str, abstract: str) -> Tuple[float, bool]:
    """
    Verify whether *claim_text* is supported by *abstract*.

    Returns
    -------
    confidence_score : float
        Cosine similarity between claim and abstract embeddings (0–1).
    verified : bool
        True when confidence_score >= 0.35.
    """
    model = _get_model()
    embeddings = model.encode([claim_text, abstract], convert_to_numpy=True)
    score = cosine_similarity(embeddings[0], embeddings[1])
    # Clamp to [0, 1] to guard against floating-point edge cases
    score = float(np.clip(score, 0.0, 1.0))
    verified = score >= 0.35
    return score, verified


def verify_citations_batch(
    pairs: list[Tuple[str, str]]
) -> list[Tuple[float, bool]]:
    """
    Verify multiple (claim, abstract) pairs in a single batch encode call
    for efficiency.

    Parameters
    ----------
    pairs : list of (claim_text, abstract) tuples

    Returns
    -------
    list of (confidence_score, verified) tuples in the same order as *pairs*.
    """
    if not pairs:
        return []

    model = _get_model()
    claims = [p[0] for p in pairs]
    abstracts = [p[1] for p in pairs]

    all_texts = claims + abstracts
    all_embeddings = model.encode(all_texts, convert_to_numpy=True)

    n = len(pairs)
    claim_embeddings = all_embeddings[:n]
    abstract_embeddings = all_embeddings[n:]

    results = []
    for c_emb, a_emb in zip(claim_embeddings, abstract_embeddings):
        score = cosine_similarity(c_emb, a_emb)
        score = float(np.clip(score, 0.0, 1.0))
        results.append((score, score >= 0.35))

    return results
