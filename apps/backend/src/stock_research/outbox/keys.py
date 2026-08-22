def build_effect_key(aggregate_type: str, aggregate_id: str, event_type: str) -> str:
    return f"{aggregate_type}:{aggregate_id}:{event_type}"
