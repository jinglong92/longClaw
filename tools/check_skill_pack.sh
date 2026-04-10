#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${1:-$(pwd)}"

check_file() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    printf '[check] missing: %s\n' "$f"
    exit 1
  fi
  printf '[check] ok: %s\n' "$f"
}

check_file "$ROOT_DIR/skills/meta/skill-safety-audit/SKILL.md"
check_file "$ROOT_DIR/skills/engineer/research-execution-protocol/SKILL.md"
check_file "$ROOT_DIR/skills/engineer/research-build/SKILL.md"
check_file "$ROOT_DIR/docs/skills-roadmap-v1.md"

printf '\n[check] preview names:\n'
grep -R "^name:" "$ROOT_DIR/skills/meta/skill-safety-audit/SKILL.md" "$ROOT_DIR/skills/engineer/research-execution-protocol/SKILL.md" "$ROOT_DIR/skills/engineer/research-build/SKILL.md"
