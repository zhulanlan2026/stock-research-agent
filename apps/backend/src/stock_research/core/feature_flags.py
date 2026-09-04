from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FeatureFlag:
    key: str
    enabled: bool


@dataclass(frozen=True)
class FeatureFlagConfig:
    key: str
    enabled: bool = False
    percentage: int = 100
    tenant_allowlist: frozenset[str] = frozenset()
    user_allowlist: frozenset[str] = frozenset()
    kill_switch: bool = False
    start_at: datetime | None = None
    end_at: datetime | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.percentage <= 100:
            raise ValueError("percentage must be between 0 and 100")


class FeatureFlagService:
    def __init__(
        self,
        flags: dict[str, bool] | None = None,
        configs: dict[str, FeatureFlagConfig] | None = None,
    ) -> None:
        self._flags = dict(flags or {})
        self._configs = dict(configs or {})

    def set_flag(self, key: str, enabled: bool) -> None:
        self._flags[key] = enabled

    def is_enabled(
        self,
        key: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        config = self._configs.get(key)
        if config is not None:
            return _evaluate(
                config,
                tenant_id=tenant_id,
                user_id=user_id,
                now=now,
            )
        return self._flags.get(key, False)

    def list_flags(self) -> list[FeatureFlag]:
        keys = set(self._flags) | set(self._configs)
        result: list[FeatureFlag] = []
        for key in sorted(keys):
            config = self._configs.get(key)
            enabled = config.enabled if config is not None else self._flags.get(key, False)
            result.append(FeatureFlag(key=key, enabled=enabled))
        return result


def _evaluate(
    config: FeatureFlagConfig,
    *,
    tenant_id: str | None,
    user_id: str | None,
    now: datetime | None,
) -> bool:
    if config.kill_switch:
        return False
    if config.enabled:
        return True
    if user_id is not None and user_id in config.user_allowlist:
        return True
    if tenant_id is not None and tenant_id in config.tenant_allowlist:
        return True
    if config.start_at is not None and (now is None or now < config.start_at):
        return False
    if config.end_at is not None and (now is None or now >= config.end_at):
        return False
    if config.percentage <= 0:
        return False
    if config.percentage >= 100:
        return True
    if user_id is None and tenant_id is None:
        return False
    seed = user_id or tenant_id or ""
    return _bucket(config.key, seed) < config.percentage


def _bucket(key: str, seed: str) -> int:
    digest = hashlib.sha256(f"{key}:{seed}".encode()).hexdigest()
    return int(digest[:8], 16) % 100
