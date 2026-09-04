from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stock_research.model_gateway.discovery import (
    ModelDiscoveryService,
    RolloutDecider,
)


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelRequest:
    model: str
    messages: list[ModelMessage]
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ModelResponse:
    content: str
    model: str


class ModelClient(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse:
        ...


class ModelGateway:
    """统一模型调用出口，后续接入 egress policy、预算和重试。"""

    def __init__(
        self,
        client: ModelClient,
        *,
        discovery: ModelDiscoveryService | None = None,
        decider: RolloutDecider | None = None,
    ) -> None:
        self._client = client
        self._discovery = discovery
        self._decider = decider

    async def complete(
        self,
        request: ModelRequest,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ) -> ModelResponse:
        if not request.model:
            raise ValueError("model is required")
        if not request.messages:
            raise ValueError("messages must not be empty")

        model = request.model
        if self._discovery is not None:
            resolved = await self._discovery.resolve(
                request.model,
                decider=self._decider,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            if resolved is not None:
                model = resolved

        return await self._client.complete(
            ModelRequest(
                model=model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )
