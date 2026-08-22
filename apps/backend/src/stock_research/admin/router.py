from fastapi import APIRouter, Depends

from stock_research.iam.dependencies import require_permission
from stock_research.stores.models.iam import User

router = APIRouter(prefix="/admin", tags=["admin"])
_require_audit_read = require_permission("admin.audit.read")


@router.get("/audit-read")
async def audit_read(
    _: User = Depends(_require_audit_read),
) -> dict[str, bool]:
    return {"ok": True}
