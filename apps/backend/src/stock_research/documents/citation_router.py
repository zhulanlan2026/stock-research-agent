import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.documents.draft import EvidenceClaimDraftStore
from stock_research.documents.schemas import EvidenceResponse
from stock_research.iam.dependencies import require_permission
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/citations", tags=["citations"])
_require_citation_read = require_permission("file.private.read")


@router.get(
    "/documents/{document_id}/evidence",
    response_model=list[EvidenceResponse],
)
async def list_document_evidence(
    document_id: uuid.UUID,
    _: User = Depends(_require_citation_read),
    session: AsyncSession = Depends(get_session),
) -> list[EvidenceResponse]:
    store = EvidenceClaimDraftStore(session)
    evidence = await store.list_evidence_by_document(document_id)
    return [EvidenceResponse.model_validate(item) for item in evidence]


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: uuid.UUID,
    _: User = Depends(_require_citation_read),
    session: AsyncSession = Depends(get_session),
) -> EvidenceResponse:
    evidence = await EvidenceClaimDraftStore(session).get_evidence(evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVIDENCE_NOT_FOUND", "message": "证据不存在"},
        )
    return EvidenceResponse.model_validate(evidence)
