from __future__ import annotations

from collections import defaultdict
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi

K = 2
RRF_CONSTANT = 60


def load_encoder(model: str, device: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model, device=device)


def normalize_embeddings(values) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    if array.ndim != 2 or not np.isfinite(array).all():
        raise ValueError("Encoder must return a finite two-dimensional array")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if (norms == 0).any():
        raise ValueError("Encoder returned a zero vector")
    return array / norms


def fuse_rankings(indices, lexical, dense) -> list[tuple[int, float]]:
    indices = np.asarray(indices, dtype=np.int64)
    lexical, dense = np.asarray(lexical), np.asarray(dense)
    if lexical.shape != indices.shape or dense.shape != indices.shape:
        raise ValueError("Ranking scores must match the candidate pool")
    if not np.isfinite(lexical).all() or not np.isfinite(dense).all():
        raise ValueError("Ranking scores must be finite")
    scores = np.zeros(len(indices), dtype=np.float64)
    for values in (lexical, dense):
        order = np.lexsort((indices, -values))
        scores[order] += 1.0 / (RRF_CONSTANT + np.arange(1, len(indices) + 1))
    order = np.lexsort((indices, -scores))
    return [(int(indices[i]), float(scores[i])) for i in order]


class HybridRetriever:
    def __init__(self, examples: list[dict], embedding_model: str,
                 embedding_batch_size: int, device: str):
        if not examples:
            raise ValueError("The example library is empty")
        self.examples = examples
        self.tokens = [row["func_before"].split() for row in examples]
        self.pools = defaultdict(list)
        for index, row in enumerate(examples):
            for field in ("repo", "language"):
                value = row.get(field)
                if isinstance(value, str) and value.strip():
                    self.pools[field, value.strip()].append(index)
        self.encoder = load_encoder(embedding_model, device)
        self.embeddings = normalize_embeddings(self.encoder.encode(
            [row["func_before"] for row in examples],
            batch_size=embedding_batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        ))
        if len(self.embeddings) != len(examples):
            raise ValueError("Encoder output does not match the example library")

    @lru_cache(maxsize=16)
    def _bm25(self, pool_key: tuple[str, str]) -> BM25Okapi:
        return BM25Okapi([self.tokens[i] for i in self.pools[pool_key]])

    def _rank(self, query: str, query_vector: np.ndarray,
              pool_key: tuple[str, str]) -> list[tuple[int, float]]:
        indices = self.pools.get(pool_key, [])
        if not indices:
            return []
        lexical = self._bm25(pool_key).get_scores(query.split())
        dense = self.embeddings[indices] @ query_vector
        return fuse_rankings(indices, lexical, dense)

    def retrieve(self, query: dict) -> list[dict]:
        code = query["func_before"]
        vectors = normalize_embeddings(self.encoder.encode(
            [code], convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        ))
        if vectors.shape != (1, self.embeddings.shape[1]):
            raise ValueError("Query embedding has an unexpected shape")
        repo = query.get("repo") or ""
        repo_rank = self._rank(code, vectors[0], ("repo", repo.strip()))
        lang_rank = self._rank(code, vectors[0], ("language", query["language"].strip()))
        selected = [(i, score, "repo") for i, score in repo_rank[:1]]
        seen = {i for i, _, _ in selected}
        for index, score in lang_rank:
            if len(selected) == K:
                break
            if index not in seen:
                selected.append((index, score, "language"))
                seen.add(index)
        return [dict(self.examples[index], example_id=f"example-{index}",
                     selection_pool=pool, rrf_score=score)
                for index, score, pool in selected]
