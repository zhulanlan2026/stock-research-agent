from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.ingest.dependencies import require_collector_ingest
from stock_research.ingest.schemas import IngestBatchRequest, IngestBatchResponse
from stock_research.ingest.store import IngestStore
from stock_research.stores.session import get_session

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "/events",
    response_model=IngestBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_events(
    body: IngestBatchRequest,
    _auth: None = Depends(require_collector_ingest),
    session: AsyncSession = Depends(get_session),
) -> IngestBatchResponse:
    accepted, duplicates = await IngestStore(session).append_events(body.events)
    await session.commit()
    return IngestBatchResponse(accepted=accepted, duplicates=duplicates)
