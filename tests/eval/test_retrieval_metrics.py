"""Live retrieval-metrics regression gate (plan "Eval harness" step, Layer 1).

Runs the real embedder + pgvector retriever over the example qrels and asserts
threshold floors. ``@pytest.mark.live`` — skipped offline and self-skips when the
corpus is empty. Thresholds are intentionally loose: the shipped example qrels
are illustrative, so this guards against gross retrieval regressions rather than
certifying a specific corpus's quality (that is the deployer's own qrels job).
"""

from __future__ import annotations

import pytest

from corpus_rag.eval.harness import evaluate_retrieval
from corpus_rag.eval.qrels import load_qrels

EXAMPLE_QRELS = "tests/eval/qrels.example.json"


def _live_retrieve_fn():
    from haystack.components.embedders import SentenceTransformersTextEmbedder
    from haystack_integrations.components.retrievers.pgvector import (
        PgvectorEmbeddingRetriever,
    )

    from corpus_rag.document_store import build_document_store
    from corpus_rag.settings import get_settings

    settings = get_settings()
    store = build_document_store(settings)
    if store.count_documents() == 0:
        pytest.skip("Empty corpus; ingest a sample corpus first (live).")

    embedder = SentenceTransformersTextEmbedder(model=settings.embed_model_id)
    embedder.warm_up()
    retriever = PgvectorEmbeddingRetriever(document_store=store, top_k=settings.top_k)

    def retrieve(query: str):
        embedding = embedder.run(text=query)["embedding"]
        return retriever.run(query_embedding=embedding)["documents"]

    return retrieve, settings.top_k


@pytest.mark.live
def test_live_retrieval_metrics_meet_floor() -> None:
    retrieve, k = _live_retrieve_fn()
    cases = load_qrels(EXAMPLE_QRELS)
    macro, per_case = evaluate_retrieval(cases, retrieve, k=k)

    # Loose gross-regression floors against the illustrative example set.
    assert macro.hit > 0.0, f"no query retrieved any relevant chunk: {macro.as_row()}"
    assert macro.recall > 0.0, f"zero recall across the eval set: {macro.as_row()}"
    # Every query must at least retrieve the requested depth (corpus permitting).
    assert all(c.n_retrieved > 0 for c in per_case)
