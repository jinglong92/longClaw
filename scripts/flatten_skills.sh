#!/usr/bin/env bash
# flatten_skills.sh — 把两层分组目录拍平为一层，保留分类前缀
# 用法：bash flatten_skills.sh [--dry-run]
#
# 效果：
#   skills/job/jd-analysis/SKILL.md       → skills/job-jd-analysis/SKILL.md
#   skills/learn/paper-deep-dive/SKILL.md → skills/learn-paper-deep-dive/SKILL.md
#   skills/<group>/<skill>/SKILL.md       → skills/<group>-<skill>/SKILL.md
#
# 已在一层的 skill（如 skills/multi-agent-bootstrap/SKILL.md）不移动。

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")" && pwd)/skills"
DRY_RUN=false

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

echo "=== flatten_skills.sh ==="
echo "skills dir: $SKILLS_DIR"
$DRY_RUN && echo "模式: DRY-RUN（只预览，不实际移动）" || echo "模式: 实际执行"
echo ""

moved=0
skipped=0

# 遍历所有两层深度的 SKILL.md
while IFS= read -r skill_md; do
  rel="${skill_md#$SKILLS_DIR/}"       # 相对路径，如 job/jd-analysis/SKILL.md
  parts=(${rel//\// })                  # 按 / 分割

  if [[ ${#parts[@]} -ne 3 ]]; then
    # 不是两层（一层或三层以上），跳过
    skipped=$((skipped + 1))
    continue
  fi

  group="${parts[0]}"   # job
  skill="${parts[1]}"   # jd-analysis
  # parts[2] == SKILL.md

  src_dir="$SKILLS_DIR/$group/$skill"
  dst_dir="$SKILLS_DIR/$group-$skill"

  if [[ -d "$dst_dir" ]]; then
    echo "  [SKIP] $group-$skill/ 已存在，跳过"
    skipped=$((skipped + 1))
    continue
  fi

  echo "  [MOVE] skills/$group/$skill/ → skills/$group-$skill/"

  if ! $DRY_RUN; then
    mv "$src_dir" "$dst_dir"
    # 如果 group 目录现在是空的，删掉
    if [[ -d "$SKILLS_DIR/$group" ]] && [[ -z "$(ls -A "$SKILLS_DIR/$group")" ]]; then
      rmdir "$SKILLS_DIR/$group"
      echo "         └─ 清理空目录 skills/$group/"
    fi
  fi

  moved=$((moved + 1))
done < <(find "$SKILLS_DIR" -name "SKILL.md" | sort)

echo ""
echo "完成：移动 $moved 个 skill，跳过 $skipped 个"
$DRY_RUN && echo "（DRY-RUN 模式，实际未移动任何文件）"
echo ""
echo "下一步："
echo "  1. 检查 skills/ 目录结构是否符合预期"
echo "  2. 重启 OpenClaw 或新开 session（旧 session 沿用旧 skill 列表快照）"
echo "  3. openclaw skills list --json | jq '.skills[] | select(.source==\"openclaw-workspace\") | .name'"
