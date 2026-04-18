#!/bin/bash
set -euo pipefail

SKIP_P2=false
for arg in "$@"; do
  [ "$arg" = "--skip-p2" ] && SKIP_P2=true
done

echo "================================================"
echo " longClaw Memory 检索升级"
echo " P0: scope 协议 | P1: 条目化 | P2: hybrid"
echo "================================================"

echo "--- 前置条件检查 ---"
if [ ! -f "AGENTS.md" ] || [ ! -f "MEMORY.md" ]; then
  echo "[ERROR] 请在 longClaw 仓库根目录运行此脚本"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 需要 Python3"
  exit 1
fi

CURRENT_VER=$(python3 - <<'PY'
import json
try:
    with open('.upgrade_state.json','r',encoding='utf-8') as f:
        print(json.load(f).get('workspace_version','unknown'))
except Exception:
    print('unknown')
PY
)
case "$CURRENT_VER" in
  3.1|3.2a) echo " [OK] workspace_version = ${CURRENT_VER}" ;;
  *) echo " [ERROR] 需要先执行 apply_all_v3.1.sh（当前版本: ${CURRENT_VER}）"; exit 1 ;;
esac

echo "--- P0：route-aware retrieval scope 协议 ---"
if rg -q "^## Memory Retrieval Scope Protocol" AGENTS.md; then
  echo " [SKIP] Memory Retrieval Scope Protocol 已存在"
else
cat >> AGENTS.md <<'EOF'

## Memory Retrieval Scope Protocol

> 核心原则：先决定搜哪里，再决定怎么搜。
> route-aware scope 比 hybrid model 更重要。

### 检索顺序（四级递进，前一级有足够结果则不继续）

```
Level 2：same-domain recent（同域 7 天内）
 → memory/YYYY-MM-DD.md（过去 7 天）中 domain 匹配的条目
 → MEMORY.md 中对应 [DOMAIN] 块

Level 3：same-domain archive（同域全量）
 → memory/YYYY-MM-DD.md（全量）中 domain 匹配的条目
 → tools/artifacts/memory_entries.jsonl 中 domain 匹配的条目

Level 4：cross-domain fallback（跨域兜底）
 → 仅当 Level 2+3 结果数 < 2 时才触发
 → 搜索所有域，结果标注 [跨域]
```
EOF
  echo " [OK] 已追加协议"
fi

echo "--- P1+P2：安装 tools/ 目录 ---"
mkdir -p tools/artifacts
[ -f tools/memory_entry.py ] || { echo "[ERROR] tools/memory_entry.py 不存在"; exit 1; }
[ -f tools/memory_search.py ] || { echo "[ERROR] tools/memory_search.py 不存在"; exit 1; }

echo "--- 构建索引（P1）---"
python3 tools/memory_entry.py --rebuild

if [ "$SKIP_P2" = false ]; then
  echo "--- P2：Ollama 环境检查 ---"
  if command -v ollama >/dev/null 2>&1; then
    echo " [OK] Ollama 已安装"
    if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
      echo " [OK] nomic-embed-text 已就绪，--hybrid 可用"
    else
      echo " [INFO] 运行：ollama pull nomic-embed-text"
    fi
  else
    echo " [INFO] Ollama 未安装，P2 暂不可用（P0+P1 已可用）"
  fi
fi

python3 - <<'PY'
import json
from datetime import datetime, timezone
p='.upgrade_state.json'
try:
    with open(p,'r',encoding='utf-8') as f:
        data=json.load(f)
except Exception:
    data={}
data['memory_retrieval_version']='v1'
data['memory_retrieval_applied_at']=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
with open(p,'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,separators=(',',':'))
print(' [OK] .upgrade_state.json: memory_retrieval_version = v1')
PY

git add AGENTS.md .upgrade_state.json tools/memory_entry.py tools/memory_search.py || true

echo "================================================"
echo " Memory 检索升级完成！"
echo "================================================"
