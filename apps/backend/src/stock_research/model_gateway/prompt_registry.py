from __future__ import annotations

from dataclasses import dataclass
from string import Template


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    template: str
    variables: frozenset[str]


class PromptRegistry:
    """版本化 Prompt 模板注册与渲染。"""

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, prompt: PromptTemplate) -> None:
        key = f"{prompt.name}:{prompt.version}"
        self._templates[key] = prompt

    def render(
        self,
        name: str,
        version: str,
        variables: dict[str, str],
    ) -> str:
        prompt = self._templates.get(f"{name}:{version}")
        if prompt is None:
            raise KeyError(f"prompt template not found: {name}:{version}")
        missing = prompt.variables - variables.keys()
        if missing:
            raise ValueError(f"missing prompt variables: {sorted(missing)}")
        return Template(prompt.template).substitute(variables)
