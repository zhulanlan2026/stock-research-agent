from __future__ import annotations

HTML_PARSER_VERSION = "lxml:1.0.0"


class HtmlParser:
    """使用 lxml 解析 HTML/XML 文本。"""

    version = HTML_PARSER_VERSION

    def parse(self, data: bytes, filename: str) -> str:
        return self._parse_bytes(data)

    def _parse_bytes(self, data: bytes) -> str:
        from lxml import etree  # type: ignore[import-untyped]

        parser = etree.HTMLParser()
        tree = etree.fromstring(data, parser)
        if tree is None:
            return ""
        text = tree.xpath("string(.)")
        return " ".join(str(text).split())
