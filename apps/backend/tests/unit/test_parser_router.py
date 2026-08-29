import pytest

from stock_research.documents.parser_router import ParserRouter


@pytest.mark.parametrize(
    ("filename", "parser"),
    [
        ("report.pdf", "mineru"),
        ("report.docx", "python-docx"),
        ("report.xlsx", "openpyxl"),
        ("report.html", "lxml"),
        ("report.csv", "csv"),
    ],
)
def test_parser_router_selects_expected_parser(filename: str, parser: str) -> None:
    route = ParserRouter().route(filename)

    assert route.parser == parser
    assert route.parser_version == "1.0.0"


def test_parser_router_rejects_unsupported_type() -> None:
    with pytest.raises(ValueError):
        ParserRouter().route("file.zip")
