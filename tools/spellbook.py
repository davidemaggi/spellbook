"""Shared helpers for the spellbook maintenance tools (stdlib only)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
TABLE_START = "<!-- spells:start -->"
TABLE_END = "<!-- spells:end -->"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> dict:
    """Minimal YAML frontmatter parser: top-level `key: value` pairs plus one
    level of nested mapping (enough for name/description/metadata)."""
    if not text.startswith("---"):
        raise ValueError("missing frontmatter (file must start with ---)")
    try:
        block = text.split("---", 2)[1]
    except IndexError:
        raise ValueError("unterminated frontmatter") from None
    data: dict = {}
    parent: str | None = None
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(\s*)([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            raise ValueError(f"unsupported frontmatter line: {line!r}")
        indent, key, value = m.groups()
        value = value.strip().strip('"').strip("'")
        if indent and parent:
            data[parent][key] = value
        else:
            parent = key if value == "" else None
            data[key] = {} if value == "" else value
    return data


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def skill_dirs() -> list[Path]:
    return sorted(d for d in SKILLS.iterdir() if d.is_dir() and not d.name.startswith("."))
