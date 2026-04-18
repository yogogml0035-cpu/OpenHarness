from __future__ import annotations

import json
import os
import tempfile
import time
from hashlib import sha1
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


# -----------------------------
# Minimal token estimation + microcompact (standalone)
# (mirrors the idea in src/openharness/services/compact/)
# -----------------------------


TIME_BASED_MC_CLEARED_MESSAGE = "[Old tool result content cleared]"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def estimate_conversation_tokens(messages) -> int:
    from openharness.engine.messages import TextBlock, ToolResultBlock, ToolUseBlock

    total = 0
    for msg in messages:
        for block in msg.content:
            if isinstance(block, TextBlock):
                total += estimate_tokens(block.text)
            elif isinstance(block, ToolResultBlock):
                total += estimate_tokens(block.content)
            elif isinstance(block, ToolUseBlock):
                total += estimate_tokens(block.name)
                total += estimate_tokens(str(block.input))
    # same conservative padding as the real code
    return int(total * (4 / 3))


def microcompact_messages(messages, *, keep_recent: int = 1) -> int:
    """Clear old tool_result content, keep last `keep_recent` results."""
    from openharness.engine.messages import ToolResultBlock

    keep_recent = max(1, int(keep_recent))
    tool_ids: list[str] = []
    for msg in messages:
        if msg.role != "user":
            continue
        for block in msg.content:
            if isinstance(block, ToolResultBlock):
                tool_ids.append(block.tool_use_id)
    if len(tool_ids) <= keep_recent:
        return 0
    clear_set = set(tool_ids[:-keep_recent])

    tokens_saved = 0
    for msg in messages:
        if msg.role != "user":
            continue
        new_content = []
        for block in msg.content:
            if isinstance(block, ToolResultBlock) and block.tool_use_id in clear_set:
                if block.content != TIME_BASED_MC_CLEARED_MESSAGE:
                    tokens_saved += estimate_tokens(block.content)
                new_content.append(
                    ToolResultBlock(
                        tool_use_id=block.tool_use_id,
                        content=TIME_BASED_MC_CLEARED_MESSAGE,
                        is_error=block.is_error,
                    )
                )
            else:
                new_content.append(block)
        msg.content = new_content
    return tokens_saved


# -----------------------------
# Minimal session snapshot (standalone)
# (mirrors src/openharness/services/session_storage.py)
# -----------------------------


