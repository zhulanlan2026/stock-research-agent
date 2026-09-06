import asyncio

import httpx


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post(
            "/api/v1/ingest/events",
            headers={"X-Collector-Token": "dev-collector-token-change-me"},
            json={
                "events": [
                    {
                        "event_id": "demo-1",
                        "event_type": "market.snapshot",
                        "payload": {
                            "symbol": "600519.SH",
                            "lastPrice": 1700.5,
                        },
                    }
                ]
            },
        )
        print(response.status_code, response.json())


if __name__ == "__main__":
    asyncio.run(main())
