from stock_research.supply_chain.skill import SupplyChainSkill


def test_supply_chain_skill_manifest_is_deny_by_default() -> None:
    manifest = SupplyChainSkill.manifest

    assert manifest.name == "supply_chain"
    assert manifest.execution_type == "deterministic_engine"
    assert manifest.external_model_allowed is False
    assert manifest.side_effect == "NONE"


def test_supply_chain_skill_builds_graph_candidate() -> None:
    candidate = SupplyChainSkill().execute("公司A与公司B签订合同")

    assert candidate.nodes == ["公司A", "公司B"]
    assert candidate.edges == [("公司A", "signed_contract_with", "公司B")]
