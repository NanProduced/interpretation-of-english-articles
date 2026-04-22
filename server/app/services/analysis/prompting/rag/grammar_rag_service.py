"""Grammar RAG service — reserved entry point.

Per grammar-rag-design.md, this module will implement:
- Build query_text from prepared sentences
- Call Bailian Embedding
- Query Zilliz ANN search
- Call Bailian Rerank
- Return final ExampleEntry list

Current status: placeholder. RAG is not yet online.
When implemented, this module will be called from
example_strategy._resolve_rag_examples().
"""

from __future__ import annotations

from app.services.analysis.prompting.example_strategy import ExampleEntry


async def query_grammar_rag(
    variant: str,
    sentences: list[dict],
    output_type: str = "grammar_note",
    top_k: int = 5,
) -> list[ExampleEntry]:
    raise NotImplementedError("Grammar RAG service is not yet implemented")
