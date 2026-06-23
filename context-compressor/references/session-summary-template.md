# Session Summary Template

Use this structure when writing summaries manually or reviewing output from `scripts/context_compressor.py summarize`.

```markdown
# Session Summary - YYYY-MM-DD

## Current Status
- Project: {project name}
- Phase: {current development phase}
- Blocker: {blocking issue or none}
- Title: {short session title}

## Completed
- {completed task}

## Key Decisions
- {decision and reason}

## Changed Files
- {path} ({change type or purpose})

## Next Steps
- {next action}

## Important Reminders
- {configuration, environment, command, or constraint to preserve}

## Raw Notes
{optional raw notes when the user explicitly asks to preserve them}
```

Keep each bullet concrete enough for a future agent to act without rereading the full transcript.
