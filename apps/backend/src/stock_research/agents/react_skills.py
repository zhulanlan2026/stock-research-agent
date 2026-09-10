from __future__ import annotations

from typing import Any, cast

from stock_research.skills.manifest import SkillManifest


class ResearchContextSkill:
    """仅供模型驱动 research 节点读取已完成的模块摘要。"""

    manifest = SkillManifest(
        name="research.context.read",
        version="1.0.0",
        execution_type="deterministic_engine",
        required_scopes=frozenset({"research.standard.execute"}),
        side_effect="NONE",
        external_model_allowed=False,
    )

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        return cast(dict[str, Any], _jsonable(state.get("results") or {}))


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    data = getattr(value, "data", None)
    if data is not None:
        return _jsonable(data)
    status = getattr(value, "status", None)
    if status is not None:
        return {"status": status}
    return str(value)
