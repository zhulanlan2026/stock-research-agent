from stock_research.documents.parsers.html import HtmlParser


class _FakeHtmlParser(HtmlParser):
    def _parse_bytes(self, data: bytes) -> str:
        return "hello html"


def test_html_parser_uses_lxml() -> None:
    assert HtmlParser().version == "lxml:1.0.0"


def test_html_parser_parses_bytes() -> None:
    assert _FakeHtmlParser().parse(b"<html></html>", "page.html") == "hello html"
