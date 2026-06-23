#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法：bash skills.sh [codex|claude|ccswitch|both|all]

把本仓库中的每个技能目录安装到所选的技能目录中。
默认目标是 Codex 和 Claude。
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_mode="${1:-both}"

repo_url="$(git -C "$repo_root" remote get-url origin 2>/dev/null || true)"
repo_owner=""
repo_name=""
repo_branch="main"
if [[ "$repo_url" =~ github\.com[:/]+([^/]+)/([^/.]+)(\.git)?$ ]]; then
  repo_owner="${BASH_REMATCH[1]}"
  repo_name="${BASH_REMATCH[2]}"
fi

skill_repos_id=""
if [[ -n "$repo_owner" && -n "$repo_name" ]]; then
  skill_repos_id="$repo_owner/$repo_name"
fi

case "$target_mode" in
  both)
    targets=("$HOME/.codex/skills" "$HOME/.claude/skills")
    ;;
  all)
    targets=("$HOME/.codex/skills" "$HOME/.claude/skills" "$HOME/.cc-switch/skills")
    ;;
  codex)
    targets=("$HOME/.codex/skills")
    ;;
  claude)
    targets=("$HOME/.claude/skills")
    ;;
  ccswitch)
    targets=("$HOME/.cc-switch/skills")
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    printf '未知目标：%s\n\n' "$target_mode" >&2
    usage >&2
    exit 1
    ;;
esac

skill_dirs=()
shopt -s nullglob
for dir in "$repo_root"/*; do
  if [[ -d "$dir" && -f "$dir/SKILL.md" ]]; then
    skill_dirs+=("$dir")
  fi
done
shopt -u nullglob

if [[ ${#skill_dirs[@]} -eq 0 ]]; then
  printf '在 %s 下没有找到技能目录\n' "$repo_root" >&2
  exit 1
fi

cleanup_generated_dirs() {
  local dest="$1"
  [[ -d "$dest/context-store" ]] && rm -rf "$dest/context-store"

  shopt -s nullglob
  local generated
  for generated in "$dest"/*-workspace; do
    rm -rf "$generated"
  done
  shopt -u nullglob
}

register_ccswitch_skill() {
  local src="$1"
  local dest="$2"
  local skill_name
  skill_name="$(basename "$src")"
  local db_path="$HOME/.cc-switch/cc-switch.db"
  [[ -f "$db_path" ]] || return 0

  local readme_url=""
  if [[ -n "$repo_owner" && -n "$repo_name" ]]; then
    readme_url="https://github.com/$repo_owner/$repo_name/blob/$repo_branch/$skill_name/SKILL.md"
  fi

  REPO_OWNER="$repo_owner" \
  REPO_NAME="$repo_name" \
  REPO_BRANCH="$repo_branch" \
  README_URL="$readme_url" \
  python - "$db_path" "$dest" "$skill_name" <<'PY'
import hashlib
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

db_path = Path(sys.argv[1])
skill_dir = Path(sys.argv[2])
skill_name = sys.argv[3]
skill_md = skill_dir / "SKILL.md"
if not skill_md.exists():
    raise SystemExit(f"missing SKILL.md: {skill_md}")

text = skill_md.read_text(encoding="utf-8")
frontmatter = re.search(r"^---\n(.*?)\n---\n", text, re.S)
description = None
if frontmatter:
    for line in frontmatter.group(1).splitlines():
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip()
            if len(description) >= 2 and description[0] == description[-1] and description[0] in {'"', "'"}:
                description = description[1:-1]
            break

owner = os.environ.get("REPO_OWNER", "").strip()
name = os.environ.get("REPO_NAME", "").strip()
branch = os.environ.get("REPO_BRANCH", "main").strip() or "main"
readme_url = os.environ.get("README_URL", "").strip() or None
content_hash = hashlib.sha256(skill_md.read_bytes()).hexdigest()
installed_at = int(time.time())
skill_id = f"{owner}/{name}/{skill_name}" if owner and name else skill_name

con = sqlite3.connect(db_path)
con.execute(
    """
    INSERT INTO skills (
        id, name, description, directory, repo_owner, repo_name, repo_branch, readme_url,
        enabled_claude, enabled_codex, enabled_gemini, enabled_opencode, enabled_hermes,
        installed_at, content_hash, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
        name=excluded.name,
        description=excluded.description,
        directory=excluded.directory,
        repo_owner=excluded.repo_owner,
        repo_name=excluded.repo_name,
        repo_branch=excluded.repo_branch,
        readme_url=excluded.readme_url,
        enabled_claude=excluded.enabled_claude,
        enabled_codex=excluded.enabled_codex,
        enabled_gemini=excluded.enabled_gemini,
        enabled_opencode=excluded.enabled_opencode,
        enabled_hermes=excluded.enabled_hermes,
        installed_at=excluded.installed_at,
        content_hash=excluded.content_hash,
        updated_at=excluded.updated_at
    """,
    (
        skill_id,
        skill_name,
        description,
        skill_name,
        owner or None,
        name or None,
        branch,
        readme_url,
        1,
        1,
        0,
        1,
        0,
        installed_at,
        content_hash,
        0,
    ),
)
if owner and name:
    con.execute(
        """
        INSERT INTO skill_repos (owner, name, branch, enabled)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(owner, name) DO UPDATE SET
            branch=excluded.branch,
            enabled=excluded.enabled
        """,
        (owner, name, branch),
    )
con.commit()
con.close()
PY
}

install_skill() {
  local src="$1"
  local dest_root="$2"
  local skill_name
  skill_name="$(basename "$src")"
  local dest="$dest_root/$skill_name"

  mkdir -p "$dest_root"
  rm -rf "$dest"
  cp -R "$src" "$dest"
  cleanup_generated_dirs "$dest"
  if [[ "$dest_root" == "$HOME/.cc-switch/skills" ]]; then
    register_ccswitch_skill "$src" "$dest"
  fi
  printf '已安装 %s -> %s\n' "$skill_name" "$dest"
}

for target in "${targets[@]}"; do
  for src in "${skill_dirs[@]}"; do
    install_skill "$src" "$target"
  done
done
