"""Check that every skill in the spellbook is consistent and portable.

    python tools/validate.py

Exits non-zero and lists every problem found. Run it before every commit; CI runs it on every push.
"""

from __future__ import annotations

import py_compile
import re
import sys

from spellbook import (MARKETPLACE, NAME_RE, README, ROOT, TABLE_END, TABLE_START,
                       load_json, parse_frontmatter, skill_dirs)

# Claude Code-only constructs that break portability when relied upon.
NON_PORTABLE = {
    r"\$ARGUMENTS": "$ARGUMENTS is Claude Code-only; describe the input in words",
    r"^allowed-tools:": "allowed-tools uses agent-specific tool names; leave it out",
}


def main() -> int:
    errors: list[str] = []
    err = errors.append

    market = load_json(MARKETPLACE)
    entries = {p["name"]: p for p in market.get("plugins", [])}
    readme = README.read_text(encoding="utf-8")
    table = readme.split(TABLE_START, 1)[-1].split(TABLE_END, 1)[0] if TABLE_START in readme else ""
    if not table:
        err(f"README.md: missing {TABLE_START} ... {TABLE_END} block")

    names = set()
    for d in skill_dirs():
        name = d.name
        names.add(name)
        where = f"skills/{name}"
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            err(f"{where}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        try:
            fm = parse_frontmatter(text)
        except ValueError as e:
            err(f"{where}/SKILL.md: {e}")
            continue

        # Agent Skills spec
        if fm.get("name") != name:
            err(f"{where}/SKILL.md: name {fm.get('name')!r} must equal the folder name")
        if not NAME_RE.match(name) or len(name) > 64:
            err(f"{where}: name must be lowercase letters/digits/hyphens, max 64 chars")
        desc = fm.get("description", "")
        if not 0 < len(desc) <= 1024:
            err(f"{where}/SKILL.md: description must be 1-1024 chars (is {len(desc)})")
        if len(fm.get("compatibility", "")) > 500:
            err(f"{where}/SKILL.md: compatibility must be max 500 chars")
        body = text.split("---", 2)[2]
        if len(body.splitlines()) > 500:
            err(f"{where}/SKILL.md: body over 500 lines; move reference material to separate files")

        # Portability
        for pattern, why in NON_PORTABLE.items():
            if re.search(pattern, text, re.M):
                err(f"{where}/SKILL.md: {why}")

        # Claude Code plugin manifest + marketplace
        version = (fm.get("metadata") or {}).get("version")
        plugin_json = d / ".claude-plugin" / "plugin.json"
        if not plugin_json.exists():
            err(f"{where}: missing .claude-plugin/plugin.json")
        else:
            plugin = load_json(plugin_json)
            if plugin.get("name") != name:
                err(f"{where}/.claude-plugin/plugin.json: name must be {name!r}")
            if version and plugin.get("version") != version:
                err(f"{where}: version mismatch, SKILL.md metadata.version={version} "
                    f"vs plugin.json={plugin.get('version')}")
        if not version:
            err(f"{where}/SKILL.md: missing metadata.version")
        entry = entries.get(name)
        if not entry:
            err(f"marketplace.json: no plugin entry for {name!r}")
        elif entry.get("source") != f"./skills/{name}":
            err(f"marketplace.json: {name!r} source must be './skills/{name}'")

        if not (d / "README.md").exists():
            err(f"{where}: missing README.md")
        if f"[{name}](skills/{name})" not in table:
            err(f"README.md: spells table has no row for {name!r}")

        for script in d.rglob("*.py"):
            try:
                py_compile.compile(str(script), doraise=True, cfile=None)
            except py_compile.PyCompileError as e:
                err(f"{script.relative_to(ROOT)}: {e.msg}")

    for orphan in sorted(set(entries) - names):
        err(f"marketplace.json: entry {orphan!r} has no skills/{orphan} folder")

    for e in errors:
        print(f"x {e}")
    print(f"{'FAILED' if errors else 'OK'}: {len(names)} skill(s), {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
