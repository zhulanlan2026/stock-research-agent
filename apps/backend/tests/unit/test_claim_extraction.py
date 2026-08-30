from stock_research.supply_chain.claim_extraction import RuleBasedClaimExtractor


def test_rule_based_claim_extractor_finds_contract_relation() -> None:
    claims = RuleBasedClaimExtractor().extract("公司A与公司B签订合同，金额1亿元")

    assert len(claims) == 1
    assert claims[0].subject == "公司A"
    assert claims[0].predicate == "signed_contract_with"
    assert claims[0].object == "公司B"


def test_rule_based_claim_extractor_returns_empty_without_pattern() -> None:
    assert RuleBasedClaimExtractor().extract("普通文本") == []
