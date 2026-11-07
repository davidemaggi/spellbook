# spellbook

A collection of portable agent skills (Agent Skills format), one per folder under `skills/`. The skills must work in every agent, not only the one editing this repo.

- **Adding, changing, releasing or removing a skill**: follow [CONTRIBUTING.md](CONTRIBUTING.md). Its portability rules apply to every SKILL.md edit.
- **Done** means `python tools/validate.py` prints `OK`. Run it after every change to `skills/`, `.claude-plugin/` or the README spells table.
- **New skills** start from `python tools/new_skill.py <name> "<description>"`, which registers the skill in all four places at once.
- **Any change to a skill** bumps its version in both `SKILL.md` `metadata.version` and `.claude-plugin/plugin.json`.
- **Tools** in `tools/` and the skills' `scripts/run.py` launchers use only the Python standard library, so they run on a bare Python without setup.
- **Language**: everything in the repo is in English.
