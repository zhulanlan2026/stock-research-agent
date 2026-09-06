from __future__ import annotations


class TextParser:
    """纯文本解析器，用于 csv / txt / md 等文本文件。"""

    def parse(self, data: bytes, filename: str) -> str:
        return data.decode("utf-8", errors="replace")
