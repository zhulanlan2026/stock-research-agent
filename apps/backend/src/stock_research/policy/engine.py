from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyRule:
    name: str
    decision: str
    condition: Callable[[dict[str, Any]], bool]


class PolicyEngine:
    """确定性 Policy Engine，默认 DENY。"""

    def __init__(self, rules: list[PolicyRule]) -> None:
        self._rules = rules

    def evaluate(self, context: dict[str, Any]) -> str:
        for rule in self._rules:
            if rule.condition(context):
                return rule.decision
        return "DENY"
