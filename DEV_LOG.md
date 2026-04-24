# DEV_LOG.md — DEV LOG 格式规范

> 本文件管：**DEV LOG 的字段、格式、示例、强制规则**。
> 它是展示协议，不是执行证据。
> 全局安全约束 → `AGENTS.md` | 专职定义 → `MULTI_AGENTS.md` | CTRL 协议 → `CTRL_PROTOCOLS.md`

---

## 字段顺序（9 个）

```
[DEV LOG]
🔀 路由     <routing decision>
🤖 模型     <actual model/mode used>
🧩 Skill    <skill match result>
🛠️ 工具     <tool call results — PostToolUse>
🧠 Memory   <domain injected + token savings>
📂 Session  <round + compression state>
🔍 检索     <retrieval scope + recall>
🤝 A2A      <cross-agent communication>
🏷️ 实体     <new/updated entities>
```

---

## 字段规范

### 🔀 路由
```
🔀 路由 <ROLE> | 触发: "<keyword>" | 模式: <normal debug|blocked/fix-now> / <单专职|双并行>
```

### 🤖 模型
```
🤖 模型 <provider/model|alias|none> | effort=<low|adaptive|high|unavailable>
```
- 写本轮实际用于产出内容的模型，以及当前会话的 effort / Think 档位
- 默认保持简短，不再展开 `session/mode/actual` 这类冗余字段
- 若本轮没有需要单独说明的模型切换或排障价值，可省略该字段
- 若本轮未实际调用需要区分的模型，写 `none`
- `effort` 优先取 `session_status` 的 Think 档位；无法核实时写 `unavailable`
- 若无法核实模型，写 `unavailable`

### 🧩 Skill
```
🧩 Skill 命中: <name> | trigger=<reason> | loaded=yes | step=<N/total|completed>
🧩 Skill 命中: none | 原因: <why>
```
- 执行期间每步更新 step 字段
- 执行完写 `completed | output=<摘要>`

### 🛠️ 工具（PostToolUse 注入）
```
🛠️ 工具 <tool>(<target>) → <result_summary> | status=<ok|failed|blocked>
```
- 多次工具调用各占一行
- `status=failed`：附失败原因
- `status=blocked`：附原因（missing_tool / deny_rule / need_auth）
- 无工具调用：`🛠️ 工具 无`

### 🧠 Memory
```
🧠 Memory <domains> | ~<N> tokens | 节省 <X>%
```
- 若 MEMORY.md 未加载（SEARCH 域等），写 `🧠 Memory (SYSTEM) only`
- 若 token 数未知，写 `~ephemeral`（不写 unavailable）

### 📂 Session
```
📂 Session 第 <N> 轮 | recent_turns=<n/20> | ctx=<current/200k> | <未触发自动压缩|已自动压缩@200k>
```
- `第 <N> 轮` 指本次 session 内的轮次（ephemeral，不跨 session 累积）
- `recent_turns=<n/20>` 表示**当前轮次进度 / Layer 2 触发阈值**；阈值变化时，这里的分母也必须同步更新
- `recent_turns` 的推荐来源是 host 在 hook context 中注入的 `current_turn_count`（常见映射：`CLAUDE_TURN_COUNT`）
- 若 session-state.json 不存在或未写入，写 `ephemeral session`（不写 unavailable）
- 跨 session 统计由 heartbeat-agent 负责，不在此字段体现
- `ctx=<current/200k>` 记录**当前上下文占用 / 200k 自动压缩阈值**；数值必须来自 runtime 或工具返回，禁止估算
- `ctx` 单位优先使用 runtime 原生单位；若为 token budget，推荐写法如 `ctx=84k/200k`
- `ctx` 的推荐来源是 host 在 hook context 中注入的 `current_context_tokens` / `context_limit_tokens`
- 若当前上下文占用暂不可读取，写 `ctx=unavailable/200k`
- 本文件只定义 DEV LOG 的展示格式；真正的自动压缩执行逻辑仍以 `CTRL_PROTOCOLS.md` 为准

### 🔍 检索
```
🔍 检索 scope=<DOMAIN> | level=<同域近期|同域归档|跨域> | 召回 <N> 条 | top=[<scores>]
```
- 若未触发检索工具（Level 1 context 已足够），写 `🔍 检索 scope=context | level=L1 | 无需工具`
- 若分数未知，写 `top=ephemeral`（不写 unavailable）

### 🤝 A2A
```
🤝 A2A <FROM> → <TO> <task> | confidence=<X.XX> | needs_ctrl=<true|false>
```
- 仅在发生跨代理通信时输出

### 🏷️ 实体
```
🏷️ 实体 检测到新实体: <entity>=<value>（<date>）→ 已更新 [<DOMAIN>]
```
- 仅在检测到新实体或实体更新时输出

---

## 输出分档

