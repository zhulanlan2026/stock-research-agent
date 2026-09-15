from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast

from stock_research.services.evidence_strength import EvidenceStrengthService
from stock_research.stores.models.evidence import Evidence


def _evidence(source_level: str, citation_ready: bool) -> Evidence:
    return cast(
        Evidence,
        SimpleNamespace(source_level=source_level, citation_ready=citation_ready),
    )


def test_evidence_strength_uses_citation_ready_levels() -> None:
    result = EvidenceStrengthService().summarize(
        symbol="600519.SH",
        as_of=datetime(2026, 9, 12, tzinfo=timezone.utc),
        evidence=[
            _evidence("E1", True),
            _evidence("E2", True),
            _evidence("E5", False),
        ],
    )

    assert result["data_available"] is True
    assert result["evidence_count"] == 3
    assert result["citation_ready_count"] == 2
    assert result["source_levels"] == {"E1": 1, "E2": 1}
    assert result["strength"] == 0.9
    assert result["strength_label"] == "强"


def test_evidence_strength_returns_insufficient_without_ready_evidence() -> None:
    result = EvidenceStrengthService().summarize(
        symbol="600519.SH",
        as_of=datetime(2026, 9, 12, tzinfo=timezone.utc),
        evidence=[_evidence("E5", False)],
    )

    assert result["data_available"] is False
    assert result["citation_ready_count"] == 0
    assert result["source_levels"] == {}
    assert result["strength"] == 0.0
    assert result["strength_label"] == "证据不足"
