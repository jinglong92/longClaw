# longClaw 功能测试案例

> 测试环境：Mac mini M4，`~/.openclaw/workspace`
> 所有命令在 workspace 根目录下执行

---

## 一、系统健康检查

### T01 — longclaw-doctor

```bash
python3 scripts/longclaw-doctor
```

**预期**：每一项显示 `[PASS]`，无 `[FAIL]`

```bash
# JSON 格式
python3 scripts/longclaw-doctor --json
```

---

### T02 — longclaw-status

```bash
python3 scripts/longclaw-status
```

**预期**：显示 DB 路径、Sessions 数量、Tool events 数量、最新 note 时间戳

---

## 二、runtime_sidecar Hook 插件

### T03 — SessionStart：协议注入 + DB 写入

```bash
echo '{"session_id":"smoke-001","platform":"local","topic_key":"test"}' \
  | python3 -m runtime_sidecar.hook_dispatcher SessionStart
```

**预期**：返回 JSON，包含 `message: "Session started. Protocols injected."`

---

### T04 — PreToolUse：rm 命令拦截

```bash
# 普通命令：不拦截
echo '{"session_id":"smoke-001","tool_name":"bash","args":"ls -la"}' \
  | python3 -m runtime_sidecar.hook_dispatcher PreToolUse

# 危险命令：自动加 -i
echo '{"session_id":"smoke-001","tool_name":"bash","args":"rm -rf /tmp/test"}' \
  | python3 -m runtime_sidecar.hook_dispatcher PreToolUse
```

**预期**：第二条返回 `modified_args`，`rm -rf` → `rm -i -rf`

---

### T05 — FileChanged：配置文件变更感知

```bash
echo '{"session_id":"smoke-001","files":["AGENTS.md","foo.txt"]}' \
  | python3 -m runtime_sidecar.hook_dispatcher FileChanged
```

**预期**：返回提示 `Important protocol files changed: AGENTS.md`，`foo.txt` 被忽略

---

### T06 — PostCompact：压缩后重注入

```bash
echo '{"session_id":"smoke-001"}' \
  | python3 -m runtime_sidecar.hook_dispatcher PostCompact
```

**预期**：返回 `message: "PostCompact complete. Protocols reinjected."`

---

## 三、state.db 状态数据库

### T07 — 查询 session 记录

```bash
python3 tools/session_search.py --query smoke-001
```

**预期**：显示 sessions、tool_events、notes 三个表的查询结果

---

### T08 — 按类型查询

```bash
# 只看 tool_events
python3 tools/session_search.py --query rm --kind tool_events

# JSON 格式输出
python3 tools/session_search.py --query smoke --kind sessions --json
```

**预期**：分别显示工具调用记录和 JSON 格式的 session 列表

---

### T09 — 直接查询 SQLite

```bash
sqlite3 memory/state.db \
  "select session_id, platform, topic_key, started_at from sessions order by started_at desc limit 5;"
```

**预期**：表格形式显示最近 5 条 session 记录

---

## 四、记忆系统

### T10 — 索引构建与统计

```bash
python3 tools/memory_entry.py --stats
```

**预期**：显示各域条目数（JOB/LEARN/ENGINEER 等）

---

### T11 — 记忆检索

```bash
# 基础检索
python3 tools/memory_search.py --query "面试"

# 指定域
python3 tools/memory_search.py --query "GRPO" --domain LEARN

# 详细模式（含评分）
python3 tools/memory_search.py --query "换电" --verbose
```

**预期**：返回相关记忆条目，verbose 模式显示 FTS 评分和实体

---

### T12 — inbox 知识摄入

```bash
# 创建测试文件
cat > inbox/test-article.md << 'EOF'
---
domain: LEARN
tags: [Agent, 测试]
importance: high
---
# 测试知识条目

这是一篇用于测试 inbox 摄入管道的文章。
包含关键词：longClaw、OpenClaw、sidecar。
EOF

# 预览（不实际写入）
python3 tools/inbox_processor.py --dry-run

# 实际处理
python3 tools/inbox_processor.py

# 查看统计
python3 tools/inbox_processor.py --stats
```

