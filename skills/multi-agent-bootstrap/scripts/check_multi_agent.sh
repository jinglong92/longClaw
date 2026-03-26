#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
MA="$ROOT/MULTI_AGENTS.md"
AG="$ROOT/AGENTS.md"

fail() { echo "[FAIL] $1"; exit 1; }
pass() { echo "[OK] $1"; }

[[ -f "$MA" ]] || fail "MULTI_AGENTS.md not found"
[[ -f "$AG" ]] || fail "AGENTS.md not found"

grep -Eq "Routing: User -> CTRL -> \[[A-Z_]+\] -> CTRL -> User|Routing: User -> CTRL -> \(\[[A-Z_]+\] \|\| \[[A-Z_]+\]\) -> CTRL -> User" "$MA" || fail "routing examples missing in MULTI_AGENTS.md"
grep -q "Routing: User -> CTRL -> \[ROLE\] -> CTRL -> User" "$AG" || fail "mandatory routing rule missing in AGENTS.md"

grep -Eq "LIFE|WORK|LEARN|ENGINEER" "$MA" || fail "core role set missing in MULTI_AGENTS.md"

grep -q "最多 2" "$MA" || echo "[WARN] parallel<=2 not explicitly documented"

pass "multi-agent baseline checks completed"
