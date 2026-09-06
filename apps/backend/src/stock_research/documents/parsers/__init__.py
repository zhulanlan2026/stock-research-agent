"""Document parser adapters."""

from typing import Protocol

from stock_research.documents.parsers.docx import DocxParser
from stock_research.documents.parsers.html import HtmlParser
from stock_research.documents.parsers.mineru import MinerUPdfParser
from stock_research.documents.parsers.text import TextParser
from stock_research.documents.parsers.xlsx import XlsxParser


class Parser(Protocol):
    def parse(self, data: bytes, filename: str) -> str:
        ...


def parser_for(parser_name: str) -> Parser:
    if parser_name == "mineru":
        return MinerUPdfParser()
    if parser_name == "python-docx":
        return DocxParser()
    if parser_name == "openpyxl":
        return XlsxParser()
    if parser_name == "lxml":
        return HtmlParser()
    if parser_name in {"csv", "text"}:
        return TextParser()
    raise ValueError(f"unsupported parser: {parser_name}")
