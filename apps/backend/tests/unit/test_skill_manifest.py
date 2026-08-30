from stock_research.skills.manifest import SkillManifest, SkillManifestRegistry


def test_skill_manifest_registry_registers_and_gets() -> None:
    registry = SkillManifestRegistry()
    registry.register(
        SkillManifest(
            name="supply_chain",
            version="1.0.0",
            execution_type="deterministic_engine",
            required_scopes=frozenset({"skill.supply_chain.execute"}),
            side_effect="NONE",
            external_model_allowed=False,
        )
    )

    manifest = registry.get("supply_chain")

    assert manifest is not None
    assert manifest.version == "1.0.0"
    assert manifest.external_model_allowed is False


def test_skill_manifest_registry_returns_none_for_missing() -> None:
    assert SkillManifestRegistry().get("missing") is None
