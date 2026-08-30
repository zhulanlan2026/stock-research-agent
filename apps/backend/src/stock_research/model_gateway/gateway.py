from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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

    def __init__(self, client: ModelClient) -> None:
        self._client = client

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if not request.model:
            raise ValueError("model is required")
        if not request.messages:
            raise ValueError("messages must not be empty")
        return await self._client.complete(request)
