import json

import httpx
import pytest

from stock_research.model_gateway.deepseek import DeepSeekClient
from stock_research.model_gateway.gateway import (
    ModelGateway,
    ModelMessage,
    ModelRequest,
    ModelResponse,
)


class _FakeClient:
    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(content="ok", model=request.model)


async def test_model_gateway_delegates_to_client() -> None:
    gateway = ModelGateway(_FakeClient())

    response = await gateway.complete(
        ModelRequest(
            model="deepseek-v4-pro",
            messages=[ModelMessage("user", "hello")],
        )
    )

    assert response.content == "ok"


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
