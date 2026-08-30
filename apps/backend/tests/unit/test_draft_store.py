from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from stock_research.documents.draft import (
    ClaimDraft,
    EvidenceClaimDraftStore,
    EvidenceDraft,
)
from stock_research.documents.store import DocumentStore


async def test_evidence_claim_draft_store_persists_drafts(db_context: Any) -> None:
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
                content="这是一段证据",
                source_level="E1",
                citation_ready=False,
                authorization={"visibility_scope": "PUBLIC"},
            )
        )
        claim = await store.create_claim(
            ClaimDraft(
                tenant_id=db_context.tenant_id,
                subject="公司A",
                predicate="signed_contract_with",
                object="客户B",
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                valid_to=None,
                evidence_ids=[str(evidence.id)],
                confidence=Decimal("0.88"),
            )
        )
        await session.commit()

        assert evidence.citation_ready is False
        assert evidence.source_level == "E1"
        assert claim.verification_status == "DRAFT"
        assert claim.confidence == 0.88
