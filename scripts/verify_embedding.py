import asyncio

import httpx

from stock_research.core.config import get_settings
from stock_research.retrieval.embedding import build_embedding_client


async def main() -> None:
    settings = get_settings()
    client = build_embedding_client(settings)
    print("model:", settings.embedding_model)
    print("using:", type(client).__name__)
    try:
        vector = (await client.embed(["贵州茅台 2025 年营收 净利润 同比增长"]))[0]
    except httpx.ConnectError as exc:
        print(f"⚠️ 网络不可达，跳过真实 embedding 验证：{exc}")
        if hasattr(client, "aclose"):
            await client.aclose()
        return
    print("dim:", len(vector))
    if hasattr(client, "aclose"):
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
