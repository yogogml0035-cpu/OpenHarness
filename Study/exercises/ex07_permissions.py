from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


def _show(title: str, decision) -> None:
    print(title)
    print(
        {
            "allowed": decision.allowed,
            "requires_confirmation": decision.requires_confirmation,
            "reason": decision.reason,
        }
    )
    print("")


def main() -> None:
    from openharness.config.settings import PathRuleConfig, PermissionSettings
    from openharness.permissions.checker import PermissionChecker
    from openharness.permissions.modes import PermissionMode

    settings = PermissionSettings(
        mode=PermissionMode.DEFAULT,
        denied_tools=["task_stop"],
        denied_commands=["rm -rf *"],
        path_rules=[
            # TODO(你来改)：加一条 deny 规则，比如禁止访问 */Study/*
            PathRuleConfig(pattern="*/DOES_NOT_MATCH/*", allow=False)
        ],
    )
    checker = PermissionChecker(settings)

    _show(
        "1) Read-only tool should pass in default mode",
        checker.evaluate("file_read", is_read_only=True, file_path=str(REPO_ROOT / "README.md")),
    )

    _show(
        "2) Mutating tool requires confirmation in default mode",
        checker.evaluate("file_write", is_read_only=False, file_path=str(REPO_ROOT / "README.md")),
    )

    _show(
        "3) Sensitive paths are always denied",
        checker.evaluate("file_read", is_read_only=True, file_path=str(Path.home() / ".ssh" / "id_rsa")),
    )

    _show(
        "4) Denied tool is blocked",
        checker.evaluate("task_stop", is_read_only=False),
    )

    _show(
        "5) Denied command patterns block even if tool name is allowed",
        checker.evaluate("bash", is_read_only=False, command="rm -rf /tmp/demo"),
    )

    full_auto = PermissionChecker(PermissionSettings(mode=PermissionMode.FULL_AUTO))
    _show(
        "6) full_auto allows mutating tools (but still denies sensitive paths)",
        full_auto.evaluate("file_write", is_read_only=False, file_path=str(REPO_ROOT / "README.md")),
    )
    _show(
        "7) full_auto still denies sensitive paths",
        full_auto.evaluate("file_read", is_read_only=True, file_path=str(Path.home() / ".aws" / "credentials")),
    )

    # TODO(你来改)：把 PermissionMode 改成 PLAN，解释为什么 mutating tools 会被直接阻断


if __name__ == "__main__":
    main()

