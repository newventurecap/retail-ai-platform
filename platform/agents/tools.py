"""Tool registry: an explicit allow-list, with an approval flag per tool."""

from collections.abc import Callable
from dataclasses import dataclass


class ToolNotAllowed(Exception):
    pass


@dataclass
class Tool:
    name: str
    fn: Callable[..., object]
    requires_approval: bool = False


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, fn: Callable[..., object], *, requires_approval: bool = False):
        self._tools[name] = Tool(name, fn, requires_approval)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolNotAllowed(f"tool '{name}' is not on the allow-list")
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools)
