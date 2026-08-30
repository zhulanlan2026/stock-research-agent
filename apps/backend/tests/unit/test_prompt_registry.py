import pytest

from stock_research.model_gateway.prompt_registry import PromptRegistry, PromptTemplate


def test_prompt_registry_renders_template() -> None:
    registry = PromptRegistry()
    registry.register(
        PromptTemplate(
            name="research",
            version="1.0.0",
            template="研究 ${symbol}",
            variables=frozenset({"symbol"}),
        )
    )

    assert registry.render("research", "1.0.0", {"symbol": "600519.SH"}) == "研究 600519.SH"


def test_prompt_registry_rejects_missing_variable() -> None:
    registry = PromptRegistry()
    registry.register(
        PromptTemplate(
            name="research",
            version="1.0.0",
            template="研究 ${symbol}",
            variables=frozenset({"symbol"}),
        )
    )

    with pytest.raises(ValueError):
        registry.render("research", "1.0.0", {})
