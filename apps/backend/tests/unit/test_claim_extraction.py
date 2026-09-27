from stock_research.supply_chain.claim_extraction import RuleBasedClaimExtractor


def test_rule_based_claim_extractor_finds_contract_relation() -> None:
    claims = RuleBasedClaimExtractor().extract("公司A与公司B签订合同，金额1亿元")

    assert len(claims) == 1
    assert claims[0].subject == "公司A"
    assert claims[0].predicate == "signed_contract_with"
    assert claims[0].object == "公司B"


def test_rule_based_claim_extractor_returns_empty_without_pattern() -> None:
    assert RuleBasedClaimExtractor().extract("普通文本") == []


def test_rule_based_claim_extractor_handles_multiple_sentences() -> None:
    claims = RuleBasedClaimExtractor().extract(
        "公司A向公司B采购原料；公司C向公司D销售产品。"
    )

    assert [(c.subject, c.predicate, c.object) for c in claims] == [
        ("公司A", "procured_from", "公司B"),
        ("公司C", "sold_to", "公司D"),
    ]
