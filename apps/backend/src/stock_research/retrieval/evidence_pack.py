from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    document_id: str
    root_evidence_id: str
    source_level: str
    score: float


@dataclass(frozen=True)
class EvidencePack:
    as_of: datetime
    items: list[EvidenceItem]


class EvidencePackBuilder:
    """组装确定性 Evidence Pack。"""

    def build(
        self,
        items: list[EvidenceItem],
        as_of: datetime,
        *,
        max_items: int = 12,
        max_per_document: int = 3,
        max_per_root: int = 2,
    ) -> EvidencePack:
        ordered = sorted(items, key=lambda item: item.score, reverse=True)
        document_counts: dict[str, int] = {}
        root_counts: dict[str, int] = {}
        selected: list[EvidenceItem] = []

        for item in ordered:
            if len(selected) >= max_items:
                break
            if document_counts.get(item.document_id, 0) >= max_per_document:
                continue
            if root_counts.get(item.root_evidence_id, 0) >= max_per_root:
                continue
            selected.append(item)
            document_counts[item.document_id] = document_counts.get(item.document_id, 0) + 1
            root_counts[item.root_evidence_id] = root_counts.get(item.root_evidence_id, 0) + 1

        return EvidencePack(as_of=as_of, items=selected)
