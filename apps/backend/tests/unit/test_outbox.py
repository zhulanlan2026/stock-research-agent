from stock_research.outbox.keys import build_effect_key
from stock_research.outbox.registry import HandlerRegistry


def test_build_effect_key() -> None:
    assert build_effect_key("report", "rep-1", "published") == "report:rep-1:published"


def test_handler_registry() -> None:
    registry = HandlerRegistry()

    async def noop(payload: dict[str, object]) -> None:
        return None

    registry.register("report.published", noop)
    assert registry.get("report.published") is noop
    assert registry.get("unknown") is None
