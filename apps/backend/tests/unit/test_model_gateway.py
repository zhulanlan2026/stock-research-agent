import json

import httpx
import pytest

from stock_research.model_gateway.deepseek import DeepSeekClient
from stock_research.model_gateway.discovery import ModelDescriptor, ModelDiscoveryService
from stock_research.model_gateway.gateway import (
    ModelGateway,
    ModelMessage,
    ModelRequest,
    ModelResponse,
)


class _FakeClient:
    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(content="ok", model=request.model)


class _FakeDecider:
    def __init__(self, enabled: dict[str, bool]) -> None:
        self._enabled = enabled

    async def is_enabled(
        self,
        key: str,
        *,
        environment: str = "production",
        tenant_id: str | None = None,
        user_id: str | None = None,
        now: object = None,
    ) -> bool:
        return self._enabled.get(key, False)


async def test_model_gateway_delegates_to_client() -> None:
    gateway = ModelGateway(_FakeClient())

    response = await gateway.complete(
        ModelRequest(
            model="deepseek-v4-pro",
            messages=[ModelMessage("user", "hello")],
        )
    )

    assert response.content == "ok"


async def test_model_gateway_resolves_alias_via_discovery() -> None:
    discovery = ModelDiscoveryService()
    discovery.register(
        ModelDescriptor("research", "deepseek-v4-pro", frozenset({"reasoning"}), 1)
    )
    gateway = ModelGateway(_FakeClient(), discovery=discovery)

    response = await gateway.complete(
        ModelRequest(
            model="research",
            messages=[ModelMessage("user", "hello")],
        )
    )

    assert response.model == "deepseek-v4-pro"


async def test_model_gateway_rolls_out_alias_behind_flag() -> None:
    discovery = ModelDiscoveryService()
    discovery.register(
        ModelDescriptor("research", "model-stable", frozenset({"reasoning"}), 1)
    )
    discovery.register(
        ModelDescriptor(
            "research",
            "model-canary",
            frozenset({"reasoning"}),
            2,
            rollout_key="research.canary",
        )
    )
    gateway = ModelGateway(
        _FakeClient(),
        discovery=discovery,
        decider=_FakeDecider({"research.canary": True}),
    )

    response = await gateway.complete(
        ModelRequest(model="research", messages=[ModelMessage("user", "hello")]),
        user_id="u1",
    )

    assert response.model == "model-canary"


async def test_model_gateway_validates_request() -> None:
    gateway = ModelGateway(_FakeClient())

    with pytest.raises(ValueError):
        await gateway.complete(ModelRequest(model="", messages=[]))


def _fake_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "deepseek-v4-pro"
        return httpx.Response(
            200,
            json={
                "model": "deepseek-v4-pro",
                "choices": [{"message": {"content": "hi"}}],
            },
        )

    return httpx.MockTransport(handler)


async def test_deepseek_client_completes_request() -> None:
    client = DeepSeekClient(
        base_url="https://api.deepseek.com",
        api_key="test-key",
        transport=_fake_transport(),
    )

    response = await client.complete(
        ModelRequest(
            model="deepseek-v4-pro",
            messages=[ModelMessage("user", "hello")],
        )
    )
    await client.aclose()

    assert response.content == "hi"
