from typing import Any

import httpx2 as httpx

from stock_research.documents.draft import (
    EvidenceClaimDraftStore,
    EvidenceDraft,
)
from stock_research.documents.store import DocumentStore
from stock_research.main import app
from stock_research.stores.session import get_session


async def _login(client: httpx.AsyncClient, db_context: Any) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": db_context.email, "password": db_context.password},
    )
    assert response.status_code == 200
    return str(response.json()["access_token"])


async def test_list_and_get_evidence(db_context: Any) -> None:
    app.dependency_overrides[get_session] = db_context.override
    try:
        async with db_context.factory() as session:
            document, version = await DocumentStore(session).create_document_with_version(
                tenant_id=db_context.tenant_id,
                owner_id=db_context.user_id,
                document_type="pdf",
                content_hash="sha256:doc",
                raw_object_key="dev/doc.pdf",
            )
            await session.commit()

            store = EvidenceClaimDraftStore(session)
            evidence = await store.create_evidence(
                EvidenceDraft(
                    tenant_id=db_context.tenant_id,
                    document_id=document.id,
                    document_version_id=version.id,
                    root_evidence_id=None,
                    page=1,
                    section="摘要",
                    content="引用内容",
                    source_level="E1",
                    citation_ready=True,
                    authorization={"visibility_scope": "PUBLIC"},
                )
            )
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _login(client, db_context)
            headers = {"Authorization": f"Bearer {token}"}

            list_response = await client.get(
                f"/api/v1/citations/documents/{document.id}/evidence",
                headers=headers,
            )
            get_response = await client.get(
                f"/api/v1/citations/evidence/{evidence.id}",
                headers=headers,
            )

        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        assert get_response.status_code == 200
        assert get_response.json()["content"] == "引用内容"
    finally:
        app.dependency_overrides.clear()
