from akshare_collector.sources.symbols import akshare_code, split_symbol, tushare_code


def test_split_symbol_with_suffix() -> None:
    assert split_symbol("600519.SH") == ("600519", "SH")
    assert split_symbol("000001.SZ") == ("000001", "SZ")


def test_split_symbol_infers_exchange() -> None:
    assert split_symbol("600519") == ("600519", "SH")
    assert split_symbol("000001") == ("000001", "SZ")
    assert split_symbol("430047") == ("430047", "BJ")


def test_akshare_code() -> None:
    assert akshare_code("600519.SH") == "600519"


def test_tushare_code() -> None:
    assert tushare_code("600519.SH") == "600519.SH"
    assert tushare_code("000001") == "000001.SZ"
