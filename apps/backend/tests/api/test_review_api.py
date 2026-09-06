from typing import Any

import httpx2 as httpx

from stock_research.main import app
from stock_research.review.human_review import HumanReviewService
from stock_research.stores.session import get_session


async def _login(client: httpx.AsyncClient, db_context: Any) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": db_context.email, "password": db_context.password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def test_review_queue_and_decision(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        async with db_context.factory() as session:
            review = await HumanReviewService(session).create(
                tenant_id=db_context.tenant_id,
                target_type="report",
                target_id="report-1",
                reviewer_id=db_context.user_id,
            )
            await session.commit()
            review_id = review.id

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            headers = {"Authorization": f"Bearer {token}"}

            queue = await client.get("/api/v1/reviews/queue", headers=headers)
            assert queue.status_code == 200
            assert any(item["id"] == str(review_id) for item in queue.json())

            decision = await client.post(
                f"/api/v1/reviews/{review_id}/decision",
                json={"decision": "APPROVED", "reason_code": "OK"},
                headers=headers,
            )
            assert decision.status_code == 200
            assert decision.json()["status"] == "APPROVED"
    finally:
        app.dependency_overrides.clear()
