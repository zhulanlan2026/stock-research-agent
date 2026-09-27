from __future__ import annotations


class RiskPropagationService:
    """沿图边做确定性风险传播，可配置多跳轮数。"""

    def propagate(
        self,
        edges: list[tuple[str, str, str]],
        initial_risk: dict[str, float],
        *,
        damping: float = 0.5,
        max_steps: int = 1,
    ) -> dict[str, float]:
        if max_steps <= 0:
            return dict(initial_risk)

        nodes: list[str] = list(initial_risk)
        for source, _predicate, target in edges:
            if source not in nodes:
                nodes.append(source)
            if target not in nodes:
                nodes.append(target)

        incoming: dict[str, list[str]] = {node: [] for node in nodes}
        for source, _predicate, target in edges:
            incoming.setdefault(target, []).append(source)

        result = {node: initial_risk.get(node, 0.0) for node in nodes}
        for _ in range(max_steps):
            next_result = dict(result)
            for node in nodes:
                sources = incoming.get(node, [])
                if not sources:
                    continue
                propagated = sum(result.get(source, 0.0) for source in sources) / len(sources)
                next_result[node] = (
                    (1 - damping) * result.get(node, 0.0) + damping * propagated
                )
            result = next_result
        return result
