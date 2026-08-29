from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

DOCX_PARSER_VERSION = "python-docx:1.0.0"


class DocxParser:
    """使用 python-docx 解析 DOCX 段落文本。"""

    version = DOCX_PARSER_VERSION

    def parse(self, data: bytes, filename: str) -> str:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / (Path(filename).name or "document.docx")
            path.write_bytes(data)
            return self._parse_path(path)

    def _parse_path(self, path: Path) -> str:
        from docx import Document  # type: ignore[import-not-found]

        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
