from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, AsyncIterator, Protocol


# This exercise is a *minimal simulation* of OpenHarness's agent loop.
# It is designed to be runnable even when optional runtime dependencies
# (e.g. anthropic SDK) are not installed yet.

REPO_ROOT = Path(__file__).resolve().parents[2]


# -----------------------------
# Minimal message / tool models
# -----------------------------


@dataclass(frozen=True)
class ToolUse:
    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    role: str  # "user" | "assistant"
    text: str = ""
    tool_uses: list[ToolUse] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)


# -----------------------------
# Minimal streaming events
# -----------------------------


@dataclass(frozen=True)
class ApiTextDeltaEvent:
    text: str


@dataclass(frozen=True)
class ApiMessageCompleteEvent:
    message: Message
    stop_reason: str | None = None


@dataclass(frozen=True)
class AssistantTextDelta:
    text: str


@dataclass(frozen=True)
class AssistantTurnComplete:
    message: Message


@dataclass(frozen=True)
class ToolExecutionStarted:
    tool_name: str
    tool_input: dict[str, Any]


@dataclass(frozen=True)
class ToolExecutionCompleted:
    tool_name: str
    output: str
    is_error: bool = False


StreamEvent = (
    AssistantTextDelta
    | AssistantTurnComplete
    | ToolExecutionStarted
    | ToolExecutionCompleted
)


# -----------------------------
# Minimal tool + permission layer
# -----------------------------


class BaseTool(Protocol):
    name: str

    def is_read_only(self, arguments: dict[str, Any]) -> bool: ...

    async def execute(self, arguments: dict[str, Any]) -> str: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    requires_confirmation: bool = False
    reason: str = ""


class PermissionChecker:
    def __init__(self, mode: str = "default") -> None:
        self._mode = mode  # "default" | "plan" | "full_auto"

    def evaluate(self, *, is_read_only: bool) -> PermissionDecision:
        if self._mode == "full_auto":
            return PermissionDecision(allowed=True, reason="full_auto allows all")
        if is_read_only:
            return PermissionDecision(allowed=True, reason="read-only allowed")
        if self._mode == "plan":
            return PermissionDecision(allowed=False, reason="plan mode blocks mutating tools")
        return PermissionDecision(
            allowed=False,
            requires_confirmation=True,
            reason="default mode requires confirmation for mutating tools",
        )


# -----------------------------
# Fake model client
# -----------------------------


class FakeApiClient:
    """First turn requests a tool, second turn ends."""

    def __init__(self) -> None:
        self._call_count = 0

    async def stream_message(self, messages: list[Message]) -> AsyncIterator[ApiTextDeltaEvent | ApiMessageCompleteEvent]:
        del messages
        self._call_count += 1

        if self._call_count == 1:
            yield ApiTextDeltaEvent("I will call a tool to compute 2+3...\n")
            yield ApiMessageCompleteEvent(
                message=Message(
                    role="assistant",
                    text="Let me compute.\n",
                    tool_uses=[
                        ToolUse(id="toolu_demo_add", name="add", input={"a": 2, "b": 3}),
                        # TODO(你来改)：再加一个 ToolUse，让模型一次请求 2 个工具调用
                    ],
                ),
                stop_reason="tool_use",
            )
            return

        yield ApiTextDeltaEvent("Done. The result is 5.\n")
        yield ApiMessageCompleteEvent(
            message=Message(role="assistant", text="Done. The result is 5."),
            stop_reason="end_turn",
        )


# -----------------------------
# Minimal run_query loop (simulation)
# -----------------------------


async def run_query_sim(
    *,
    api_client: FakeApiClient,
    tool_registry: ToolRegistry,
    permission_checker: PermissionChecker,
    messages: list[Message],
    max_turns: int = 5,
) -> AsyncIterator[StreamEvent]:
    for _turn in range(max_turns):
        final: Message | None = None
        async for event in api_client.stream_message(messages):
            if isinstance(event, ApiTextDeltaEvent):
                yield AssistantTextDelta(text=event.text)
            else:
                final = event.message

        if final is None:
            raise RuntimeError("No final assistant message")

        messages.append(final)
        yield AssistantTurnComplete(message=final)

        if not final.tool_uses:
            return

        tool_results: list[ToolResult] = []
        for tool_use in final.tool_uses:
            yield ToolExecutionStarted(tool_name=tool_use.name, tool_input=tool_use.input)

            tool = tool_registry.get(tool_use.name)
            if tool is None:
                output = f"Unknown tool: {tool_use.name}"
                is_error = True
            else:
                decision = permission_checker.evaluate(is_read_only=tool.is_read_only(tool_use.input))
                if not decision.allowed:
                    output = decision.reason
                    is_error = True
                else:
                    output = await tool.execute(tool_use.input)
                    is_error = False

            tool_results.append(ToolResult(tool_use_id=tool_use.id, content=output, is_error=is_error))
            yield ToolExecutionCompleted(tool_name=tool_use.name, output=output, is_error=is_error)

        messages.append(Message(role="user", tool_results=tool_results))

    raise RuntimeError(f"Exceeded max_turns={max_turns}")


class AddTool:
    name = "add"

    def is_read_only(self, arguments: dict[str, Any]) -> bool:
        del arguments
        return True

    async def execute(self, arguments: dict[str, Any]) -> str:
        a = int(arguments.get("a", 0))
        b = int(arguments.get("b", 0))
        return str(a + b)


async def _run() -> None:
    registry = ToolRegistry()
    registry.register(AddTool())

    # TODO(你来改)：把 mode 改成 "plan" 或 "full_auto"，观察 mutating tool 会怎样
    #   - "plan" 模式下，非只读工具会被阻断（AddTool 是只读的所以不受影响）
    #   - 如果你把 AddTool.is_read_only 改成 return False，plan 模式就会阻断它
    #   - "full_auto" 模式下所有工具都会被放行
    permissions = PermissionChecker(mode="default")
    api_client = FakeApiClient()
    messages = [Message(role="user", text="Compute 2+3")]

    print("Repo root:", REPO_ROOT)
    print("=== Streaming events (simulation) ===")
    print("")

    # 收集事件日志，用于最后打印"事件时间线"
    event_log: list[str] = []

    async for event in run_query_sim(
        api_client=api_client,
        tool_registry=registry,
        permission_checker=permissions,
        messages=messages,
    ):
        event_type = type(event).__name__
        event_log.append(event_type)

        if isinstance(event, AssistantTextDelta):
            sys.stdout.write(event.text)
            continue
        print(event_type, getattr(event, "tool_name", ""), getattr(event, "output", ""))

    # 打印事件时间线（帮助你理解 run_query 的事件产出顺序）
    print("\n=== Event timeline ===")
    for i, name in enumerate(event_log, 1):
        print(f"  {i}. {name}")

    print("\nFinal messages:")
    for msg in messages:
        if msg.role == "assistant":
            print("assistant:", msg.text.strip())

    # 自我验证：
    # 1. 你应该看到 event_log 里的顺序是：
    #    AssistantTextDelta → AssistantTurnComplete → ToolExecutionStarted → ToolExecutionCompleted → AssistantTextDelta → AssistantTurnComplete
    # 2. 如果你加了第二个 ToolUse，应该看到两组 ToolExecutionStarted/Completed
    # 3. 如果你把 mode 改成 "plan" 且工具是 mutating 的，应该看到 output 里包含 "plan mode blocks"


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

