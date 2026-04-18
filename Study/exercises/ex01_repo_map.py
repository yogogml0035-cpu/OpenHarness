from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "openharness"


def main() -> None:
    """Count module distribution to build a mental map of the project.

    Learning goals:
    - See how many sub-modules exist and how large each is
    - Reinforce the "core trio: engine/tools/permissions" by adjusting sort order
    - Learn to use tests/ as a second entry point for understanding the project
    """
    if not SRC_ROOT.exists():
        raise SystemExit(f"Cannot find package dir: {SRC_ROOT}")

    counts: Counter[str] = Counter()
    for path in SRC_ROOT.rglob("*.py"):
        rel = path.relative_to(SRC_ROOT)
        top = rel.parts[0] if len(rel.parts) > 1 else "(root)"
        counts[top] += 1

    total = sum(counts.values())
    print(f"Repo root: {REPO_ROOT}")
    print(f"Package:   {SRC_ROOT}")
    print(f"Py files:  {total}")
    print(f"Modules:   {len(counts)}")
    print("")

    # This priority list corresponds to the "learning order":
    # core loop first, then capability layer, then extension layer
    # TODO: adjust this order to what you think is best for understanding the project
    #   Hint: engine/tools/permissions are the core trio and should come first
    priority = [
        "engine",
        "tools",
        "permissions",
        "hooks",
        "commands",
        "ui",
        "config",
        "plugins",
        "skills",
        "mcp",
        "tasks",
        "swarm",
    ]
    priority_index = {name: i for i, name in enumerate(priority)}

    def sort_key(item: tuple[str, int]) -> tuple[int, str]:
        name, _count = item
        return (priority_index.get(name, 10_000), name)

    print("Top-level modules (sorted by priority):")
    for name, count in sorted(counts.items(), key=sort_key):
        print(f"- {name:<20} {count} files")

    # TODO: count test files under tests/ and group by subdirectory
    #   Example approach:
    #   tests_root = REPO_ROOT / "tests"
    #   for path in tests_root.rglob("test_*.py"):
    #       ...
    #   After completing this, you should be able to answer:
    #   "Which module has the most tests? Which module has no tests?"
    print("")
    print("Tip: extend this script to also count tests/ files.")

    # Self-verification: after running this script, you should be able to answer
    # within 1 minute:
    # 1. "How many files does the engine module have?"
    # 2. "How many files does the tools module have?"
    # 3. "Which modules have you never heard of?" (e.g. channels/bridge/personalization)


if __name__ == "__main__":
    sys.exit(main())
