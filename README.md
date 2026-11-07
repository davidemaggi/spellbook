<div align="center">

<img src="assets/banner.svg" alt="spellbook: portable skills for every AI agent" width="100%">

**Teach your AI agent new tricks. One command, any agent.**

[![Validate](https://github.com/davidemaggi/spellbook/actions/workflows/validate.yml/badge.svg)](https://github.com/davidemaggi/spellbook/actions/workflows/validate.yml)
[![Agent Skills](https://img.shields.io/badge/format-Agent%20Skills-7e22ce)](https://agentskills.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-fbbf24)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/davidemaggi/spellbook?style=flat&color=f9a8d4)](https://github.com/davidemaggi/spellbook/stargazers)

[Quick start](#-quick-start) · [The spells](#-the-spells) · [Installation](#-installation) · [Write your own](#-write-your-own-spell)

</div>

---

## ✨ What is this?

**spellbook** is a collection of ready-to-use skills for AI coding agents. Each spell is a folder with a `SKILL.md` (and the scripts behind it), written in the open [Agent Skills](https://agentskills.io) format, so the same spell works in **Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot, OpenCode** and every other agent that speaks the format.

You install a spell once, and your agent knows when and how to use it. You ask in plain words, and the agent does the rest.

## 🚀 Quick start

```bash
npx skills add davidemaggi/spellbook
```

Pick the spells and the agents you want from the interactive menu, and that's it. Requires Node.js 22.20+.

## 📜 The spells

<!-- spells:start -->
| Spell | What it does |
| --- | --- |
| [transcribe](skills/transcribe) | 🎙️ Transcribe video/audio **locally** on your GPU with faster-whisper: raw text, SRT subtitles and a polished Markdown transcript. Nothing leaves your machine. |
<!-- spells:end -->

## 🪄 Why spellbook?

- 🌍 **Agent-agnostic.** Plain Agent Skills, no lock-in. Switch agents and keep your spells.
- 🎯 **Install only what you need.** One spell, a handful, or the whole book.
- 🔒 **Local-first.** Spells run on your machine. Heavy lifting (like transcription) never hits a cloud API.
- 🧰 **Batteries included.** Spells bring their own scripts and set up their own environment on first use.
- ✅ **Validated.** Every push is checked for spec compliance and portability.

## 📦 Installation

<details open>
<summary><b>Any agent: <code>npx skills</code> (recommended)</b></summary>

The [skills CLI](https://github.com/vercel-labs/skills) puts each spell in the right folder for each agent.

```bash
# browse the book
npx skills add davidemaggi/spellbook --list

# one spell, choosing agents interactively
npx skills add davidemaggi/spellbook --skill transcribe

# explicit agents; -g = for your user, in every project
npx skills add davidemaggi/spellbook --skill transcribe -a claude-code -a codex -a gemini-cli -g

# the whole book
npx skills add davidemaggi/spellbook --skill '*' -g
```

Keep spells fresh with `npx skills update`, and remove them with `npx skills remove <name>`.

</details>

<details>
<summary><b>Claude Code: plugin marketplace</b></summary>

```bash
claude plugin marketplace add davidemaggi/spellbook   # once
claude plugin install transcribe@spellbook
```

You can also run these inside a session as `/plugin marketplace add davidemaggi/spellbook` and `/plugin install transcribe@spellbook`. Plugin skills are namespaced, for example `/transcribe:transcribe`.

</details>

<details>
<summary><b>Manual</b></summary>

```bash
git clone https://github.com/davidemaggi/spellbook
cp -r spellbook/skills/transcribe ~/.claude/skills/   # or your agent's skills folder
```

</details>

## 🧙 Write your own spell

```bash
python tools/new_skill.py my-spell "What it does in one line"
python tools/validate.py
```

The first command scaffolds the spell and registers it in the catalog. [CONTRIBUTING.md](CONTRIBUTING.md) covers the rest: portability rules, versioning and releases.

---

<div align="center">

If a spell saved you some time, a ⭐ helps others find the book.

Made with 🪄 by [Davide Maggi](https://github.com/davidemaggi) · [MIT](LICENSE)

</div>
