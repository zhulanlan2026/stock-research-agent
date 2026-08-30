from __future__ import annotations

from dataclasses import dataclass

from stock_research.documents.chunking import TextChunk, TextChunker


@dataclass(frozen=True)
class DocumentAgentResult:
    agent: str
    chunks: list[TextChunk]


class DocumentAgent:
    """文档 Agent 骨架，当前执行确定性分块。"""

    name = "document"

    def __init__(self) -> None:
        self._chunker = TextChunker()

    async def run(self, text: str) -> DocumentAgentResult:
        chunks = self._chunker.chunk_text(text)
        return DocumentAgentResult(agent=self.name, chunks=chunks)
