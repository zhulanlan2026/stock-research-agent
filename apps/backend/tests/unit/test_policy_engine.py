from stock_research.policy.engine import PolicyEngine, PolicyRule


def test_policy_engine_allows_matching_rule() -> None:
    engine = PolicyEngine(
        [
            PolicyRule("allow-admin", "ALLOW", lambda ctx: ctx.get("role") == "admin"),
            PolicyRule("review-risk", "REVIEW", lambda ctx: ctx.get("risk") == "high"),
        ]
    )

    assert engine.evaluate({"role": "admin", "risk": "low"}) == "ALLOW"


def test_policy_engine_defaults_to_deny() -> None:
    engine = PolicyEngine([])

    assert engine.evaluate({"role": "user"}) == "DENY"
