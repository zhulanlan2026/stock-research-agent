from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedBlockDraft:
    document_version_id: uuid.UUID
    page_start: int
    page_end: int
    section: str
    block_type: str
    content_hash: str
    text: str
    metadata: dict[str, object]


def build_text_block(
    *,
    document_version_id: uuid.UUID,
    text: str,
    page_start: int = 1,
    page_end: int = 1,
    section: str = "body",
    block_type: str = "text",
    metadata: dict[str, object] | None = None,
) -> NormalizedBlockDraft:
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return NormalizedBlockDraft(
        document_version_id=document_version_id,
        page_start=page_start,
        page_end=page_end,
        section=section,
        block_type=block_type,
        content_hash=content_hash,
        text=text,
        metadata=metadata or {},
    )
