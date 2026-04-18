from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


def build_backend_command(
    *,
    cwd: str | None = None,
    model: str | None = None,
    max_turns: int | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    api_key: str | None = None,
    api_format: str | None = None,
    permission_mode: str | None = None,
) -> list[str]:
    """Build the same backend command as `src/openharness/ui/react_launcher.py`.

    We re-implement it here to keep this exercise runnable even if optional
    runtime dependencies are not installed yet.
    """
    command = [sys.executable, "-m", "openharness", "--backend-only"]
    if cwd:
        command.extend(["--cwd", cwd])
    if model:
        command.extend(["--model", model])
    if max_turns is not None:
        command.extend(["--max-turns", str(max_turns)])
    if base_url:
        command.extend(["--base-url", base_url])
    if system_prompt:
        command.extend(["--system-prompt", system_prompt])
    if api_key:
        command.extend(["--api-key", api_key])
    if api_format:
        command.extend(["--api-format", api_format])
    if permission_mode:
        command.extend(["--permission-mode", permission_mode])
    return command


def main() -> None:
    cmd = build_backend_command(
        cwd=str(REPO_ROOT),
        model="gpt-5.4",
        max_turns=3,
        base_url=None,
        system_prompt=None,
        api_key=None,
        api_format=None,
        # TODO(你来改)：改成 "plan" / "default" / "full_auto" 看命令如何变化
        permission_mode="plan",
    )
    print("Backend command (React TUI will spawn this):")
    print(" ".join(cmd))
    print("")

    # TODO(你来改)：把下面结构补全（例如加入 base_url/system_prompt），并观察 JSON 输出
    frontend_config = {
        "backend_command": cmd,
        "initial_prompt": None,
        "theme": "default",
    }
    print("As OPENHARNESS_FRONTEND_CONFIG JSON:")
    print(json.dumps(frontend_config, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
