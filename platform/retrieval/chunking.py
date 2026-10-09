def chunk_text(text: str, *, size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping character chunks, preferring whitespace boundaries."""
    if size <= overlap:
        raise ValueError("size must be greater than overlap")
    text = text.strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size - overlap, end)
            end = boundary if boundary > start else end
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]
