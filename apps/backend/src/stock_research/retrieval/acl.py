from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AccessContext:
    tenant_id: str
    user_id: str
    allowed_visibility: frozenset[str]
    allowed_licenses: frozenset[str]
    allowed_symbols: frozenset[str]


@dataclass(frozen=True)
class DocumentAccess:
    doc_id: str
    tenant_id: str
    owner_id: str
    visibility_scope: str
    license_policy_id: str | None
    symbol: str | None
    available_at: datetime | None


class AclFilter:
    """检索前 ACL 过滤，默认拒绝。"""

    def filter(
        self,
        documents: Iterable[DocumentAccess],
        context: AccessContext,
        *,
        as_of: datetime | None = None,
    ) -> list[DocumentAccess]:
        allowed: list[DocumentAccess] = []
        for document in documents:
            if not self.is_allowed(document, context, as_of=as_of):
                continue
            allowed.append(document)
        return allowed

    def is_allowed(
        self,
        document: DocumentAccess,
        context: AccessContext,
        *,
        as_of: datetime | None = None,
    ) -> bool:
        if document.tenant_id != context.tenant_id:
            return False
        if document.visibility_scope not in context.allowed_visibility:
            return False
        if (
            document.license_policy_id is not None
            and document.license_policy_id not in context.allowed_licenses
        ):
            return False
        if (
            document.symbol is not None
            and document.symbol not in context.allowed_symbols
        ):
            return False
        if (
            as_of is not None
            and document.available_at is not None
            and document.available_at > as_of
        ):
            return False
        return True
