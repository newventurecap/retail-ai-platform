"""Ingestion and permission-aware retrieval over an Azure AI Search index.

Each application owns its index; this module only provides the pattern. Documents carry
``allowed_groups`` and queries are filtered to the caller's groups (security trimming).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from retail_ai.observability import traced_span
from retail_ai.retrieval.chunking import chunk_text

Embedder = Callable[[Sequence[str]], list[list[float]]]


@dataclass
class Document:
    id: str
    text: str
    allowed_groups: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def ingest(search_client, documents: Sequence[Document], embed: Embedder, *, size: int = 800) -> int:
    """Chunk, embed and upload documents. Returns the number of chunks indexed."""
    records = []
    for doc in documents:
        chunks = chunk_text(doc.text, size=size)
        vectors = embed(chunks)
        for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            records.append(
                {
                    "id": f"{doc.id}-{i}",
                    "parent_id": doc.id,
                    "content": chunk,
                    "content_vector": vector,
                    "allowed_groups": doc.allowed_groups,
                    **doc.metadata,
                }
            )
    if records:
        search_client.upload_documents(documents=records)
    return len(records)


def _groups_filter(groups: Sequence[str]) -> str:
    # Documents with no groups are public; otherwise caller needs at least one matching group.
    quoted = ",".join(g.replace("'", "''") for g in groups)
    clause = "not allowed_groups/any()"
    return f"{clause} or allowed_groups/any(g: search.in(g, '{quoted}', ','))" if quoted else clause


class Retriever:
    def __init__(self, search_client, embed: Embedder, *, top_k: int = 5):
        self._client = search_client
        self._embed = embed
        self._top_k = top_k

    def retrieve(self, query: str, *, user_groups: Sequence[str] = ()) -> list[dict]:
        with traced_span("retrieval.search", top_k=self._top_k):
            vector = self._embed([query])[0]
            results = self._client.search(
                search_text=query,
                vector_queries=[
                    {"kind": "vector", "vector": vector, "fields": "content_vector", "k": self._top_k}
                ],
                filter=_groups_filter(user_groups),
                top=self._top_k,
            )
            return [dict(r) for r in results]
