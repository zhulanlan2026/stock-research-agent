import pytest

from stock_research.policy.engine import PolicyEngine, PolicyRule
from stock_research.retrieval.acl import AccessContext, AclFilter, DocumentAccess
from stock_research.skills.gateway import SkillCallContext, SkillDeniedError, SkillGateway
from stock_research.skills.manifest import SkillManifest
from stock_research.supply_chain.graph_candidate import GraphCandidate
from stock_research.supply_chain.graph_review import GraphReviewService


async def test_skill_gateway_denies_missing_scope() -> None:
    gateway = SkillGateway()
    gateway.register_skill(
        SkillManifest(
            name="dangerous",
            version="1.0.0",
            execution_type="deterministic_engine",
            required_scopes=frozenset({"skill.dangerous.execute"}),
            side_effect="FORMAL",
            external_model_allowed=False,
        ),
        lambda: None,
    )

    with pytest.raises(SkillDeniedError):
        await gateway.execute(
            "dangerous",
            SkillCallContext(scopes=frozenset(), agent="research"),
        )


def test_policy_engine_defaults_to_deny() -> None:
    assert PolicyEngine([]).evaluate({"risk": "high"}) == "DENY"
    assert (
        PolicyEngine(
            [PolicyRule("allow", "ALLOW", lambda ctx: ctx.get("approved") is True)]
        ).evaluate({"approved": True})
        == "ALLOW"
    )


def test_acl_denies_cross_tenant() -> None:
    context = AccessContext(
        tenant_id="tenant-1",
        user_id="user-1",
        allowed_visibility=frozenset({"PUBLIC"}),
        allowed_licenses=frozenset(),
        allowed_symbols=frozenset(),
    )
    document = DocumentAccess(
        doc_id="doc-1",
        tenant_id="tenant-2",
        owner_id="user-1",
        visibility_scope="PUBLIC",
        license_policy_id=None,
        symbol=None,
        available_at=None,
    )

    assert AclFilter().filter([document], context) == []


def test_graph_review_requires_evidence() -> None:
    candidate = GraphCandidate(nodes=["A", "B"], edges=[("A", "edge", "B")])

    assert GraphReviewService().review(candidate, []).status == "REJECTED"