| 档位 | 使用场景 |
|------|---------|
| `normal debug` | 普通执行、检索、审查、改写、读回、非阻塞推进 |
| `blocked/fix-now` | 卡住、证据缺失、用户质疑"是不是没执行"、需要立即补救 |

## Dev Mode 不可省略规则

当 `dev_mode_effective = true` 时：

- 每条用户可见回复都必须包含一个真实的 `[DEV LOG]`
- 不允许因为“简洁输出”“正文隐藏 routing”“减少打扰”而省略
- `routing_visibility=devlog_only` 只表示把路由放进 DEV LOG，不表示可以不展示 DEV LOG
- 只有用户明确要求关闭 dev mode 后，才允许停止输出 `[DEV LOG]`

其中：
- `dev_mode_effective = (memory/session-state.json.dev_mode == true) OR (本轮用户明确说出 "开启 dev mode" / "打开开发者模式")`
- 这条规则是为了兼容 `AGENTS.md` 里“session-state 在回复草拟后、发送前写入”的时序；**开启 dev mode 的当轮就必须切到本模板，不得等下一轮**
- 激活回合若某些 session 字段尚未持久化，按本文件字段规范写 `ephemeral` 或 `unavailable`
- 不得单独回复“已开启 dev mode”却不附带 `[DEV LOG]`

---

## 示例 A：normal debug

```
[DEV LOG]
🔀 路由 ENGINEER | 触发: "改配置" | 模式: normal debug / 单专职
🤖 模型 openai-codex/gpt-5.4 | effort=adaptive
🧩 Skill 命中: agent-review | trigger=workspace 配置审查 | loaded=yes | step=completed
🛠️ 工具 Edit(AGENTS.md) → 插入 Immutable Rules 节，+18行 | status=ok
        Bash(git commit) → hash=f951b9a | status=ok
🧠 Memory (SYSTEM)+[ENGINEER] | ~210 tokens | 节省 72%
📂 Session 第 15 轮 | recent_turns=15/20 | ctx=84k/200k | 未触发自动压缩
🔍 检索 scope=ENGINEER | level=同域近期 | 召回 2 条 | top=[0.91, 0.78]
🏷️ 实体 检测到新实体: AGENTS_version=v2（2026-04-14）→ 已更新 [ENGINEER]
```

## 示例 B：blocked/fix-now

```
[DEV LOG]
🔀 路由 SEARCH | 触发: "查最新论文" | 模式: blocked/fix-now / 单专职
🤖 模型 none | effort=adaptive
🧩 Skill 命中: public-evidence-fetch | trigger=公开网页证据抓取 | loaded=yes | step=2/4
🛠️ 工具 WebFetch(arxiv.org) → 403 Forbidden | status=blocked(missing_tool)
🧠 Memory (SYSTEM) | ~80 tokens
📂 Session 第 20 轮 | recent_turns=20/20 | ctx=unavailable/200k | 已自动压缩@200k
🔍 检索 scope=LEARN | level=同域近期 | 召回 0 条
```

---

## 最低合格线

- **强制项**（不得省略）：`🔀 路由`、`🧩 Skill`、`🛠️ 工具`、`📂 Session`
- `🤖 模型` 为可选项：仅在用户追问模型、模型切换、fallback 命中、或模型信息对排障有直接价值时输出；若输出，只写“本轮用了啥模型 + 当前 effort”
- `⚖️ 置信度` 为可选项：仅在存在证据冲突、不确定性较高、用户质疑结论、或需要显式标注判断依据时输出
- 至少输出 9 个字段中的 4 个
- 有文件改动或校验时，`🔍 检索` 不得省略
- `🤝 A2A` 仅在发生跨代理通信时输出
- `🏷️ 实体` 仅在检测到新实体或实体更新时输出
- 无工具调用时必须写 `🛠️ 工具 无`

---

## 强制输出规则（Immutable，来自 AGENTS.md）

DEV LOG 每轮必须输出，以下情况下不得省略或缩减：

1. Skill 执行期间（每一轮）
2. 复杂任务执行中（涉及多步/文件修改/工具调用）
3. 用户质疑"是不是没执行"或"为什么没做"
4. 发生阻塞、证据缺失、需要补救

**禁止使用内置 session-state.json 序列化格式**：

无论何种触发场景（包括 dev mode 开启、/new 新会话第一轮、系统事件触发），DEV LOG **必须**使用本文件定义的 9 字段模板，不得输出如下内置格式：

```
# ❌ 禁止输出这种格式
routing: User -> CTRL -> ...
session_id: openclaw_meta_...
round: 46
dev_mode: true
...
```

正确做法是读取 DEV_LOG.md 中的字段规范和示例，按模板输出。

**禁止**：
- 以"输出太长"为由省略
- 以"Skill 已执行完"为由省略
- 只输出 Routing 行跳过其他字段
- 把计划、意图、猜测写入字段（必须是 runtime-produced 或 tool-returned 值）
- 字段无真实来源时，写 `unavailable`，不得编造
