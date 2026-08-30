from pathlib import Path

from stock_research.documents.parsers.xlsx import XlsxParser


class _FakeXlsxParser(XlsxParser):
    def _parse_path(self, path: Path) -> str:
        return "a\tb\nc\td"


def test_xlsx_parser_uses_openpyxl() -> None:
    assert XlsxParser().version == "openpyxl:1.0.0"


def test_xlsx_parser_writes_temp_file_and_parses() -> None:
    assert _FakeXlsxParser().parse(b"fake xlsx", "report.xlsx") == "a\tb\nc\td"
