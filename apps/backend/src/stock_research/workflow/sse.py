import json

from stock_research.stores.models.workflow import WorkflowEvent


def parse_last_event_id(value: str | None) -> int:
    if not value:
        return 0
    try:
        return max(0, int(value))
    except ValueError:
        return 0


def format_sse(event: WorkflowEvent) -> str:
    payload = event.payload or {}
    data: dict[str, object] = {
        "event_id": str(event.id),
        "sequence_no": event.sequence_no,
        "task_id": str(event.task_id),
        "type": event.event_type,
        "stage": event.stage,
        "progress": payload.get("progress"),
        "message": payload.get("message"),
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
    return (
        f"id: {event.sequence_no}\n"
        f"event: {event.event_type}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )
