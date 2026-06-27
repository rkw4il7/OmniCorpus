"""Pure retrieval-metric math (Layer 1). No I/O, no models — fully offline.

All ranked-list metrics operate on a list of per-rank relevance flags
(``flags[i]`` is ``True`` iff the document at rank ``i`` is relevant), most-
relevant first. Recall is computed separately from a *covered / total* count
because, with chunk-boundary drift, one gold item can match several chunks and
one chunk can match several gold items — so recall must count distinct gold
items covered, not relevant documents retrieved.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


def precision_at_k(flags: Sequence[bool], k: int) -> float:
    """Fraction of the top-``k`` retrieved documents that are relevant."""
    if k <= 0:
        raise ValueError("k must be >= 1")
    top = flags[:k]
    return sum(1 for f in top if f) / k


def recall_at_k(covered: int, total_relevant: int) -> float:
    """Fraction of gold-relevant items covered by the top-``k`` retrieval.

    :param covered: Distinct gold items with >=1 matching doc in the top-k.
    :param total_relevant: Total distinct gold items for the query.
    """
    if total_relevant <= 0:
        return 0.0
    return covered / total_relevant


def hit_at_k(flags: Sequence[bool], k: int) -> float:
    """1.0 if any of the top-``k`` documents is relevant, else 0.0."""
    if k <= 0:
        raise ValueError("k must be >= 1")
    return 1.0 if any(flags[:k]) else 0.0


def reciprocal_rank(flags: Sequence[bool]) -> float:
    """Reciprocal of the rank (1-based) of the first relevant document, else 0."""
    for i, f in enumerate(flags, start=1):
        if f:
            return 1.0 / i
    return 0.0


def ndcg_at_k(flags: Sequence[bool], k: int, total_relevant: int) -> float:
    """Normalised DCG@k with binary gains.

    DCG uses gain 1 for each relevant doc, discounted by ``1/log2(rank+1)``. The
    ideal DCG places ``min(total_relevant, k)`` relevant docs at the top ranks.
    """
    if k <= 0:
        raise ValueError("k must be >= 1")
    dcg = sum(1.0 / math.log2(i + 1) for i, f in enumerate(flags[:k], start=1) if f)
    ideal_hits = min(total_relevant, k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


@dataclass(frozen=True)
class RetrievalMetrics:
    """Per-query or macro-averaged retrieval metrics at a fixed ``k``."""

    k: int
    precision: float
    recall: float
    mrr: float
    ndcg: float
    hit: float
    n_queries: int = 1

    def as_row(self) -> dict[str, float | int]:
        """Flat dict for table/JSON rendering."""
        return {
            "k": self.k,
            "queries": self.n_queries,
            "precision@k": round(self.precision, 4),
            "recall@k": round(self.recall, 4),
            "mrr": round(self.mrr, 4),
            "ndcg@k": round(self.ndcg, 4),
            "hit@k": round(self.hit, 4),
        }


def per_query(
    flags: Sequence[bool], *, k: int, covered: int, total_relevant: int
) -> RetrievalMetrics:
    """Compute all metrics for a single query's ranked relevance flags."""
    return RetrievalMetrics(
        k=k,
        precision=precision_at_k(flags, k),
        recall=recall_at_k(covered, total_relevant),
        mrr=reciprocal_rank(flags),
        ndcg=ndcg_at_k(flags, k, total_relevant),
        hit=hit_at_k(flags, k),
        n_queries=1,
    )


def aggregate(per_query_metrics: Sequence[RetrievalMetrics]) -> RetrievalMetrics:
    """Macro-average a list of per-query metrics (equal weight per query)."""
    n = len(per_query_metrics)
    if n == 0:
        raise ValueError("cannot aggregate zero queries")
    k = per_query_metrics[0].k
    if any(m.k != k for m in per_query_metrics):
        raise ValueError("cannot aggregate metrics computed at different k")
    return RetrievalMetrics(
        k=k,
        precision=sum(m.precision for m in per_query_metrics) / n,
        recall=sum(m.recall for m in per_query_metrics) / n,
        mrr=sum(m.mrr for m in per_query_metrics) / n,
        ndcg=sum(m.ndcg for m in per_query_metrics) / n,
        hit=sum(m.hit for m in per_query_metrics) / n,
        n_queries=n,
    )
