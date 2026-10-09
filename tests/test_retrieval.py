from unittest.mock import MagicMock

import pytest
from retail_ai.retrieval import Document, Retriever, chunk_text, ingest


def fake_embed(texts):
    return [[float(len(t))] for t in texts]


def test_chunking_overlaps_and_covers_text():
    text = " ".join(f"word{i}" for i in range(300))
    chunks = chunk_text(text, size=200, overlap=40)
    assert len(chunks) > 1 and all(len(c) <= 200 for c in chunks)
    assert chunks[0].startswith("word0") and chunks[-1].endswith("word299")


def test_chunking_rejects_bad_params():
    with pytest.raises(ValueError):
        chunk_text("x", size=10, overlap=10)


def test_ingest_uploads_records_with_groups():
    client = MagicMock()
    n = ingest(client, [Document("p1", "return policy text", allowed_groups=["staff"])], fake_embed)
    records = client.upload_documents.call_args.kwargs["documents"]
    assert n == len(records) == 1
    assert records[0]["parent_id"] == "p1" and records[0]["allowed_groups"] == ["staff"]


def test_retrieve_applies_security_filter():
    client = MagicMock()
    client.search.return_value = [{"content": "a"}]
    out = Retriever(client, fake_embed).retrieve("refund?", user_groups=["staff", "o'brien"])
    assert out == [{"content": "a"}]
    flt = client.search.call_args.kwargs["filter"]
    assert "staff,o''brien" in flt and "not allowed_groups/any()" in flt


def test_retrieve_without_groups_only_public():
    client = MagicMock()
    client.search.return_value = []
    Retriever(client, fake_embed).retrieve("x")
    assert client.search.call_args.kwargs["filter"] == "not allowed_groups/any()"
