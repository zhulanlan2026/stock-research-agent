from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureFlag:
    key: str
    enabled: bool


class FeatureFlagService:
    def __init__(self, flags: dict[str, bool] | None = None) -> None:
        self._flags = dict(flags or {})

    def set_flag(self, key: str, enabled: bool) -> None:
        self._flags[key] = enabled

    def is_enabled(self, key: str) -> bool:
        return self._flags.get(key, False)

    def list_flags(self) -> list[FeatureFlag]:
        return [
            FeatureFlag(key=key, enabled=enabled)
            for key, enabled in sorted(self._flags.items())
        ]
