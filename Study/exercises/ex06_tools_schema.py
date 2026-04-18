from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any

from pydantic import BaseModel


# This is a minimal standalone version of `src/openharness/tools/base.py`.
# We keep it local so the exercise can run before installing all project deps.

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ToolExecutionContext:
    cwd: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    output: str
    is_error: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    name: str
    description: str
    input_model: type[BaseModel]

    @abstractmethod
    async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult: ...

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return False

    def to_api_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def to_api_schema(self) -> list[dict[str, Any]]:
        return [tool.to_api_schema() for tool in self._tools.values()]


class ReverseArgs(BaseModel):
    text: str


class ReverseTool(BaseTool):
    name = "reverse"
    description = "Reverse a string (read-only toy tool)."
    input_model = ReverseArgs

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(self, arguments: ReverseArgs, context: ToolExecutionContext) -> ToolResult:
        del context
        return ToolResult(output=arguments.text[::-1])


async def _run() -> None:
    registry = ToolRegistry()
    registry.register(ReverseTool())

    tool = registry.get("reverse")
    assert tool is not None

    print("Tool schema:")
    print(tool.to_api_schema())
    print("")

    result = await tool.execute(
        tool.input_model.model_validate({"text": "OpenHarness"}),
        ToolExecutionContext(cwd=REPO_ROOT),
    )
    print("Tool execution result:")
    print({"output": result.output, "is_error": result.is_error})
    print("")

    print("Registry schemas:")
    print(registry.to_api_schema())

    # TODO(你来改)：新增一个 repeat(text, times) 工具并注册，再打印 registry.to_api_schema()
    #   参考做法：
    #   class RepeatArgs(BaseModel):
    #       text: str
    #       times: int
    #
    #   class RepeatTool(BaseTool):
    #       name = "repeat"
    #       description = "Repeat text N times."
    #       input_model = RepeatArgs
    #       ...
    #
    #   然后故意传入 times="x"（字符串而不是整数），观察 pydantic 校验报错：
    #   tool.input_model.model_validate({"text": "hi", "times": "x"})
    #
    #   自我验证：
    #   1. registry.to_api_schema() 应该返回 2 个工具的 schema（reverse + repeat）
    #   2. pydantic 校验 times="x" 时，应该抛出 ValidationError，包含 "int" 相关提示
    #   3. 思考：为什么 OpenHarness 用 pydantic 校验而不是让模型"自觉"填对参数？
    #      答案：模型可能犯错，pydantic 提供了"最后一道类型防线"


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
