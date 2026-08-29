from pathlib import Path

from stock_research.documents.parsers.docx import DocxParser


class _FakeDocxParser(DocxParser):
    def _parse_path(self, path: Path) -> str:
        return "hello docx"


def test_docx_parser_uses_python_docx() -> None:
    assert DocxParser().version == "python-docx:1.0.0"


def test_docx_parser_writes_temp_file_and_parses() -> None:
    assert _FakeDocxParser().parse(b"fake docx", "report.docx") == "hello docx"
