from datetime import datetime, timezone

from stock_research.retrieval.evidence_pack import (
    EvidenceItem,
    EvidencePackBuilder,
)


def test_evidence_pack_enforces_document_and_root_limits() -> None:
    items = [
        EvidenceItem("e1", "doc-1", "root-1", "E1", 1.0),
        EvidenceItem("e2", "doc-1", "root-1", "E1", 0.9),
        EvidenceItem("e3", "doc-1", "root-2", "E1", 0.8),
        EvidenceItem("e4", "doc-2", "root-3", "E1", 0.7),
    ]

    pack = EvidencePackBuilder().build(
        items,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        max_per_document=2,
        max_per_root=1,
    )

    assert len(pack.items) == 3
    assert "e2" not in {item.evidence_id for item in pack.items}


def test_evidence_pack_limits_total_items() -> None:
    items = [
        EvidenceItem(f"e{index}", f"doc-{index}", f"root-{index}", "E1", float(index))
        for index in range(20)
    ]

    pack = EvidencePackBuilder().build(
        items,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        max_items=5,
    )

    assert len(pack.items) == 5
    assert pack.items[0].evidence_id == "e19"


def test_evidence_pack_drops_non_citation_ready() -> None:
    items = [
        EvidenceItem("e1", "doc-1", "root-1", "E1", 1.0, citation_ready=True),
        EvidenceItem("e2", "doc-1", "root-1", "E1", 0.9, citation_ready=False),
    ]

    pack = EvidencePackBuilder().build(
        items,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    assert {item.evidence_id for item in pack.items} == {"e1"}


def test_evidence_pack_drops_wrong_document_revision() -> None:
    items = [
        EvidenceItem(
            "e1", "doc-1", "root-1", "E1", 1.0, document_version_id="v2"
        ),
        EvidenceItem(
            "e2", "doc-1", "root-2", "E1", 0.9, document_version_id="v1"
        ),
    ]

    pack = EvidencePackBuilder().build(
        items,
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        latest_document_versions={"doc-1": "v2"},
    )

    assert {item.evidence_id for item in pack.items} == {"e1"}
