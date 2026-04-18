from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    from openharness.engine.messages import ConversationMessage, TextBlock, ToolResultBlock, ToolUseBlock

    assistant = ConversationMessage(
        role="assistant",
        content=[
            TextBlock(text="I'll use a tool.\n"),
            ToolUseBlock(id="toolu_demo", name="echo", input={"text": "hello"}),
            # TODO(你来改)：再加一个 ToolUseBlock，并补齐它的 tool_result（见下面 user message）
        ],
    )

    tool_results_user = ConversationMessage(
        role="user",
        content=[
            ToolResultBlock(tool_use_id="toolu_demo", content="hello", is_error=False),
            # TODO(你来改)：这里补第二个 ToolResultBlock，并可把 is_error=True 试一下
        ],
    )

    print("assistant.tool_uses:")
    for tu in assistant.tool_uses:
        print("-", {"id": tu.id, "name": tu.name, "input": tu.input})
    print("")

    print("assistant.to_api_param():")
    print(json.dumps(assistant.to_api_param(), indent=2, ensure_ascii=False))
    print("")

    print("tool_results_user.to_api_param():")
    print(json.dumps(tool_results_user.to_api_param(), indent=2, ensure_ascii=False))
    print("")

    # Demonstrate that tool_results are carried as a user message
    messages = [ConversationMessage.from_user_text("Hi"), assistant, tool_results_user]
    print("Conversation roles:", [m.role for m in messages])


if __name__ == "__main__":
    main()

