import pytest

from stock_research.documents.chunking import TextChunker


def test_text_chunker_splits_with_overlap() -> None:
    text = "0123456789" * 5

    chunks = TextChunker().chunk_text(text, max_chars=12, overlap=4)

    assert len(chunks) > 1
    assert all(chunk.text for chunk in chunks)
    assert chunks[-1].text.endswith("9")


def test_text_chunker_handles_empty_text() -> None:
    assert TextChunker().chunk_text("   ") == []


def test_text_chunker_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        TextChunker().chunk_text("abc", max_chars=0)
    with pytest.raises(ValueError):
        TextChunker().chunk_text("abc", max_chars=10, overlap=10)
