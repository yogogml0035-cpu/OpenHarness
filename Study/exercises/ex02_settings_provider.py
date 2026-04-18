from __future__ import annotations

import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


def _brief(settings) -> dict[str, str]:
    return {
        "active_profile": settings.active_profile,
        "provider": settings.provider or "(auto)",
        "api_format": settings.api_format,
        "model": settings.model,
        "base_url": settings.base_url or "",
        "permission_mode": settings.permission.mode.value,
    }


def _diff(before: dict[str, str], after: dict[str, str]) -> dict[str, dict[str, str]]:
    changed: dict[str, dict[str, str]] = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed[key] = {"before": str(before.get(key)), "after": str(after.get(key))}
    return changed


def main() -> None:
    from openharness.config import settings as settings_mod
    from openharness.config.settings import PermissionMode, Settings, strip_ansi_escape_sequences

    def _profile_view(settings: Settings) -> dict[str, str]:
        profile_name, profile = settings.resolve_profile()
        return {
            "profile_name": profile_name,
            "label": profile.label,
            "provider": profile.provider,
            "api_format": profile.api_format,
            "auth_source": profile.auth_source,
            "default_model": profile.default_model,
            "resolved_model": profile.resolved_model,
            "base_url": profile.base_url or "",
        }

    baseline = Settings().materialize_active_profile()
    print("Baseline settings:")
    print(_brief(baseline))
    print("Active profile view:")
    print(_profile_view(baseline))
    print("")

    switched_profile = baseline.merge_cli_overrides(
        # TODO(你来改)：把这里换成 "claude-api"/"codex"/"copilot" 等试试
        active_profile="openai-compatible",
    )
    print("After merge_cli_overrides(active_profile=...):")
    print(_brief(switched_profile))
    print("Active profile view:")
    print(_profile_view(switched_profile))
    print("")

    overridden_model = baseline.merge_cli_overrides(model="gpt-5.4")
    print("After merge_cli_overrides(model='gpt-5.4'):")
    print(_brief(overridden_model))
    print("Diff view:")
    print(_diff(_brief(baseline), _brief(overridden_model)))
    print("")

    plan_mode = baseline.model_copy(update={"permission": baseline.permission.model_copy(update={"mode": PermissionMode.PLAN})})
    print("After switching permission.mode to PLAN:")
    print({"permission_mode": plan_mode.permission.mode.value, "model": plan_mode.model})
    print("")

    # TODO(你来改)：演示环境变量覆盖（不读你的 ~/.openharness/settings.json）
    # 提示：settings_mod._apply_env_overrides 会读取 OPENHARNESS_MODEL 等 env
    os.environ["OPENHARNESS_MODEL"] = "claude-sonnet-4-6"
    env_applied = settings_mod._apply_env_overrides(baseline)
    print("After _apply_env_overrides with OPENHARNESS_MODEL=claude-sonnet-4-6:")
    print({"model": env_applied.model})
    print("")

    noisy = "\x1b[1mclaude-sonnet-4-6\x1b[0m"
    print("Strip ANSI demo:")
    print({"raw": noisy, "clean": strip_ansi_escape_sequences(noisy)})


if __name__ == "__main__":
    main()
