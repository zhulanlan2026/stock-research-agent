from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphAclContext:
    allowed_nodes: frozenset[str]


class GraphAclFilter:
    """图发布前 ACL 过滤，默认拒绝未授权节点。"""

    def filter_edges(
        self,
        edges: list[tuple[str, str, str]],
        context: GraphAclContext,
    ) -> list[tuple[str, str, str]]:
        return [
            edge
            for edge in edges
            if edge[0] in context.allowed_nodes and edge[2] in context.allowed_nodes
        ]
