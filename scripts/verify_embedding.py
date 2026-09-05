import asyncio

from stock_research.core.config import get_settings
from stock_research.retrieval.embedding import build_embedding_client


async def main() -> None:
    settings = get_settings()
    client = build_embedding_client(settings)
    print("model:", settings.embedding_model)
    print("using:", type(client).__name__)
    vector = (await client.embed(["贵州茅台 2025 年营收 净利润 同比增长"]))[0]
    print("dim:", len(vector))
    if hasattr(client, "aclose"):
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
