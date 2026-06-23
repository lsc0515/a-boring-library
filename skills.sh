#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash skills.sh [codex|claude|both]

Install every skill directory in this repository into the selected skills
folder(s). The default target is both Codex and Claude.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_mode="${1:-both}"

case "$target_mode" in
  both)
    targets=("$HOME/.codex/skills" "$HOME/.claude/skills")
    ;;
  codex)
    targets=("$HOME/.codex/skills")
    ;;
  claude)
    targets=("$HOME/.claude/skills")
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    printf 'Unknown target: %s\n\n' "$target_mode" >&2
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
  printf 'No skill directories found under %s\n' "$repo_root" >&2
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
  printf 'Installed %s -> %s\n' "$skill_name" "$dest"
}

for target in "${targets[@]}"; do
  for src in "${skill_dirs[@]}"; do
    install_skill "$src" "$target"
  done
done
