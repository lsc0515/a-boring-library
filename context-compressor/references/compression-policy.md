# Compression Policy

## Layers

| Layer | File or Directory | Purpose | Target Size |
| --- | --- | --- | --- |
| 0 | `PROJECT.md` | Project identity, current status, latest session pointer, durable milestones | ~5 KB |
| 1 | `CONTEXT.md` | Compact working context with high-value file excerpts and latest session | <= 1 MB |
| 2 | `INDEX.md` and latest `snapshots/` | File tree, symbols, TODO/FIXME markers, JSON lookup data | ~300 KB |
| 3 | `sessions/` and older `snapshots/` | Full local archive for recall and handoff | unbounded |

## Priority Order

1. Current state, blockers, and next steps.
2. User decisions, constraints, and explicit reminders.
3. Files changed in the latest session.
4. Config files, package manifests, and entry points.
5. Recently modified source files.
6. Symbol names, API signatures, TODO/FIXME markers.
7. Older session records and low-score file paths.

## File Compression

- Keep full excerpts only for small, high-score text files.
- Store paths and metadata for binary, generated, lock, and large files.
- Extract symbols from common Python, JavaScript/TypeScript, Go, and Rust declarations.
- Keep TODO/FIXME markers with file and line number.
- Store full file tree and symbol maps as JSON snapshots for deterministic lookup.

## Session Compression

Use structured summaries instead of full transcripts unless the user explicitly marks a milestone or asks to preserve raw notes.

Keep:

- Completed tasks.
- Key decisions and rejected alternatives when relevant.
- Changed files.
- Commands or verification results that matter for continuation.
- Current blockers.
- Next steps.
- Environment details that future sessions could otherwise miss.

Avoid:

- Secrets, tokens, private keys, credentials, and `.env` values.
- Long command output unless it contains a decision-relevant error.
- Repeated status chatter.
- Generic explanation that can be reconstructed from code.

## Budget Tuning

The default `--budget 1000000` caps `CONTEXT.md` around one megabyte. Lower the budget for small model contexts or large repos with many high-value files:

```bash
python scripts/context_compressor.py --project /path/to/project compress --budget 300000
```

Raise it only when the caller can safely load more context. The script truncates `CONTEXT.md` rather than omitting `PROJECT.md`, `INDEX.md`, sessions, or snapshots.
