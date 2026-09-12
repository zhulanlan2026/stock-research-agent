from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import defaultdict

import httpx


async def run(
    *,
    base_url: str,
    email: str,
    password: str,
    tenant_slug: str,
    symbols: list[str],
    period: str,
    limit: int,
    rounds: int,
    concurrency: int,
) -> int:
    async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
        login = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
                "tenant_slug": tenant_slug,
            },
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        semaphore = asyncio.Semaphore(concurrency)
        results: list[dict[str, object]] = []

        async def one(symbol: str, round_no: int) -> None:
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(
                        f"/market/bars/{symbol}/cycle",
                        headers=headers,
                        params={"period": period, "limit": limit},
                    )
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    data = response.json()
                    results.append(
                        {
                            "symbol": symbol,
                            "round": round_no,
                            "http_status": response.status_code,
                            "http_ms": elapsed_ms,
                            "sample_count": data.get("sample_count"),
                            "lstm_available": data.get("lstm_available"),
                            "lstm_ms": data.get("lstm_latency_ms"),
                            "predictions": data.get("lstm_predictions"),
                        }
                    )
                except Exception as exc:
                    elapsed_ms = int((time.perf_counter() - started) * 1000)
                    results.append(
                        {
                            "symbol": symbol,
                            "round": round_no,
                            "http_status": 0,
                            "http_ms": elapsed_ms,
                            "error": type(exc).__name__,
                        }
                    )

        tasks = [
            one(symbol, round_no)
            for round_no in range(1, rounds + 1)
            for symbol in symbols
        ]
        await asyncio.gather(*tasks)

        print(json.dumps(results, ensure_ascii=False, indent=2))
        summary: dict[str, dict[str, int | float]] = defaultdict(
            lambda: {
                "count": 0,
                "total_http_ms": 0,
                "total_lstm_ms": 0,
                "lstm_available": 0,
            }
        )
        for item in results:
            symbol = str(item["symbol"])
            summary[symbol]["count"] += 1
            summary[symbol]["total_http_ms"] += int(str(item.get("http_ms", 0)))
            if item.get("lstm_available"):
                summary[symbol]["lstm_available"] += 1
                summary[symbol]["total_lstm_ms"] += int(str(item.get("lstm_ms") or 0))

        print("\nsummary")
        for symbol, stat in sorted(summary.items()):
            count = int(stat["count"])
            available = int(stat["lstm_available"])
            print(
                symbol,
                {
                    "count": count,
                    "avg_http_ms": round(float(stat["total_http_ms"]) / count, 1),
                    "avg_lstm_ms": (
                        round(float(stat["total_lstm_ms"]) / available, 1)
                        if available
                        else None
                    ),
                    "lstm_available": available,
                },
            )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch LSTM cycle prediction stress test")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--email", default="e2e@example.com")
    parser.add_argument("--password", default="e2e-password-123")
    parser.add_argument("--tenant-slug", default="dev")
    parser.add_argument("--symbols", default="600519.SH,000001.SZ,000858.SZ")
    parser.add_argument("--period", default="1d")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    symbols = [item.strip() for item in args.symbols.split(",") if item.strip()]
    raise SystemExit(
        asyncio.run(
            run(
                base_url=args.base_url,
                email=args.email,
                password=args.password,
                tenant_slug=args.tenant_slug,
                symbols=symbols,
                period=args.period,
                limit=args.limit,
                rounds=args.rounds,
                concurrency=args.concurrency,
            )
        )
    )


if __name__ == "__main__":
    main()
