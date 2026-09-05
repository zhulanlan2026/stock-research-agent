from __future__ import annotations

import time

import httpx

from stock_research.model_gateway.gateway import ModelRequest, ModelResponse

# 每百万 token 的估算价格（美元）：(input, output)
_PRICE_PER_MILLION: dict[str, tuple[float, float]] = {
    "deepseek-chat": (0.27, 1.10),
    "deepseek-reasoner": (0.55, 2.19),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _PRICE_PER_MILLION.get(
        model, _PRICE_PER_MILLION["deepseek-chat"]
    )
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


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
        start = time.perf_counter()
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
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return ModelResponse(
            content=str(data["choices"][0]["message"]["content"]),
            model=str(data.get("model") or request.model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
