"""Scaffold a new skill and register it everywhere it needs to appear.

    python tools/new_skill.py <skill-name> "<one-line description>"

Creates skills/<skill-name>/ (SKILL.md, README.md, .claude-plugin/plugin.json),
adds the marketplace entry and the README table row. Then edit SKILL.md and run
tools/validate.py.
"""

from __future__ import annotations

import sys

from spellbook import (MARKETPLACE, NAME_RE, README, SKILLS, TABLE_END, load_json,
                       write_json)

AUTHOR = "Davide Maggi"
REPO = "davidemaggi/spellbook"

SKILL_MD = """\
---
name: {name}
description: {description} Use when <the situations that should trigger this skill>.
license: MIT
metadata:
  author: {author}
  version: "0.1.0"
---

# {title}

<What the agent does with the user's input, described in words.>

## 1. <First step>

<Instructions. Refer to bundled files by path relative to this skill's folder,
e.g. `scripts/run.py`.>

## 2. Report

<What the agent tells the user at the end.>
"""

README_MD = """\
# {name}

{description}

## Install

```bash
npx skills add {repo} --skill {name} -g
```

## Usage

Ask your agent, for example: *"..."*.
"""


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    name, description = sys.argv[1], sys.argv[2].strip().rstrip(".") + "."
    if not NAME_RE.match(name) or len(name) > 64:
        sys.exit("skill name must be lowercase letters, digits and hyphens (max 64 chars)")
    d = SKILLS / name
    if d.exists():
        sys.exit(f"skills/{name} already exists")

    (d / "scripts").mkdir(parents=True)
    (d / "scripts" / ".gitkeep").touch()
    fmt = dict(name=name, description=description, author=AUTHOR, repo=REPO,
               title=name.replace("-", " ").capitalize())
    (d / "SKILL.md").write_text(SKILL_MD.format(**fmt), encoding="utf-8")
    (d / "README.md").write_text(README_MD.format(**fmt), encoding="utf-8")
    write_json(d / ".claude-plugin" / "plugin.json", {
        "name": name,
        "version": "0.1.0",
        "description": description,
        "author": {"name": AUTHOR},
        "homepage": f"https://github.com/{REPO}/tree/main/skills/{name}",
        "license": "MIT",
    })

    market = load_json(MARKETPLACE)
    market["plugins"].append({"name": name, "source": f"./skills/{name}",
                              "description": description})
    market["plugins"].sort(key=lambda p: p["name"])
    write_json(MARKETPLACE, market)

    readme = README.read_text(encoding="utf-8")
    row = f"| [{name}](skills/{name}) | {description} |\n"
    readme = readme.replace(TABLE_END, row + TABLE_END, 1)
    README.write_text(readme, encoding="utf-8")

    print(f"created skills/{name}/ and registered it in marketplace.json and README.md")
    print(f"next: edit skills/{name}/SKILL.md, then run: python tools/validate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
