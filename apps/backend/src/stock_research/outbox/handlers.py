from __future__ import annotations

import structlog

from stock_research.outbox.registry import HandlerRegistry

logger = structlog.get_logger(__name__)


async def handle_research_approved(payload: dict[str, object]) -> None:
    logger.info("research approved outbox event", payload=payload)


async def handle_review_decision(payload: dict[str, object]) -> None:
    logger.info("review decision outbox event", payload=payload)


def build_default_registry() -> HandlerRegistry:
    registry = HandlerRegistry()
    registry.register("research.approved", handle_research_approved)
    registry.register("review.decision", handle_review_decision)
    return registry
