# Context Compressor Skill

`context-compressor` is a Codex/Claude Code skill for compressing, saving, and recalling terminal AI project context. It creates a local project memory store with `PROJECT.md`, `CONTEXT.md`, `INDEX.md`, session summaries, milestones, and snapshots under the skill folder's `context-store/` directory.

## Install For Codex

Clone this repository, then copy or link the skill folder into your Codex skills directory.

### Windows PowerShell

```powershell
git clone https://github.com/<owner>/<repo>.git
Copy-Item -Recurse .\<repo>\context-compressor "$env:USERPROFILE\.codex\skills\context-compressor"
```

### macOS/Linux

```bash
git clone https://github.com/<owner>/<repo>.git
mkdir -p ~/.codex/skills
cp -R <repo>/context-compressor ~/.codex/skills/context-compressor
```

## Install For Claude Code

### Windows PowerShell

```powershell
git clone https://github.com/<owner>/<repo>.git
Copy-Item -Recurse .\<repo>\context-compressor "$env:USERPROFILE\.claude\skills\context-compressor"
```

### macOS/Linux

```bash
git clone https://github.com/<owner>/<repo>.git
mkdir -p ~/.claude/skills
cp -R <repo>/context-compressor ~/.claude/skills/context-compressor
```

Restart your terminal AI session after installing.

## One-Command Install

From the repository root, run:

```bash
bash skills.sh
```

That installs every skill in the repo into both Codex and Claude skill folders. Use `bash skills.sh codex` or `bash skills.sh claude` to target one side only.
On Windows, run it with Git Bash: `C:\Program Files\Git\bin\bash.exe skills.sh`.

## Usage

Ask naturally:

```text
Compress this project context so I can resume later.
```

Or invoke the skill explicitly:

```text
Use $context-compressor to summarize this session and save project context.
```

Chinese prompts are supported by the skill description:

```text
压缩一下当前项目上下文，方便下次恢复
```

## Direct Script Usage

The bundled script uses only the Python standard library, so it can also be run directly:

```bash
python context-compressor/scripts/context_compressor.py --project /path/to/project compress
python context-compressor/scripts/context_compressor.py --project /path/to/project status --json
python context-compressor/scripts/context_compressor.py --project /path/to/project recall "decision keyword"
```

## Memory Location

By default, memory is stored beside the skill:

```text
context-compressor/context-store/projects/{project-hash}/
```

Each installed copy of the skill has its own local memory store. To use a different location, pass `--store /custom/context-store` or set `WORKBUDDY_CONTEXT_STORE`.

## Repository Contents

```text
context-compressor/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/context_compressor.py
```

Only the `context-compressor/` folder is the skill. The repository-level `README.md` is for GitHub users.
