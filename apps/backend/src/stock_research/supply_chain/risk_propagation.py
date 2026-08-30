from __future__ import annotations


class RiskPropagationService:
    """沿图边做一轮确定性风险传播。"""

    def propagate(
        self,
        edges: list[tuple[str, str, str]],
        initial_risk: dict[str, float],
        *,
        damping: float = 0.5,
    ) -> dict[str, float]:
        result = dict(initial_risk)
        incoming: dict[str, list[str]] = {node: [] for node in result}
        for source, _predicate, target in edges:
            incoming.setdefault(target, []).append(source)

        for node in result:
            sources = incoming.get(node, [])
            if not sources:
                continue
            propagated = sum(result.get(source, 0.0) for source in sources) / len(sources)
            result[node] = (1 - damping) * result.get(node, 0.0) + damping * propagated
        return result
