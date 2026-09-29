"""Run retrieval evaluation against the project's real Hybrid RAG retriever.

Requires the same environment variables as the application. The script does
not invent scores: it queries the configured retriever and computes metrics
from the returned source paths.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from evaluation.metrics import summarize
from hybrid_rag_pipeline.rag.retriever.retrieval import retrieve

BASE = Path(__file__).resolve().parent
DATASET = BASE / "hybrid_rag_eval.json"
RESULTS = BASE / "hybrid_rag_results.json"


def source_key(doc) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    return str(metadata.get("source") or metadata.get("file_path") or metadata.get("path") or "").lower()


def matches(source: str, expected: str) -> bool:
    return expected.lower() in source


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    k = int(data.get("k", 5))
    retriever = retrieve(k=k, rerank=True)
    rows = []

    for case in data["cases"]:
        started = time.perf_counter()
        docs = retriever.invoke(case["question"])
        latency_ms = (time.perf_counter() - started) * 1000
        sources = [source_key(doc) for doc in docs]
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

    summary = summarize(rows, k=k)
    output = {"summary": summary, "cases": rows}
    RESULTS.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Results: {RESULTS}")


if __name__ == "__main__":
    main()
