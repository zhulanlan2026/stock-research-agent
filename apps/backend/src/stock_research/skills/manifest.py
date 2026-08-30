from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    execution_type: str
    required_scopes: frozenset[str]
    side_effect: str
    external_model_allowed: bool


class SkillManifestRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, SkillManifest] = {}

    def register(self, manifest: SkillManifest) -> None:
        self._manifests[manifest.name] = manifest

    def get(self, name: str) -> SkillManifest | None:
        return self._manifests.get(name)
