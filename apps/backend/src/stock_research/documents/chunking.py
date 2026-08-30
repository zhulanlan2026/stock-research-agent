from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    index: int
    text: str
    content_hash: str


class TextChunker:
    """按字符数 + 重叠窗口做确定性文本分块。"""

    def chunk_text(
        self,
        text: str,
        *,
        max_chars: int = 1000,
        overlap: int = 100,
    ) -> list[TextChunk]:
        if max_chars <= 0:
            raise ValueError("max_chars must be positive")
        if overlap < 0 or overlap >= max_chars:
            raise ValueError("overlap must be between 0 and max_chars")

        text = text.strip()
        if not text:
            return []

        chunks: list[TextChunk] = []
        start = 0
        index = 0
        step = max_chars - overlap
        while start < len(text):
            end = min(start + max_chars, len(text))
            piece = text[start:end]
            if piece:
                chunks.append(
                    TextChunk(
                        chunk_id=_chunk_id(piece, index),
                        index=index,
                        text=piece,
                        content_hash=hashlib.sha256(piece.encode("utf-8")).hexdigest(),
                    )
                )
                index += 1
            if end == len(text):
                break
            start += step
        return chunks


def _chunk_id(text: str, index: int) -> str:
    digest = hashlib.sha256(f"{index}:{text}".encode()).hexdigest()
    return f"chunk:{digest}"
