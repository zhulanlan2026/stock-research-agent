import uuid
from datetime import datetime, timezone

from stock_research.stores.models.workflow import WorkflowEvent
from stock_research.workflow.sse import format_sse, parse_last_event_id


def test_parse_last_event_id() -> None:
    assert parse_last_event_id(None) == 0
    assert parse_last_event_id("5") == 5
    assert parse_last_event_id("abc") == 0
    assert parse_last_event_id("-3") == 0


def test_format_sse() -> None:
    event = WorkflowEvent(
        id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        sequence_no=1,
        event_type="stage_progress",
        stage="evidence_retrieval",
        payload={"progress": 0.65, "message": "正在校验证据"},
        created_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc),
    )
    text = format_sse(event)
    assert "id: 1\n" in text
    assert "event: stage_progress\n" in text
    assert "evidence_retrieval" in text
    assert "正在校验证据" in text
