#!/usr/bin/env python3
"""Project context compression and recall utility.

This script intentionally uses only the Python standard library so it can run
inside a Codex skill without extra installation steps.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DEFAULT_BUDGET_BYTES = 1_000_000
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STORE = SKILL_DIR / "context-store"
TEXT_READ_LIMIT_BYTES = 256_000
SNIPPET_LINE_LIMIT = 80

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "out",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".turbo",
    ".venv",
    "venv",
    "env",
    ".env",
    "context-store",
}

IGNORE_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
}

BINARY_EXTS = {
    ".7z",
    ".bmp",
    ".dll",
    ".doc",
    ".docx",
    ".exe",
    ".gif",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".pyc",
    ".rar",
    ".so",
    ".sqlite",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".zip",
}

SOURCE_EXTS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}

CONFIG_NAMES = {
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "Makefile",
    "README.md",
    "compose.yaml",
    "docker-compose.yml",
    "eslint.config.js",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "tsconfig.json",
    "vite.config.js",
}

TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s-]*(.*)", re.IGNORECASE)

SYMBOL_PATTERNS = [
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)\b", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(?[^=\n]*?\)?\s*=>", re.MULTILINE),
    re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)\b", re.MULTILINE),
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE),
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)\b", re.MULTILINE),
    re.compile(r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_]\w*)\s*\(", re.MULTILINE),
    re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)\s*\(", re.MULTILINE),
    re.compile(r"^\s*(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)\b", re.MULTILINE),
]


@dataclass
class FileInfo:
    path: str
    abs_path: Path
    size: int
    mtime: float
    ext: str
    is_text: bool
    score: float
    symbols: list[str] = field(default_factory=list)
    todos: list[tuple[int, str]] = field(default_factory=list)
    summary: str = ""


@dataclass
class ProjectPaths:
    store_root: Path
    project_root: Path
    project_id: str
    project_dir: Path
    sessions_dir: Path
    snapshots_dir: Path


class ByteBudgetWriter:
    def __init__(self, budget: int):
        self.budget = budget
        self.parts: list[str] = []
        self.used = 0
        self.truncated = False

    def append(self, text: str) -> bool:
        encoded_len = len(text.encode("utf-8"))
        if self.used + encoded_len <= self.budget:
            self.parts.append(text)
            self.used += encoded_len
            return True

        remaining = self.budget - self.used
        if remaining > 128:
            clipped = text.encode("utf-8")[: remaining - 64].decode("utf-8", errors="ignore")
            self.parts.append(clipped.rstrip() + "\n\n[truncated to budget]\n")
            self.used = len("".join(self.parts).encode("utf-8"))
        self.truncated = True
        return False

    def text(self) -> str:
        return "".join(self.parts)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return dt.date.today().isoformat()


def resolve_project(path: str | None) -> Path:
    return Path(path or os.getcwd()).expanduser().resolve()


def resolve_store(path: str | None) -> Path:
    return Path(path or os.environ.get("WORKBUDDY_CONTEXT_STORE", DEFAULT_STORE)).expanduser().resolve()


def project_hash(project_root: Path) -> str:
    normalized = str(project_root).replace("\\", "/")
    if os.name == "nt":
        normalized = normalized.lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def get_paths(project: str | None, store: str | None) -> ProjectPaths:
    project_root = resolve_project(project)
    store_root = resolve_store(store)
    pid = project_hash(project_root)
    project_dir = store_root / "projects" / pid
    return ProjectPaths(
        store_root=store_root,
        project_root=project_root,
        project_id=pid,
        project_dir=project_dir,
        sessions_dir=project_dir / "sessions",
        snapshots_dir=project_dir / "snapshots",
    )


def ensure_store(paths: ProjectPaths) -> None:
    paths.sessions_dir.mkdir(parents=True, exist_ok=True)
    paths.snapshots_dir.mkdir(parents=True, exist_ok=True)
    update_global_index(paths)


def update_global_index(paths: ProjectPaths, extra: dict | None = None) -> None:
    paths.store_root.mkdir(parents=True, exist_ok=True)
    index_path = paths.store_root / "global-index.json"
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"projects": {}}
    else:
        data = {"projects": {}}

    projects = data.setdefault("projects", {})
    current = projects.setdefault(paths.project_id, {})
    current.update(
        {
            "name": paths.project_root.name,
            "path": str(paths.project_root),
            "project_id": paths.project_id,
            "updated_at": utc_now(),
        }
    )
    if extra:
        current.update(extra)
    index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def should_ignore_dir(name: str) -> bool:
    return name in IGNORE_DIRS or name.startswith(".") and name not in {".github"}


def should_skip_file(path: Path) -> bool:
    if path.name in IGNORE_FILES:
        return True
    if path.suffix.lower() in BINARY_EXTS:
        return True
    return False


def is_probably_text(path: Path, size: int) -> bool:
    if path.suffix.lower() in BINARY_EXTS:
        return False
    if size == 0:
        return True
    try:
        with path.open("rb") as fh:
            chunk = fh.read(min(size, 4096))
        if b"\0" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


def read_text_limited(path: Path, limit: int = TEXT_READ_LIMIT_BYTES) -> str:
    with path.open("rb") as fh:
        raw = fh.read(limit)
    return raw.decode("utf-8", errors="ignore")


def score_file(rel_path: str, path: Path, size: int, mtime: float) -> float:
    score = 0.0
    age_hours = max(0.0, (dt.datetime.now().timestamp() - mtime) / 3600)
    score += max(0.0, 50.0 - age_hours / 24.0)
    if path.name in CONFIG_NAMES or rel_path.lower().endswith((".md", ".toml", ".json", ".yaml", ".yml")):
        score += 25.0
    if path.suffix.lower() in SOURCE_EXTS:
        score += 20.0
    if any(part in {"src", "app", "lib", "server", "client", "components", "pages"} for part in Path(rel_path).parts):
        score += 15.0
    if size > 512_000:
        score -= 15.0
    elif size < 80_000:
        score += 5.0
    return round(score, 2)


def extract_symbols(text: str, max_symbols: int = 80) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for pattern in SYMBOL_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1)
            if name not in seen:
                found.append(name)
                seen.add(name)
            if len(found) >= max_symbols:
                return found
    return found


def extract_todos(text: str, max_todos: int = 40) -> list[tuple[int, str]]:
    todos: list[tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = TODO_RE.search(line)
        if match:
            detail = match.group(2).strip() or line.strip()
            todos.append((line_no, detail[:200]))
            if len(todos) >= max_todos:
                break
    return todos


def summarize_file(rel_path: str, size: int, symbols: list[str], todos: list[tuple[int, str]]) -> str:
    parts = [f"{rel_path} ({size} bytes)"]
    if symbols:
        parts.append("symbols: " + ", ".join(symbols[:12]))
    if todos:
        parts.append(f"{len(todos)} TODO/FIXME marker(s)")
    return "; ".join(parts)


def scan_project(project_root: Path) -> list[FileInfo]:
    files: list[FileInfo] = []
    for root, dirs, names in os.walk(project_root):
        dirs[:] = [d for d in dirs if not should_ignore_dir(d)]
        root_path = Path(root)
        for name in names:
            abs_path = root_path / name
            if should_skip_file(abs_path):
                continue
            try:
                stat = abs_path.stat()
            except OSError:
                continue
            rel_path = abs_path.relative_to(project_root).as_posix()
            is_text = is_probably_text(abs_path, stat.st_size)
            symbols: list[str] = []
            todos: list[tuple[int, str]] = []
            if is_text:
                try:
                    text = read_text_limited(abs_path)
                    symbols = extract_symbols(text)
                    todos = extract_todos(text)
                except OSError:
                    pass
            score = score_file(rel_path, abs_path, stat.st_size, stat.st_mtime)
            info = FileInfo(
                path=rel_path,
                abs_path=abs_path,
                size=stat.st_size,
                mtime=stat.st_mtime,
                ext=abs_path.suffix.lower(),
                is_text=is_text,
                score=score,
                symbols=symbols,
                todos=todos,
            )
            info.summary = summarize_file(rel_path, stat.st_size, symbols, todos)
            files.append(info)
    files.sort(key=lambda item: (-item.score, item.path))
    return files


def render_file_tree(files: list[FileInfo], limit: int = 400) -> str:
    lines = ["```text\n"]
    for info in sorted(files, key=lambda item: item.path)[:limit]:
        lines.append(f"{info.path} ({info.size} bytes)\n")
    if len(files) > limit:
        lines.append(f"... {len(files) - limit} more files omitted\n")
    lines.append("```\n")
    return "".join(lines)


def render_symbols(files: list[FileInfo], limit: int = 300) -> str:
    lines = ["| File | Symbols |\n", "| --- | --- |\n"]
    count = 0
    for info in files:
        if not info.symbols:
            continue
        lines.append(f"| `{info.path}` | {', '.join(info.symbols[:20])} |\n")
        count += 1
        if count >= limit:
            break
    if count == 0:
        lines.append("| _none found_ | |\n")
    return "".join(lines)


def render_todos(files: list[FileInfo], limit: int = 120) -> str:
    lines: list[str] = []
    count = 0
    for info in files:
        for line_no, detail in info.todos:
            lines.append(f"- `{info.path}:{line_no}` {detail}\n")
            count += 1
            if count >= limit:
                return "".join(lines)
    return "".join(lines) if lines else "- None found.\n"


def write_snapshot(paths: ProjectPaths, files: list[FileInfo]) -> Path:
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    snapshot_dir = paths.snapshots_dir / stamp
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    file_tree = [
        {
            "path": info.path,
            "size": info.size,
            "mtime": dt.datetime.fromtimestamp(info.mtime).isoformat(),
            "score": info.score,
            "is_text": info.is_text,
        }
        for info in sorted(files, key=lambda item: item.path)
    ]
    symbols = {info.path: info.symbols for info in files if info.symbols}
    (snapshot_dir / "file_tree.json").write_text(json.dumps(file_tree, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (snapshot_dir / "symbols.json").write_text(json.dumps(symbols, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot_dir


def latest_session(paths: ProjectPaths) -> Path | None:
    if not paths.sessions_dir.exists():
        return None
    sessions = sorted(paths.sessions_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return sessions[0] if sessions else None


def read_latest_session_excerpt(paths: ProjectPaths, max_bytes: int = 16_000) -> str:
    session = latest_session(paths)
    if not session:
        return "No prior session summary found.\n"
    text = read_text_limited(session, max_bytes)
    return f"Source: `{session.name}`\n\n{text.strip()}\n"


def write_project_md(paths: ProjectPaths, files: list[FileInfo], context_bytes: int, phase: str | None = None, status: str | None = None) -> None:
    session = latest_session(paths)
    lines = [
        f"# {paths.project_root.name} Project Memory\n\n",
        "## Core Metadata\n",
        f"- Project: {paths.project_root.name}\n",
        f"- Path: {paths.project_root}\n",
        f"- Project ID: {paths.project_id}\n",
        f"- Updated: {utc_now()}\n",
        f"- Current phase: {phase or 'unspecified'}\n",
        f"- Current status: {status or 'context compressed'}\n",
        f"- Last session: {session.name if session else 'none'}\n",
        f"- Files indexed: {len(files)}\n",
        f"- Context bytes: {context_bytes}\n\n",
        "## Current State\n",
        "- Load `CONTEXT.md` first for the compact working set.\n",
        "- Load `INDEX.md` when file tree, symbol, or TODO lookup is needed.\n",
        "- Search `sessions/` for older decisions and handoffs.\n\n",
        "## Permanent Milestones\n",
        "- Add durable milestones with `context_compressor.py milestone --message \"...\"`.\n",
    ]
    (paths.project_dir / "PROJECT.md").write_text("".join(lines), encoding="utf-8")


def write_index_md(paths: ProjectPaths, files: list[FileInfo], snapshot_dir: Path) -> None:
    lines = [
        f"# {paths.project_root.name} Context Index\n\n",
        f"- Generated: {utc_now()}\n",
        f"- Project ID: {paths.project_id}\n",
        f"- Snapshot: `{snapshot_dir.name}`\n",
        f"- Files indexed: {len(files)}\n\n",
        "## File Tree\n\n",
        render_file_tree(files),
        "\n## Symbols\n\n",
        render_symbols(files),
        "\n## TODO And FIXME Markers\n\n",
        render_todos(files),
    ]
    (paths.project_dir / "INDEX.md").write_text("".join(lines), encoding="utf-8")


def format_excerpt(text: str, max_lines: int = SNIPPET_LINE_LIMIT) -> str:
    lines = text.splitlines()
    clipped = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        clipped += f"\n... {len(lines) - max_lines} more lines omitted"
    return clipped


def write_context_md(paths: ProjectPaths, files: list[FileInfo], budget: int) -> int:
    writer = ByteBudgetWriter(budget)
    total_size = sum(info.size for info in files)
    text_files = sum(1 for info in files if info.is_text)

    writer.append(
        f"# {paths.project_root.name} Compressed Context\n\n"
        f"- Generated: {utc_now()}\n"
        f"- Project path: `{paths.project_root}`\n"
        f"- Project ID: `{paths.project_id}`\n"
        f"- Files indexed: {len(files)} ({text_files} text)\n"
        f"- Raw indexed size: {total_size} bytes\n"
        f"- Budget: {budget} bytes\n\n"
    )

    writer.append("## How To Resume\n\n")
    writer.append(
        "1. Read `PROJECT.md` for status and durable milestones.\n"
        "2. Use this file as the compact working context.\n"
        "3. Read `INDEX.md` for file tree, symbols, and TODO lookup.\n"
        "4. Search `sessions/` for older decisions before guessing.\n\n"
    )

    writer.append("## Latest Session\n\n")
    writer.append(read_latest_session_excerpt(paths))
    writer.append("\n")

    writer.append("## High-Value Files\n\n")
    for info in files[:80]:
        writer.append(f"### `{info.path}`\n\n")
        writer.append(f"- Size: {info.size} bytes\n- Score: {info.score}\n")
        if info.symbols:
            writer.append(f"- Symbols: {', '.join(info.symbols[:24])}\n")
        if info.todos:
            writer.append(f"- TODO/FIXME: {len(info.todos)} marker(s)\n")
        if info.is_text and info.size <= TEXT_READ_LIMIT_BYTES:
            try:
                excerpt = format_excerpt(read_text_limited(info.abs_path), SNIPPET_LINE_LIMIT)
                writer.append("\n```text\n" + excerpt.rstrip() + "\n```\n\n")
            except OSError:
                writer.append("\n[unreadable]\n\n")
        else:
            writer.append("\n[large or non-text file; see index/snapshot]\n\n")
        if writer.truncated:
            break

    writer.append("## TODO And FIXME Markers\n\n")
    writer.append(render_todos(files))
    writer.append("\n")

    content = writer.text()
    (paths.project_dir / "CONTEXT.md").write_text(content, encoding="utf-8")
    return len(content.encode("utf-8"))


def compress_project(args: argparse.Namespace) -> None:
    paths = get_paths(args.project, args.store)
    ensure_store(paths)
    files = scan_project(paths.project_root)
    snapshot_dir = write_snapshot(paths, files)
    write_index_md(paths, files, snapshot_dir)
    context_bytes = write_context_md(paths, files, args.budget)
    write_project_md(paths, files, context_bytes, phase=args.phase, status="context compressed")
    update_global_index(
        paths,
        {
            "files_indexed": len(files),
            "context_bytes": context_bytes,
            "latest_snapshot": snapshot_dir.name,
            "project_dir": str(paths.project_dir),
        },
    )
    print(f"Compressed {len(files)} files into {context_bytes} bytes")
    print(f"Project store: {paths.project_dir}")


def init_project(args: argparse.Namespace) -> None:
    paths = get_paths(args.project, args.store)
    ensure_store(paths)
    if not (paths.project_dir / "PROJECT.md").exists():
        write_project_md(paths, [], 0, phase=args.phase, status="initialized")
    if not (paths.project_dir / "CONTEXT.md").exists():
        (paths.project_dir / "CONTEXT.md").write_text("# Compressed Context\n\nNo context has been generated yet.\n", encoding="utf-8")
    if not (paths.project_dir / "INDEX.md").exists():
        (paths.project_dir / "INDEX.md").write_text("# Context Index\n\nNo index has been generated yet.\n", encoding="utf-8")
    update_global_index(paths, {"project_dir": str(paths.project_dir)})
    print(f"Initialized context store: {paths.project_dir}")


def append_lines(title: str, items: list[str]) -> list[str]:
    lines = [f"## {title}\n"]
    if items:
        lines.extend(f"- {item}\n" for item in items)
    else:
        lines.append("- None recorded.\n")
    lines.append("\n")
    return lines


def summarize_session(args: argparse.Namespace) -> None:
    paths = get_paths(args.project, args.store)
    ensure_store(paths)
    date = args.date or today()
    session_path = paths.sessions_dir / f"{date}.md"
    raw_notes = ""
    if args.from_file:
        raw_notes = Path(args.from_file).expanduser().read_text(encoding="utf-8")

    lines = [
        f"# Session Summary - {date}\n\n",
        "## Current Status\n",
        f"- Project: {paths.project_root.name}\n",
        f"- Phase: {args.phase or 'unspecified'}\n",
        f"- Blocker: {args.blocker or 'none'}\n",
    ]
    if args.title:
        lines.append(f"- Title: {args.title}\n")
    lines.append("\n")
    lines.extend(append_lines("Completed", args.completed))
    lines.extend(append_lines("Key Decisions", args.decision))
    lines.extend(append_lines("Changed Files", args.changed_file))
    lines.extend(append_lines("Next Steps", args.next_step))
    lines.extend(append_lines("Important Reminders", args.note))
    if raw_notes.strip():
        lines.append("## Raw Notes\n")
        lines.append(raw_notes.strip() + "\n\n")

    if session_path.exists() and args.append:
        existing = session_path.read_text(encoding="utf-8")
        content = existing.rstrip() + "\n\n---\n\n" + "".join(lines)
    else:
        content = "".join(lines)
    session_path.write_text(content, encoding="utf-8")

    files = scan_project(paths.project_root)
    context_bytes = write_context_md(paths, files, args.budget)
    write_project_md(paths, files, context_bytes, phase=args.phase, status="session summarized")
    update_global_index(paths, {"last_session": str(session_path), "context_bytes": context_bytes})
    print(f"Wrote session summary: {session_path}")
    print(f"Refreshed CONTEXT.md ({context_bytes} bytes)")


def add_milestone(args: argparse.Namespace) -> None:
    paths = get_paths(args.project, args.store)
    ensure_store(paths)
    milestone_path = paths.sessions_dir / "milestones.md"
    line = f"- {utc_now()} - {args.message.strip()}\n"
    if milestone_path.exists():
        content = milestone_path.read_text(encoding="utf-8")
        if not content.startswith("# Milestones"):
            content = "# Milestones\n\n" + content
    else:
        content = "# Milestones\n\n"
    milestone_path.write_text(content.rstrip() + "\n" + line, encoding="utf-8")
    print(f"Added milestone: {milestone_path}")


def recall(args: argparse.Namespace) -> None:
    paths = get_paths(args.project, args.store)
    ensure_store(paths)
    query = args.query.lower()
    files = [
        paths.project_dir / "PROJECT.md",
        paths.project_dir / "CONTEXT.md",
        paths.project_dir / "INDEX.md",
    ]
    files.extend(sorted(paths.sessions_dir.glob("*.md"), reverse=True))

    matches: list[tuple[Path, int, str]] = []
    for path in files:
        if not path.exists():
            continue
        try:
            for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                if query in line.lower():
                    matches.append((path, line_no, line.strip()))
                    if len(matches) >= args.limit:
                        break
        except OSError:
            continue
        if len(matches) >= args.limit:
            break

    if not matches:
        print(f"No matches for: {args.query}")
        return
    for path, line_no, line in matches:
        print(f"{path}:{line_no}: {line}")


def status(args: argparse.Namespace) -> None:
    paths = get_paths(args.project, args.store)
    ensure_store(paths)
    files = scan_project(paths.project_root)
    context_path = paths.project_dir / "CONTEXT.md"
    index_path = paths.project_dir / "INDEX.md"
    sessions = list(paths.sessions_dir.glob("*.md")) if paths.sessions_dir.exists() else []
    data = {
        "project": paths.project_root.name,
        "path": str(paths.project_root),
        "project_id": paths.project_id,
        "store": str(paths.project_dir),
        "files_indexed_now": len(files),
        "context_bytes": context_path.stat().st_size if context_path.exists() else 0,
        "index_bytes": index_path.stat().st_size if index_path.exists() else 0,
        "sessions": len(sessions),
        "latest_session": str(latest_session(paths)) if latest_session(paths) else None,
    }
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    for key, value in data.items():
        print(f"{key}: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compress, persist, and recall project context.")
    parser.add_argument("--project", help="Project root path. Defaults to current working directory.")
    parser.add_argument("--store", help="Context store path. Defaults to WORKBUDDY_CONTEXT_STORE or the skill-local context-store directory.")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create the project context store skeleton.")
    init_cmd.add_argument("--phase", help="Current project phase.")
    init_cmd.set_defaults(func=init_project)

    compress_cmd = sub.add_parser("compress", help="Scan the project and generate PROJECT.md, CONTEXT.md, INDEX.md, and snapshots.")
    compress_cmd.add_argument("--budget", type=int, default=DEFAULT_BUDGET_BYTES, help="Maximum CONTEXT.md size in bytes.")
    compress_cmd.add_argument("--phase", help="Current project phase.")
    compress_cmd.set_defaults(func=compress_project)

    summarize_cmd = sub.add_parser("summarize", help="Write a structured session summary and refresh compressed context.")
    summarize_cmd.add_argument("--budget", type=int, default=DEFAULT_BUDGET_BYTES)
    summarize_cmd.add_argument("--date", help="Session date in YYYY-MM-DD format. Defaults to today.")
    summarize_cmd.add_argument("--title", help="Short session title.")
    summarize_cmd.add_argument("--phase", help="Current project phase.")
    summarize_cmd.add_argument("--blocker", help="Current blocker, if any.")
    summarize_cmd.add_argument("--completed", action="append", default=[], help="Completed work item. Repeatable.")
    summarize_cmd.add_argument("--decision", action="append", default=[], help="Key decision. Repeatable.")
    summarize_cmd.add_argument("--changed-file", action="append", default=[], help="Changed file path and note. Repeatable.")
    summarize_cmd.add_argument("--next-step", action="append", default=[], help="Next step. Repeatable.")
    summarize_cmd.add_argument("--note", action="append", default=[], help="Important reminder. Repeatable.")
    summarize_cmd.add_argument("--from-file", help="Markdown/text file with raw notes to append.")
    summarize_cmd.add_argument("--append", action="store_true", help="Append to an existing same-day summary.")
    summarize_cmd.set_defaults(func=summarize_session)

    recall_cmd = sub.add_parser("recall", help="Search project memory by keyword.")
    recall_cmd.add_argument("query", help="Keyword or phrase to search for.")
    recall_cmd.add_argument("--limit", type=int, default=20)
    recall_cmd.set_defaults(func=recall)

    milestone_cmd = sub.add_parser("milestone", help="Record a durable milestone that should not be compressed away.")
    milestone_cmd.add_argument("--message", required=True, help="Milestone text.")
    milestone_cmd.set_defaults(func=add_milestone)

    status_cmd = sub.add_parser("status", help="Show context store status.")
    status_cmd.add_argument("--json", action="store_true", help="Print JSON.")
    status_cmd.set_defaults(func=status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001 - CLI should return clean errors.
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
