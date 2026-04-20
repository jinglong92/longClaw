# runtime_sidecar — 中文说明

> English version: [README.md](README.md)

> **一句话定位**：sidecar 是 longClaw 的"基础设施层"，负责把 OpenClaw 触发的 hook 事件转发给 Python 处理模块，并把运行状态记录到本地数据库，供诊断和查询使用。

---

## 为什么需要 sidecar？

longClaw 的架构分三层：

```
OpenClaw（宿主）
    ↓ 触发 hook 事件
longClaw workspace（大脑）
    ↓ CTRL、分域记忆、skill、路由
runtime_sidecar（基础设施）
    ↓ hook 处理、状态记录、健康检查
```

在 sidecar 出现之前，`.claude/settings.json` 里的 hook 都是直接写 shell 命令，比如：

```json
"SessionStart": [{
  "command": "printf '...' >> $CLAUDE_ENV_FILE && cat CTRL_PROTOCOLS.md >> $CLAUDE_ENV_FILE"
}]
```

这样写有几个问题：
- shell 命令越来越长，难以维护
- 一个命令出错会影响整个 hook 链
- 无法写单元测试
- 运行过程没有日志，出问题不知道哪里坏了

sidecar 把这些 shell 命令全部替换成 Python 模块，解决上述问题。

---

## 目录结构

```
runtime_sidecar/
├── hook_dispatcher.py      # 统一入口，接收事件并分发
├── event_bus.py            # 事件总线，把事件路由给对应插件
├── hook_events.py          # 事件类型定义（枚举）
├── plugins/                # 各个 hook 的处理逻辑
│   ├── session_start.py    # 会话启动时：注入协议文件、写 DB
│   ├── post_compact.py     # 压缩后：重新注入协议文件
│   ├── file_changed.py     # 配置文件变更时：提示 CTRL 重读
│   ├── pre_tool_use.py     # 工具调用前：拦截危险命令（如 rm）
│   └── user_prompt_submit.py  # 用户发消息时：处理 /new 命令等
├── state/                  # 本地 SQLite 状态数据库
│   ├── db.py               # 数据库初始化
│   ├── schema.sql          # 建表语句
│   ├── writers.py          # 写入操作
│   └── readers.py          # 查询操作
├── doctor/                 # 健康检查
│   ├── checks.py           # 检查项汇总
│   ├── config_check.py     # 配置文件检查
│   └── state_check.py      # 数据库状态检查
└── logging/
    └── logger.py           # 统一日志格式
```

---

## 工作流程

每次 OpenClaw 触发一个 hook，流程如下：

```
OpenClaw 触发 hook（如 SessionStart）
    ↓
scripts/hooks/hook_dispatcher_session_start.sh
    ↓（调用）
python3 -m runtime_sidecar.hook_dispatcher SessionStart
    ↓
hook_dispatcher.py 读取 stdin 的 JSON 上下文
    ↓
EventBus 找到监听 SessionStart 的插件
    ↓
session_start.py 的 handle_event() 执行：
  - 把 CTRL_PROTOCOLS.md + DEV_LOG.md 注入 $CLAUDE_ENV_FILE
  - 检查 heartbeat-state.json 是否有待处理事项
  - 在 state.db 里记录本次 session
    ↓
结果以 JSON 数组输出到 stdout
```

**关键设计**：每个插件独立运行，一个插件失败不会影响其他插件。

---

## 各 hook 插件说明

### SessionStart — 会话启动

**触发时机**：每次开启新对话时

**做了什么**：
1. 把 `CTRL_PROTOCOLS.md` 和 `DEV_LOG.md` 写入 `$CLAUDE_ENV_FILE`，确保 CTRL 从第一轮就用正确的 DEV LOG 模板
2. 检查 `memory/heartbeat-state.json`，如果有 P0/P1 待处理事项，输出提醒
3. 在 `state.db` 的 `sessions` 表里记录本次会话

### PostCompact — 压缩后重注入

