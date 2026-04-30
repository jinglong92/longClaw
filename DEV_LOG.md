# DEV_LOG.md — DEV LOG 格式规范

> 展示协议，不是执行证据。安全约束 → `AGENTS.md` | 专职 → `MULTI_AGENTS.md` | CTRL → `CTRL_PROTOCOLS.md`

## 全局规则

- **数据来源**：所有字段值必须来自本轮 `session_status()` / runtime / tool returns / hook 注入；禁止沿用上一轮缓存或编造。
- **不可读时**：整行写 `unavailable`（或字段内 `unavailable` / `none` / `ephemeral`，按下方规范），但**不得省略强制项**。
- **渲染前**：必须调用 `session_status()` 取本轮 ctx / tokens / cache / compactions / think；ctx 不可用才回退 `[ctx-preflight]` hook。
- **位置约束**：当 `session-state.dev_log_position=tail` 时，`[DEV LOG]` 必须位于每轮回复正文末尾，不得前置到正文上方。
- **禁止内置裸格式**：不得输出 `session_id:` / `round:` / `dev_mode:` 这类 JSON 风格裸字段块，必须按下方模板渲染。

## 字段模板（10 个，按此顺序）

```
[DEV LOG]
🔀 路由     <ROLE> | 触发: "<keyword>" | 模式: <normal debug|blocked/fix-now> / <单专职|双并行>
🤖 模型     <provider/model|none> | effort=<low|medium|high|adaptive>
🧮 Tokens   in=<N> | out=<N> | cache=<X%> hit | cached=<N> | new=<N>
🧩 Skill    命中: <name> | trigger=<reason> | loaded=yes | step=<N/total|completed>   # 或: 命中: none | 原因: <why>
🛠️ 工具     <tool>(<target>) → <summary> | status=<ok|failed|blocked>                # 多次调用各占一行；无调用写 "无"
🧠 Memory   <domains> | ~<N> tokens | 节省 <X>%                                       # 未加载 MEMORY.md 写 "(SYSTEM) only"
📂 Session  第 <N> 轮 | ctx=<cur>/200k (<P%>) | compactions=<n> | tool_events=<n> | trim_events=<n> | <未触发压缩|Layer 2 已触发>
🔍 检索     scope=<DOMAIN> | level=<同域近期|同域归档|跨域> | 召回 <N> 条 | top=[<scores>]   # 未触发: scope=context | level=L1 | 无需工具
🤝 A2A      <FROM> → <TO> <task> | confidence=<X.XX> | needs_ctrl=<true|false>        # 仅跨代理通信时输出
🏷️ 实体     检测到新实体: <entity>=<value>（<date>）→ 已更新 [<DOMAIN>]                # 仅有新实体时输出
```

## 字段补充约定

- **🤖 模型**：仅输出 `provider/model` 与 `effort`；`effort` 取 Think 档位。本轮无模型差异写 `none`。
- **🧮 Tokens**：单位与 banner 一致（`7.2k` / `570` / `13k`），不二次换算。session_status 不可用时整行写 `🧮 Tokens unavailable`。极短首轮可写 `in=0 | out=ephemeral`。
- **🧩 Skill**：执行期每步刷新 step；完成写 `step=completed | output=<摘要>`。
- **📂 Session**：
  - `第 N 轮` 为本 session 内轮次（不跨 session 累积）。
  - `tool_events` / `trim_events` 取自 UserPromptSubmit hook 的 `[sidecar]` 注入；hook 缺失写 `tool_events=0 | trim_events=0 | source=hook-offline`。
  - session-state.json 不存在写 `ephemeral session`。
  - 可附 `recap=memory/recap.json`；但 `source=hook-offline` 时 recap 内 tool 字段不可信。
- **🔍 检索**：分数未知写 `top=ephemeral`。

## 输出分档

| 档位 | 场景 |
|------|------|
| `normal debug` | 普通执行、检索、改写、读回、非阻塞推进 |
| `blocked/fix-now` | 卡住、证据缺失、用户质疑"是不是没执行"、需立即补救 |

## 强制输出场景（满足任一即必须输出，不得省略或缩减）

1. Skill 执行期间（每一轮）
2. 复杂任务（多步 / 文件修改 / 工具调用）
3. 用户质疑"是不是没执行"或"为什么没做"
4. 发生阻塞、证据缺失、需要补救
5. `dev_mode_effective = true`
6. 用户明确要求显示 DEV LOG

`dev_mode_effective = (session-state.json.dev_mode == true) OR (本轮明确说"开启 dev mode" / "打开开发者模式")`。
开启的当轮就必须切到本模板，不得等下一轮；尚未持久化的字段按"全局规则"写 `ephemeral` / `unavailable`。

## 最低合格线

- **强制项**（不可省略）：`🔀 路由` `🤖 模型` `🧮 Tokens` `🧩 Skill` `🛠️ 工具` `📂 Session`
- 至少输出 10 个字段中的 6 个
- 有文件改动或校验时，`🔍 检索` 不得省略
- 无工具调用必须写 `🛠️ 工具 无`
- `🤝 A2A` / `🏷️ 实体` 仅按各自触发条件输出
- `⚖️ 置信度` 可选：证据冲突、不确定性高、用户质疑结论时才加

## 禁止

- 以"输出太长" / "Skill 已执行完" / "简洁输出"为由省略
- 只输出 🔀 路由 一行跳过其他字段
- 写入计划、意图、猜测（必须 runtime-produced / tool-returned）
- 字段无真实来源时编造数据（应写 `unavailable`）
- 输出内置 JSON 裸块（`session_id:` / `round:` / `dev_mode:` 等）

## 示例：normal debug

```
[DEV LOG]
🔀 路由 ENGINEER | 触发: "改配置" | 模式: normal debug / 单专职
🤖 模型 openai-codex/gpt-5.4 | effort=medium
🧮 Tokens in=7.2k | out=570 | cache=65% hit | cached=13k | new=0
🧩 Skill 命中: longclaw-checkup | trigger=体检 workspace | loaded=yes | step=completed
🛠️ 工具 Edit(AGENTS.md) → 插入 Immutable Rules，+18行 | status=ok
        Bash(git commit) → hash=f951b9a | status=ok
🧠 Memory (SYSTEM)+[ENGINEER] | ~210 tokens | 节省 72%
📂 Session 第 15 轮 | ctx=21k/200k (10%) | compactions=0 | tool_events=12 | trim_events=2 | 未触发压缩
🔍 检索 scope=ENGINEER | level=同域近期 | 召回 2 条 | top=[0.91, 0.78]
🏷️ 实体 检测到新实体: AGENTS_version=v2（2026-04-14）→ 已更新 [ENGINEER]
```

## 示例：blocked/fix-now（仅展示差异行）

```
🔀 路由 SEARCH | 触发: "查最新论文" | 模式: blocked/fix-now / 单专职
🛠️ 工具 WebFetch(arxiv.org) → 403 Forbidden | status=blocked(missing_tool)
📂 Session 第 20 轮 | ctx=84k/200k (42%) | compactions=2 | tool_events=35 | trim_events=12 | Layer 2 已触发
```
