from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
import sys
import time
from typing import Any, Literal

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


# Minimal protocol models (compare with `src/openharness/ui/protocol.py`).
class FrontendRequest(BaseModel):
    type: Literal["submit_line", "shutdown"]
    line: str | None = None


class BackendEvent(BaseModel):
    type: Literal["ready", "error"]
    message: str | None = None
    commands: list[str] | None = None
    state: dict[str, Any] | None = None


async def _run() -> None:
    from openharness.coordinator.coordinator_mode import (
        TaskNotification,
        format_task_notification,
        parse_task_notification,
    )
    from openharness.mcp.types import McpJsonConfig
    from openharness.state.app_state import AppState
    from openharness.tasks import get_task_manager

    with tempfile.TemporaryDirectory(prefix="openharness-study-data-") as data_dir:
        os.environ["OPENHARNESS_DATA_DIR"] = data_dir
        os.environ["OPENHARNESS_CONFIG_DIR"] = data_dir

        # --- 1) MCP config model (no external connections) ---
        cfg = McpJsonConfig.model_validate(
            {
                "mcpServers": {
                    "demo": {
                        "type": "stdio",
                        "command": "python3",
                        "args": ["-c", "print('hello from mcp demo')"],
                    }
                }
            }
        )
        print("MCP servers configured:", sorted(cfg.mcpServers.keys()))
        print("Tip: real connection logic lives in src/openharness/mcp/client.py")
        print("")

        # --- 2) UI protocol models ---
        req = FrontendRequest.model_validate({"type": "submit_line", "line": "hello"})
        print("FrontendRequest JSON:", req.model_dump())

        state = AppState(model="fake", permission_mode="default", theme="default", cwd=str(REPO_ROOT))
        ready = BackendEvent(
            type="ready",
            state={"model": state.model, "cwd": state.cwd, "permission_mode": state.permission_mode},
            commands=["/help", "/exit"],
        )
        print("BackendEvent.ready JSON keys:", sorted(ready.model_dump().keys()))
        print("")

        # --- 3) Background task demo (shell task) ---
        manager = get_task_manager()
        task = await manager.create_shell_task(
            command="echo OpenHarness-task-demo",
            description="Study demo task",
            cwd=str(REPO_ROOT),
        )
        deadline = time.time() + 2.0
        while time.time() < deadline:
            current = manager.get_task(task.id)
            if current is not None and current.status != "running":
                break
            await asyncio.sleep(0.05)
        output = manager.read_task_output(task.id)
        print("Task output tail:", output.strip())
        print("")

        # TODO(你来改)：把 command 改成 `python3 -c "print('hi')"`，并观察输出变化

        # --- 4) Coordinator notification XML demo ---
        n = TaskNotification(task_id="a123", status="completed", summary="Demo finished", result="ok", usage={"total_tokens": 42})
        xml = format_task_notification(n)
        parsed = parse_task_notification(xml)
        print("task-notification roundtrip ok:", parsed == n)
        # TODO(你来改)：自己构造一个 XML（改 task-id/usage 字段），验证 parse 是否符合预期


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
