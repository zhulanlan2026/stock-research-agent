from stock_research.iam.authorization import (
    AbacContext,
    AbacEnvironment,
    AbacModelPolicy,
    AbacPolicyEngine,
    AbacResource,
    AbacSubject,
)


def test_default_context_is_allowed() -> None:
    context = AbacContext(
        subject=AbacSubject(tenant_id="t1", user_id="u1", roles=frozenset({"PAID_USER"})),
        resource=AbacResource(visibility_scope="PUBLIC"),
    )
    assert AbacPolicyEngine().evaluate(context).decision == "ALLOW"


def test_private_resource_denies_other_owner() -> None:
    context = AbacContext(
        subject=AbacSubject(tenant_id="t1", user_id="u1", roles=frozenset({"PAID_USER"})),
        resource=AbacResource(visibility_scope="PRIVATE", owner_id="u2"),
    )
    decision = AbacPolicyEngine().evaluate(context)
    assert decision.decision == "DENY"
    assert "DATA_SCOPE_DENIED" in decision.reasons


def test_external_model_denies_private_content() -> None:
    context = AbacContext(
        subject=AbacSubject(tenant_id="t1", user_id="u1", roles=frozenset({"PAID_USER"})),
        resource=AbacResource(visibility_scope="PRIVATE", owner_id="u1"),
        model=AbacModelPolicy(external_model_allowed=False),
    )
    decision = AbacPolicyEngine().evaluate(context)
    assert decision.decision == "DENY"
    assert "EXTERNAL_MODEL_DENIED" in decision.reasons


def test_degraded_system_denies() -> None:
    context = AbacContext(
        subject=AbacSubject(tenant_id="t1", user_id="u1", roles=frozenset({"ADMIN"})),
        resource=AbacResource(visibility_scope="PUBLIC"),
        environment=AbacEnvironment(system_health="BLOCK"),
    )
    assert AbacPolicyEngine().evaluate(context).decision == "DENY"
