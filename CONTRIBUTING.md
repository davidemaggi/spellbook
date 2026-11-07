# Contributing to spellbook

How to add, change and release spells. Each spell is one skill in the [Agent Skills](https://agentskills.io/specification) format.

## Repository layout

```text
.claude-plugin/marketplace.json   Claude Code plugin catalog, one entry per skill
.github/workflows/validate.yml    CI: runs tools/validate.py on every push and PR
assets/                           README images
skills/<name>/
  SKILL.md                        frontmatter + instructions for the agent
  README.md                       docs for humans
  .claude-plugin/plugin.json      Claude Code plugin manifest
  scripts/                        bundled code (optional)
tools/
  new_skill.py                    scaffold + register a new skill
  validate.py                     consistency and portability checks
```

A skill is registered in four places: its folder, its `plugin.json`, the `marketplace.json` entry, and the spells table in `README.md` (between the `<!-- spells:start -->` / `<!-- spells:end -->` markers). `new_skill.py` creates all four, and `validate.py` checks that they agree.

## Adding a spell

1. Scaffold it:

   ```bash
   python tools/new_skill.py <name> "<one-line description>"
   ```

   The name uses lowercase letters, digits and hyphens. It becomes the folder name, the skill name and the plugin name.
2. Write `skills/<name>/SKILL.md`:
   - `description` is what makes the agent pick the skill. Say what it does, then "Use when ..." with the distinct situations that should trigger it.
   - Keep the body under 500 lines. Move long reference material into separate files in the skill folder and point to them from SKILL.md.
3. Write `skills/<name>/README.md` for humans: what it does, requirements, usage.
4. Polish the row in the README spells table (an emoji and a short pitch).
5. Run `python tools/validate.py` until it prints `OK`.
6. Try the skill for real in at least one agent: `npx skills add . --skill <name> -a claude-code`, from the repo root.

## Portability rules

Spells must work in any agent, so a SKILL.md uses only what every agent understands:

| Use | Instead of |
| --- | --- |
| Paths relative to the skill folder (`scripts/run.py`), optionally with `${CLAUDE_SKILL_DIR}` as a hint | Relying on `${CLAUDE_SKILL_DIR}` alone |
| The input described in words ("the files the user asked for") | `$ARGUMENTS` |
| Actions ("read the file", "run the command") | Tool names (`Read`, `Bash`, `allowed-tools`) |
| Scripts that need only Python or Node, and set up their own dependencies (see `skills/transcribe/scripts/run.py`) | Assuming globally installed packages |
| The `compatibility` field for real requirements (GPU, Python version, network) | Undocumented requirements |

Claude Code-only frontmatter such as `argument-hint` is allowed, because other agents ignore unknown fields.

Scripts that need third-party packages create their own virtual environment under a per-user data directory (`%LOCALAPPDATA%\spellbook\<skill>` on Windows, `~/.local/share/spellbook/<skill>` elsewhere). They never install into the skill folder, because `npx skills update` replaces it.

## Changing a spell and releasing

Every change to a skill bumps its version, in **both** `SKILL.md` (`metadata.version`) and `.claude-plugin/plugin.json` (`version`). `validate.py` fails if they differ. Claude Code uses `plugin.json`'s version to detect plugin updates.

Use [semver](https://semver.org):
- **patch** for fixes and wording;
- **minor** for new options or behaviour;
- **major** for changes in outputs, file names or requirements.

Commit messages start with the skill name (`transcribe: add --output-dir`), or `repo:` for changes that touch no skill.

To release, tag the commit `<name>-v<version>` (e.g. `transcribe-v1.2.0`) and push the tag. Users can pin a tag with `claude plugin marketplace add davidemaggi/spellbook#<tag>`.

## Removing a spell

Delete `skills/<name>/`, its `marketplace.json` entry and its README row, then run `validate.py`.
