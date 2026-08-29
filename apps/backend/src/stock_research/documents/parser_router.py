from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParserRoute:
    parser: str
    parser_version: str


class ParserRouter:
    """按扩展名路由到文档解析器，V2.0 第 14.1 节。"""

    def route(self, filename: str | None) -> ParserRoute:
        suffix = Path(filename or "").suffix.lower()
        if suffix == ".pdf":
            return ParserRoute("mineru", "1.0.0")
        if suffix == ".docx":
            return ParserRoute("python-docx", "1.0.0")
        if suffix == ".xlsx":
            return ParserRoute("openpyxl", "1.0.0")
        if suffix in {".html", ".htm", ".xml"}:
            return ParserRoute("lxml", "1.0.0")
        if suffix == ".csv":
            return ParserRoute("csv", "1.0.0")
        raise ValueError(f"unsupported document type: {suffix or 'unknown'}")