**触发时机**：OpenClaw 对 context 做了压缩（对话太长时自动触发）

**做了什么**：
- 重新把 `CTRL_PROTOCOLS.md` 和 `DEV_LOG.md` 注入 context
- 原因：压缩会清掉 context 里的协议文件，不重注入 CTRL 就"忘"了规则

### FileChanged — 配置文件变更感知

**触发时机**：`AGENTS.md`、`MULTI_AGENTS.md`、`CTRL_PROTOCOLS.md`、`DEV_LOG.md` 被修改时

**做了什么**：
- 输出提示，告诉 CTRL 哪个配置文件变了，下一轮回复前需要重读

### PreToolUse — 工具调用前拦截

**触发时机**：CTRL 准备调用 Bash 工具时

**做了什么**：
- 检测命令里是否有 `rm`，如果有，自动加 `-i` 标志（交互式确认，防止误删）
- 在 `state.db` 的 `tool_events` 表里记录本次工具调用

### UserPromptSubmit — 用户消息提交时

**触发时机**：用户每次发消息时

**做了什么**：
- 检测是否是 `/new` 命令，如果是，触发 `openclaw gateway restart`（清空 context，开启新会话）

---

## state.db — 本地状态数据库

数据库路径：`memory/state.db`

**不要把它和 OpenClaw 自己的 session 存储混淆**——这是 longClaw 自己维护的轻量记录层，用于诊断和查询。

### 主要表

| 表名 | 记录什么 |
|------|---------|
| `sessions` | 每次会话的元数据（session_id、平台、话题、开始/结束时间） |
| `tool_events` | 工具调用记录（工具名、参数、是否成功、耗时） |
| `route_decisions` | CTRL 的路由决策（路由到哪个专职、置信度）|
| `notes` | 各类事件备注（file_changed、compact 等） |

### 查询方式

```bash
# 用脚本查询（推荐）
cd ~/.openclaw/workspace
python3 tools/session_search.py --query test-session-001
python3 tools/session_search.py --query compact --kind notes
python3 tools/session_search.py --query rm --kind tool_events --json

# 直接用 sqlite3
sqlite3 memory/state.db "select * from sessions order by started_at desc limit 5;"
```

---

## 健康检查

```bash
cd ~/.openclaw/workspace

# 文字格式
python3 scripts/longclaw-doctor

# JSON 格式（便于脚本解析）
python3 scripts/longclaw-doctor --json

# 查看当前状态快照
python3 scripts/longclaw-status
```

---

## 新增一个 hook 插件

假设你想新增一个 `PostToolUse` 插件，步骤如下：

**1. 在 `hook_events.py` 里注册新事件类型**

```python
class HookEventType(str, Enum):
    POST_TOOL_USE = "PostToolUse"   # 新增这一行
```

**2. 在 `plugins/` 下新建模块**

```python
# plugins/post_tool_use.py

HANDLED_EVENTS = ["PostToolUse"]

def handle_event(context: dict) -> dict:
    tool_name = context.get("tool_name", "unknown")
    # 你的处理逻辑
    return {"message": f"PostToolUse handled for {tool_name}"}
```

**3. 在 `event_bus.py` 的 `plugin_names` 列表里加上新模块名**

```python
plugin_names = [
    "session_start",
    "post_compact",
    "file_changed",
    "pre_tool_use",
    "user_prompt_submit",
    "post_tool_use",    # 新增这一行
]
```

**4. 在 `scripts/hooks/` 下新建对应的 shell 脚本**（参考其他脚本的写法）

**5. 在 `.claude/settings.json` 里注册新 hook**

---

## 设计原则

- **不修改 OpenClaw**：sidecar 只是在旁边监听和记录，不改动宿主行为
- **插件隔离**：一个插件出错不影响其他插件，也不影响主会话
- **可移除**：删掉整个 `runtime_sidecar/` 目录，longClaw 核心功能不受影响
- **可测试**：每个插件都是普通 Python 函数，可以单独测试
