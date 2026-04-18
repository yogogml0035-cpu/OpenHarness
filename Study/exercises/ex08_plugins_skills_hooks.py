from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    from openharness.plugins.loader import load_plugin
    from openharness.skills.loader import _parse_skill_markdown

    with tempfile.TemporaryDirectory(prefix="openharness-study-plugin-") as tmp:
        plugin_dir = Path(tmp) / "demo-plugin"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "name": "demo-plugin",
            "version": "0.0.1",
            "description": "A minimal plugin for Study exercises",
            "enabled_by_default": True,
        }
        _write(plugin_dir / "plugin.json", json.dumps(manifest, indent=2) + "\n")

        # commands/hello.md
        _write(
            plugin_dir / "commands" / "hello.md",
            "# Hello\n\nPrint a friendly greeting.\n",
        )

        # skills/demo/SKILL.md
        _write(
            plugin_dir / "skills" / "demo" / "SKILL.md",
            "# Demo Skill\n\nThis is a demo skill.\n",
        )

        loaded = load_plugin(plugin_dir, enabled_plugins={})
        if loaded is None:
            raise SystemExit("Failed to load plugin")

        print("Loaded plugin:")
        print({"name": loaded.manifest.name, "enabled": loaded.enabled, "path": str(loaded.path)})
        print("")

        print("Commands:")
        for cmd in loaded.commands:
            print("-", {"name": cmd.name, "description": cmd.description})
        print("")

        print("Skills:")
        for skill in loaded.skills:
            name, desc = _parse_skill_markdown("demo", skill.content)
            print("-", {"name": name, "description": desc, "source": skill.source})
        print("")

        # TODO(你来改)：给 commands/hello.md 加 YAML frontmatter（--- ... ---），观察 description 如何变化
        # TODO(你来改)：给 SKILL.md 加 frontmatter（name/description），观察 _parse_skill_markdown 的解析结果


if __name__ == "__main__":
    main()

