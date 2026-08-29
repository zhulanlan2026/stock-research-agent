import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from stock_research.documents.dependencies import get_raw_object_store
from stock_research.documents.parser_router import ParserRouter
from stock_research.documents.schemas import DocumentUploadResponse
from stock_research.documents.security import FileSecurityService
from stock_research.documents.storage import RawObjectStore
from stock_research.documents.store import DocumentStore
from stock_research.iam.dependencies import require_permission
from stock_research.stores.models.iam import User
from stock_research.stores.session import get_session

router = APIRouter(prefix="/files", tags=["files"])
_require_upload = require_permission("file.upload")

MAX_UPLOAD_BYTES = 100 * 1024 * 1024


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: Annotated[UploadFile, File()],
    symbol: Annotated[str | None, Form()] = None,
    document_type: Annotated[str, Form()] = "unknown",
    current_user: User = Depends(_require_upload),
    session: AsyncSession = Depends(get_session),
    object_store: RawObjectStore = Depends(get_raw_object_store),
) -> DocumentUploadResponse:
    data = await file.read()
    security = FileSecurityService().validate(
        file.filename,
        file.content_type,
        data,
    )
    if not security.allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FILE_SECURITY_REJECTED",
                "message": security.reason or "文件安全校验失败",
            },
        )

    content_hash = security.content_hash
    safe_filename = security.sanitized_filename
    parser_route = ParserRouter().route(safe_filename)
    object_key = f"{current_user.tenant_id}/{uuid.uuid4()}/{safe_filename}"

    await object_store.put_object(
        object_key,
        data,
        file.content_type or "application/octet-stream",
    )

    document, version = await DocumentStore(session).create_document_with_version(
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
        symbol=symbol,
        document_type=document_type,
        content_hash=content_hash,
        raw_object_key=object_key,
        parser=parser_route.parser,
        parser_version=parser_route.parser_version,
    )
    await session.commit()

    return DocumentUploadResponse(
        document_id=document.id,
        version_id=version.id,
        version_no=version.version_no,
        document_type=document.document_type,
        content_hash=content_hash,
        raw_object_key=object_key,
        status=document.status,
        created_at=document.created_at,
    )
