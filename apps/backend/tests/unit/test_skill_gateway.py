import pytest

from stock_research.skills.gateway import SkillCallContext, SkillDeniedError, SkillGateway
from stock_research.skills.manifest import SkillManifest


async def test_skill_gateway_allows_with_required_scope() -> None:
    gateway = SkillGateway()
    gateway.register_skill(
        SkillManifest(
            name="test",
            version="1.0.0",
            execution_type="deterministic_engine",
            required_scopes=frozenset({"skill.test.execute"}),
            side_effect="NONE",
            external_model_allowed=False,
        ),
        lambda text: text.upper(),
    )

    result = await gateway.execute(
        "test",
        SkillCallContext(scopes=frozenset({"skill.test.execute"}), agent="research"),
        text="hello",
    )

    assert result == "HELLO"


async def test_skill_gateway_denies_missing_scope() -> None:
    gateway = SkillGateway()
    gateway.register_skill(
        SkillManifest(
            name="test",
            version="1.0.0",
            execution_type="deterministic_engine",
            required_scopes=frozenset({"skill.test.execute"}),
            side_effect="NONE",
            external_model_allowed=False,
        ),
        lambda text: text,
    )

    with pytest.raises(SkillDeniedError):
        await gateway.execute(
            "test",
            SkillCallContext(scopes=frozenset(), agent="research"),
            text="hello",
        )
