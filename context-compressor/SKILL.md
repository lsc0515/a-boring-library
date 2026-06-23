---
name: context-compressor
description: Terminal AI context compression and project session persistence for Codex CLI, Claude Code, WorkBuddy, and similar command-line AI workflows. Use whenever the user asks to compress or save project context, persist or resume a terminal AI session, create searchable session summaries, recall prior decisions, mark milestones, inspect context-store status, or implement commands like /compress, /recall, /summarize, /status, /milestone. Also use for Chinese requests such as 压缩上下文, 保存上下文, 总结本轮会话, 续接/恢复会话, 召回之前进展, 记录里程碑, 查看上下文状态, or 让终端 AI 记住项目进度. Use at explicit session start/end handoff moments to load or refresh PROJECT.md, CONTEXT.md, INDEX.md, and sessions in a local ~/.workbuddy/context-store.
---

# Context Compressor

## Overview

Use this skill to create and maintain a local, project-scoped memory store that keeps the next Codex session grounded without loading the entire repository or conversation history. It stores compact context in `PROJECT.md`, `CONTEXT.md`, `INDEX.md`, daily session summaries, and snapshots under `~/.workbuddy/context-store/projects/{project-hash}/`.

The bundled script is deterministic and standard-library only:

```bash
python scripts/context_compressor.py --project /path/to/project compress
```

## Core Workflow

1. Resolve the project root from the user's workspace or `--project`.
2. Initialize the context store if it does not exist.
3. Run `compress` to create or refresh:
   - `PROJECT.md`: layer 0 metadata and durable status.
   - `CONTEXT.md`: layer 1 compact working context capped by byte budget.
   - `INDEX.md`: layer 2 file tree, symbols, and TODO/FIXME markers.
   - `sessions/`: layer 3 summaries and milestones.
   - `snapshots/`: JSON file tree and symbol snapshots.
4. At the end of meaningful work, run `summarize` with completed work, decisions, changed files, next steps, and reminders.
5. When the user asks what happened before, run `recall` before guessing from memory.

The skill cannot install a true terminal shutdown hook by itself. Treat explicit user requests such as "compress", "summarize this session", "recall", "resume", "session end", or `/compress` as lifecycle boundaries and invoke the script.

## Commands

Use the script path inside the skill folder. If the current working directory is the skill folder, `scripts/context_compressor.py` is enough; otherwise pass the absolute path.

### Initialize

Create the storage skeleton for a project:

```bash
python scripts/context_compressor.py --project /path/to/project init --phase "Phase 1"
```

### Compress

Scan the project and refresh compact context:

```bash
python scripts/context_compressor.py --project /path/to/project compress --budget 1000000 --phase "Phase 1"
```

### Summarize

Persist an end-of-session handoff and refresh `CONTEXT.md`:

```bash
python scripts/context_compressor.py --project /path/to/project summarize \
  --title "Implemented context compressor skill" \
  --phase "Phase 1" \
  --completed "Created store skeleton and compression script" \
  --decision "Use local ~/.workbuddy/context-store with project-hash isolation" \
  --changed-file "context-compressor/scripts/context_compressor.py" \
  --next-step "Wire external terminal hooks if automation is needed" \
  --note "Skill scripts use only Python standard library"
```

Repeat `--completed`, `--decision`, `--changed-file`, `--next-step`, and `--note` as needed. Use `--append` to add another summary block to an existing daily summary.

### Recall

Search the local memory store:

```bash
python scripts/context_compressor.py --project /path/to/project recall "project-hash"
```

### Status

Inspect context size and session count:

```bash
python scripts/context_compressor.py --project /path/to/project status --json
```

### Milestone

Record a durable decision or checkpoint that should not be compressed away:

```bash
python scripts/context_compressor.py --project /path/to/project milestone --message "Auth migration completed and verified."
```

## Resume Procedure

When starting or resuming a project:

1. Run `status` to find the project store.
2. Read `PROJECT.md` first.
3. Read `CONTEXT.md` for the current compact working set.
4. Read `INDEX.md` only when file tree, symbol lookup, or TODO context is needed.
5. Use `recall <keyword>` for older decisions, blockers, or handoffs.

## Compression Policy

Prefer project facts over generic commentary. Keep durable state, changed files, decisions, blockers, commands, and next steps. Avoid storing secrets. The default byte budget is 1,000,000 bytes for `CONTEXT.md`.

Read `references/compression-policy.md` when tuning the budget, deciding what belongs in each layer, or explaining tradeoffs.

Read `references/session-summary-template.md` when manually composing or reviewing session summaries.