**预期**：dry-run 显示会生成的块数，实际处理后文件移入 `inbox/processed/`

---

## 五、model_mode 模型模式管理

### T13 — 查看和切换模型模式

```bash
# 查看当前模式
python3 tools/model_mode.py get

# 切换到 primary（禁用自动降级）
python3 tools/model_mode.py set primary
python3 tools/model_mode.py get

# 恢复 auto
python3 tools/model_mode.py set auto
python3 tools/model_mode.py get
```

**预期**：每次 get 返回当前 `model_mode`，set 后立即生效

---

## 六、Skill 系统

### T14 — Skill 目录结构验证

```bash
# 查看所有 skill（应全部是一层目录）
find skills -name "SKILL.md" | sort

# 验证无两层目录
find skills -name "SKILL.md" | awk -F'/' '{print NF}' | sort -u
```

**预期**：`find` 输出全部是 `skills/xxx/SKILL.md` 格式（3段），`awk` 输出只有 `3`

---

### T15 — flatten_skills 脚本（dry-run）

```bash
bash scripts/flatten_skills.sh --dry-run
```

**预期**：显示"移动 0 个 skill，跳过 N 个"（已全部拍平，无需移动）

---

## 七、心跳系统

### T16 — 心跳通畅性检查

```bash
bash tools/test_heartbeat.sh
```

**预期**：6 个检查阶段全部通过，显示索引条目数和各域统计

---

### T17 — Gateway cron 验证

```bash
# 查看已安装的 Gateway cron
/opt/homebrew/opt/node/bin/node \
  /opt/homebrew/lib/node_modules/openclaw/dist/entry.js \
  cron list 2>/dev/null | grep -i longclaw || echo "请用 openclaw cron list 查看"
```

**预期**：显示 `longclaw-heartbeat-am` 和 `longclaw-heartbeat-pm` 两条记录

---

## 八、配置验证

### T18 — settings.json 语法检查

```bash
python3 -m json.tool .claude/settings.json > /dev/null && echo "JSON 语法正确"
```

**预期**：输出 `JSON 语法正确`

---

### T19 — Hook 脚本存在性检查

```bash
for f in \
  scripts/hooks/hook_dispatcher_session_start.sh \
  scripts/hooks/hook_dispatcher_user_prompt_submit.sh \
  scripts/hooks/hook_dispatcher_pre_tool_use.sh \
  scripts/hooks/hook_dispatcher_post_compact.sh \
  scripts/hooks/hook_dispatcher_file_changed.sh; do
  [ -f "$f" ] && echo "✓ $f" || echo "✗ $f 缺失"
done
```

**预期**：5 个文件全部显示 `✓`

---

## 快速全量跑一遍

把上面核心测试串起来，一次执行：

```bash
cd ~/.openclaw/workspace

echo "=== T01 doctor ===" && python3 scripts/longclaw-doctor
echo "=== T02 status ===" && python3 scripts/longclaw-status
echo "=== T03 SessionStart ===" && echo '{"session_id":"smoke-final"}' | python3 -m runtime_sidecar.hook_dispatcher SessionStart
echo "=== T04 PreToolUse rm ===" && echo '{"session_id":"smoke-final","tool_name":"bash","args":"rm /tmp/x"}' | python3 -m runtime_sidecar.hook_dispatcher PreToolUse
echo "=== T05 FileChanged ===" && echo '{"session_id":"smoke-final","files":["AGENTS.md"]}' | python3 -m runtime_sidecar.hook_dispatcher FileChanged
echo "=== T06 PostCompact ===" && echo '{"session_id":"smoke-final"}' | python3 -m runtime_sidecar.hook_dispatcher PostCompact
echo "=== T07 session_search ===" && python3 tools/session_search.py --query smoke-final
echo "=== T10 memory stats ===" && python3 tools/memory_entry.py --stats
echo "=== T13 model_mode ===" && python3 tools/model_mode.py get
echo "=== T18 settings.json ===" && python3 -m json.tool .claude/settings.json > /dev/null && echo "JSON OK"
echo "=== ALL DONE ==="
```
