from __future__ import annotations


def split_symbol(symbol: str) -> tuple[str, str]:
    """把 '600519.SH' 拆成 ('600519', 'SH')，也兼容不带交易所后缀的代码。"""
    text = symbol.strip()
    if "." in text:
        code, exchange = text.split(".", 1)
        return code.strip(), exchange.strip().upper()
    if text.startswith(("6", "9")):
        return text, "SH"
    if text.startswith(("0", "2", "3")):
        return text, "SZ"
    if text.startswith(("4", "8")):
        return text, "BJ"
    return text, ""


def akshare_code(symbol: str) -> str:
    return split_symbol(symbol)[0]


def tushare_code(symbol: str) -> str:
    code, exchange = split_symbol(symbol)
    if not exchange:
        return code
    return f"{code}.{exchange}"
