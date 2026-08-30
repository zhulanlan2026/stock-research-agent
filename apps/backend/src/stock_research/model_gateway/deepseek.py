from __future__ import annotations

import httpx

from stock_research.model_gateway.gateway import ModelRequest, ModelResponse


class DeepSeekClient:
    """DeepSeek OpenAI 兼容 API 客户端。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=60.0,
        )

    async def complete(self, request: ModelRequest) -> ModelResponse:
        response = await self._client.post(
            "/chat/completions",
            json={
                "model": request.model,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in request.messages
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        )
        response.raise_for_status()
        data = response.json()
        return ModelResponse(
            content=str(data["choices"][0]["message"]["content"]),
            model=str(data.get("model") or request.model),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
