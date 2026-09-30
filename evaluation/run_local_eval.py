"""
Offline local evaluation for the Hybrid RAG pipeline.
No backend, no cloud APIs, no .env needed.

Uses BM25 over the project source files + the HuggingFace cross-encoder
reranker (same model as production) to evaluate retrieval quality against
the existing evaluation/hybrid_rag_eval.json dataset.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

# ── metric helpers (re-use project's own metrics.py) ───────────────────────
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.metrics import summarize

# ── lightweight deps (rank_bm25 + sentence-transformers already in requirements.txt)
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

# ───────────────────────────────────────────────────────────────────────────
DATASET   = ROOT / "evaluation" / "hybrid_rag_eval.json"
RESULTS   = ROOT / "evaluation" / "hybrid_rag_results_local.json"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
K = 5       # top-k after rerank
FETCH_K = 20  # candidates fed to reranker

# ── 1. Index every .py file in the project ─────────────────────────────────
def build_corpus(root: Path) -> list[dict]:
    docs = []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        text = p.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            docs.append({"source": str(rel).replace("\\", "/"), "text": text})
    return docs

# ── 2. BM25 search ─────────────────────────────────────────────────────────
def bm25_search(corpus: list[dict], query: str, n: int) -> list[dict]:
    tokenised = [doc["text"].lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenised)
    scores = bm25.get_scores(query.lower().split())
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
    return [corpus[i] for i in top_idx]

# ── 3. Cross-encoder rerank ────────────────────────────────────────────────
def rerank(cross_enc: CrossEncoder, query: str, candidates: list[dict], top_n: int) -> list[dict]:
    pairs = [(query, d["text"][:512]) for d in candidates]
    ce_scores = cross_enc.predict(pairs)
    ranked = sorted(zip(ce_scores, candidates), key=lambda x: x[0], reverse=True)
    return [d for _, d in ranked[:top_n]]

# ── 4. Source-label match (same logic as run_hybrid_eval.py) ───────────────
def matches(source: str, expected: str) -> bool:
    return expected.lower() in source.lower()

# ── 5. Main ────────────────────────────────────────────────────────────────
def main() -> None:
    print("Building corpus from project .py files...")
    corpus = build_corpus(ROOT)
    print(f"  {len(corpus)} source files indexed.")

    print(f"Loading cross-encoder: {RERANKER_MODEL}")
    cross_enc = CrossEncoder(RERANKER_MODEL)

    data = json.loads(DATASET.read_text(encoding="utf-8"))
    rows = []

    for case in data["cases"]:
        started = time.perf_counter()
        candidates = bm25_search(corpus, case["question"], FETCH_K)
        final = rerank(cross_enc, case["question"], candidates, K)
        latency_ms = (time.perf_counter() - started) * 1000

        sources = [d["source"] for d in final]
        relevant = set(case["relevant"])
        retrieved_labels = [
            expected
            for source in sources
            for expected in relevant
            if matches(source, expected)
        ]

        rows.append({
            "id": case["id"],
            "question": case["question"],
            "retrieved": retrieved_labels,
            "relevant": sorted(relevant),
            "retrieved_sources": sources,
            "latency_ms": round(latency_ms, 2),
        })
        print(f"  [{case['id']}] retrieved: {sources}")

    summary = summarize(rows, k=K)
    output = {"summary": summary, "cases": rows}
    RESULTS.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("\n=== RESULTS ===")
    print(json.dumps(summary, indent=2))
    print(f"\nFull results saved to: {RESULTS}")

if __name__ == "__main__":
    main()
