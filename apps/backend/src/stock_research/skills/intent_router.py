from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentRoute:
    intent: str
    agent: str


class IntentRouter:
    """确定性意图路由，后续可替换为模型路由。"""

    def route(self, text: str) -> IntentRoute:
        if "文档" in text or "文件" in text:
            return IntentRoute("document", "document")
        if "报告" in text or "研报" in text:
            return IntentRoute("report", "report")
        if "审核" in text or "review" in text.lower():
            return IntentRoute("review", "review")
        return IntentRoute("research", "research")
