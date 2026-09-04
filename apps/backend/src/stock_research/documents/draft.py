from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.stores.models.evidence import Claim, Evidence


@dataclass(frozen=True)
class EvidenceDraft:
    tenant_id: uuid.UUID | None
    document_id: uuid.UUID | None
    document_version_id: uuid.UUID | None
    root_evidence_id: uuid.UUID | None
    page: int | None
    section: str | None
    content: str
    source_level: str | None
    citation_ready: bool
    authorization: dict[str, object]


@dataclass(frozen=True)
class ClaimDraft:
    tenant_id: uuid.UUID | None
    subject: str
    predicate: str
    object: str
    valid_from: datetime | None
    valid_to: datetime | None
    evidence_ids: list[str]
    confidence: Decimal


class EvidenceClaimDraftStore:
    """保存 DRAFT 状态的 Evidence / Claim，不执行正式发布。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_evidence(self, draft: EvidenceDraft) -> Evidence:
        content_hash = hashlib.sha256(draft.content.encode()).hexdigest()
        evidence = Evidence(
            tenant_id=draft.tenant_id,
            document_id=draft.document_id,
            document_version_id=draft.document_version_id,
            root_evidence_id=draft.root_evidence_id,
            page=draft.page,
            section=draft.section,
            content_hash=content_hash,
            content=draft.content,
            source_level=draft.source_level,
            citation_ready=draft.citation_ready,
            authorization=draft.authorization,
        )
        self.session.add(evidence)
        await self.session.flush()
        await self.session.refresh(evidence)
        return evidence

    async def create_claim(self, draft: ClaimDraft) -> Claim:
        claim = Claim(
            tenant_id=draft.tenant_id,
            subject=draft.subject,
            predicate=draft.predicate,
            object=draft.object,
            valid_from=draft.valid_from,
            valid_to=draft.valid_to,
            evidence_ids=draft.evidence_ids,
            verification_status="DRAFT",
            confidence=draft.confidence,
        )
        self.session.add(claim)
        await self.session.flush()
        await self.session.refresh(claim)
        return claim

    async def get_evidence(
        self, evidence_id: uuid.UUID, *, tenant_id: uuid.UUID
    ) -> Evidence | None:
        result = await self.session.execute(
            select(Evidence).where(
                Evidence.id == evidence_id,
                Evidence.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_evidence_by_document(
        self,
        document_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
    ) -> list[Evidence]:
        result = await self.session.execute(
            select(Evidence)
            .where(
                Evidence.document_id == document_id,
                Evidence.tenant_id == tenant_id,
            )
            .order_by(Evidence.created_at, Evidence.id)
        )
        return list(result.scalars().all())
