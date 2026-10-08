---
name: ecc
description: Router into the vendored ECC (Everything Claude Code) library — 293 skills, 68 agent prompts and 94 command playbooks. Loads only the one entry the task needs.
disable-model-invocation: true
argument-hint: "[skill | agent | command name] [task]  — or empty for the catalog"
---

# /ecc — on-demand ECC library

ECC ([affaan-m/ecc](https://github.com/affaan-m/ecc), v2.2.3, MIT) is vendored under `.claude/ecc/`
**deliberately outside** Claude Code's discovery paths. Installed as a plugin it adds ~45k tokens to
every session, registers 24 hooks and starts an MCP server; here it costs nothing until this command
runs. Do not move it into `.claude/skills/`, `.claude/agents/` or `.claude/commands/`, and do not
install its hooks, MCP servers or `rules/`.

Arguments: `$ARGUMENTS`

## How to route

1. **No arguments** → read `.claude/ecc/INDEX.md` section headings only and show the user a short
   menu: the 10–15 entries most useful for *this* repository (Django/DRF, Postgres, React/TS,
   testing, security, code review, planning, docs), each as `/ecc <name> — one line`, in Uzbek.
   Then stop and wait.
2. **First word matches a name** (skill, agent or command — exact first, then prefix) → use it.
   Otherwise treat all arguments as a task description and `grep -i` the index for 2–4 keywords;
   if one entry clearly fits, use it; if several do, list the top 3–5 and ask which. Never read the
   whole index into context — it is ~80 KB.
3. **Load only the chosen entry:**
   - `skill` → read `.claude/ecc/skills/<dir>/SKILL.md`; read its `references/` or other files
     only when the skill points at them for the step you are on.
   - `agent` → read `.claude/ecc/agents/<name>.md` and run it with the Agent tool
     (`subagent_type: general-purpose`), passing the file's body as the system-level brief plus the
     user's task. Ignore its `model:` line.
   - `command` → read `.claude/ecc/commands/<name>.md` and follow it as a playbook.
4. **Path rewriting.** `${CLAUDE_PLUGIN_ROOT}` / `$CLAUDE_PLUGIN_ROOT` means `.claude/ecc`.
   Anything under `scripts/`, `hooks/`, `mcp-configs/` or `.claude-plugin/` was **not** vendored —
   if a step needs it, tell the user that part is unavailable in this install and continue without
   it. Never `npm install`, `npx`, or fetch ECC tooling from the network to fill the gap.

## Project rules always win

ECC is generic advice. Wherever it disagrees with this repository, follow the repository:
`CLAUDE.md` and `docs/00–07` are the source of truth (locked invariants, service/selector layering,
`organization_id` + RLS on every tenant table, cross-tenant tests returning `404`, append-only
ledgers, `SubscriptionWriteGate` on every viewset, brand tokens with no blue/purple, `format.ts`,
`t()` with ʻ/ʼ apostrophes). Do not write ECC's own artefacts (instinct stores, `.ecc/`,
`~/.claude/` settings, session logs) unless the user asks.

Reply to the user in Uzbek; code, comments, commits and docs stay in English.