class UsageSnapshot(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


_PERSISTED_TOOL_METADATA_KEYS = (
    "permission_mode",
    "read_file_state",
    "invoked_skills",
    "async_agent_state",
    "recent_work_log",
    "recent_verified_work",
    "task_focus_state",
    "compact_checkpoints",
    "compact_last",
)


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _sanitize_metadata(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_metadata(v) for v in value]
    return str(value)


def _persistable_tool_metadata(tool_metadata: dict[str, object] | None) -> dict[str, Any]:
    if not isinstance(tool_metadata, dict):
        return {}
    payload: dict[str, Any] = {}
    for key in _PERSISTED_TOOL_METADATA_KEYS:
        if key in tool_metadata:
            payload[key] = _sanitize_metadata(tool_metadata[key])
    return payload


def _get_data_dir() -> Path:
    env_dir = os.environ.get("OPENHARNESS_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
    else:
        data_dir = Path.home() / ".openharness" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_sessions_dir() -> Path:
    path = _get_data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_session_dir(cwd: str | Path) -> Path:
    path = Path(cwd).resolve()
    digest = sha1(str(path).encode("utf-8")).hexdigest()[:12]
    session_dir = get_sessions_dir() / f"{path.name}-{digest}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_session_snapshot(
    *,
    cwd: str | Path,
    model: str,
    system_prompt: str,
    messages,
    usage: UsageSnapshot,
    session_id: str | None = None,
    tool_metadata: dict[str, object] | None = None,
) -> Path:
    from openharness.engine.messages import ConversationMessage

    session_dir = get_project_session_dir(cwd)
    sid = session_id or uuid4().hex[:12]
    now = time.time()

    summary = ""
    for msg in messages:
        if isinstance(msg, ConversationMessage) and msg.role == "user" and msg.text.strip():
            summary = msg.text.strip()[:80]
            break

    payload = {
        "session_id": sid,
        "cwd": str(Path(cwd).resolve()),
        "model": model,
        "system_prompt": system_prompt,
        "messages": [m.model_dump(mode="json") for m in messages],
        "usage": usage.model_dump(),
        "tool_metadata": _persistable_tool_metadata(tool_metadata),
        "created_at": now,
        "summary": summary,
        "message_count": len(messages),
    }
    data = json.dumps(payload, indent=2) + "\n"
    latest_path = session_dir / "latest.json"
    latest_path.write_text(data, encoding="utf-8")
    session_path = session_dir / f"session-{sid}.json"
    session_path.write_text(data, encoding="utf-8")
    return latest_path


def load_session_snapshot(cwd: str | Path) -> dict[str, Any] | None:
    path = get_project_session_dir(cwd) / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    from openharness.engine.messages import (
        ConversationMessage,
        TextBlock,
        ToolResultBlock,
        ToolUseBlock,
    )
    from openharness.memory.manager import add_memory_entry, list_memory_files

    with tempfile.TemporaryDirectory(prefix="openharness-study-data-") as data_dir, tempfile.TemporaryDirectory(
        prefix="openharness-study-project-"
    ) as project_dir:
        os.environ["OPENHARNESS_DATA_DIR"] = data_dir
        os.environ["OPENHARNESS_CONFIG_DIR"] = data_dir

        cwd = Path(project_dir)

        # --- 1) microcompact demo ---
        messages: list[ConversationMessage] = []
        messages.append(ConversationMessage.from_user_text("Please do several tool calls."))

        for i in range(5):
            tool_id = f"toolu_{i}"
            messages.append(
                ConversationMessage(
                    role="assistant",
                    content=[
                        TextBlock(text=f"Calling tool {i}\n"),
                        ToolUseBlock(id=tool_id, name="read_file", input={"path": f"file{i}.txt"}),
                    ],
                )
            )
            messages.append(
                ConversationMessage(
                    role="user",
                    content=[
                        ToolResultBlock(
                            tool_use_id=tool_id,
                            content=("X" * 800) + f" (tool {i})",
                            is_error=False,
                        )
                    ],
                )
            )

        tokens_before = estimate_conversation_tokens(messages)
        saved = microcompact_messages(messages, keep_recent=1)
        tokens_after = estimate_conversation_tokens(messages)
        print("microcompact:")
        print(
            {
                "tokens_before": tokens_before,
                "tokens_after": tokens_after,
                "tokens_saved_est": tokens_before - tokens_after,
                "tokens_saved_raw": saved,
            }
        )
        print("")

        # TODO(你来改)：把 keep_recent 改成 3，预测 tokens_saved_est 会变大还是变小，并解释

        # --- 2) session snapshot demo ---
        tool_metadata = {
            "permission_mode": "default",
            "read_file_state": [],
            "invoked_skills": ["plan"],
            # This should NOT be persisted (not in whitelist).
            "not_persisted": {"hello": "world"},
        }
        snapshot_path = save_session_snapshot(
            cwd=cwd,
            model="fake-model",
            system_prompt="fake",
            messages=messages,
            usage=UsageSnapshot(input_tokens=10, output_tokens=20),
            tool_metadata=tool_metadata,
        )
        loaded = load_session_snapshot(cwd) or {}
        print("session snapshot saved:", snapshot_path.name)
        print("persisted tool_metadata keys:", sorted((loaded.get("tool_metadata") or {}).keys()))
        print("")

        # TODO(你来改)：把 tool_metadata 里的 not_persisted 改成 read_file_state，观察是否会被持久化

        # --- 3) memory demo (real project code, safe to run) ---
        add_memory_entry(
            cwd,
            title="Why microcompact exists",
            content="Microcompact clears old tool outputs to save tokens.",
        )
        print("memory files:", [p.name for p in list_memory_files(cwd)])
        print("done at:", time.strftime("%H:%M:%S"))


if __name__ == "__main__":
    sys.exit(main())

