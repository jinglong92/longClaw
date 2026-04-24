---
name: longclaw-checkup
description: longClaw 运行时体检与诊断。用于检查 skill 不触发、hook 不生效、DEV LOG 异常、state.db 记账异常、memory 检索退化、配置迁移不完整等问题。Use when the user says 体检、自检、诊断、doctor、status、排查 longClaw、skill 不触发、hook 有问题、sidecar 异常、DEV LOG 乱了.
version: 1.0.0
author: jinglong92
license: MIT
requires: ["file_read", "shell_exec"]
---

# longClaw Checkup

对 longClaw 做“先体检、后深挖”的诊断闭环。
目标不是泛泛 review，而是快速回答三件事：

1. 现在有没有明显异常
2. 异常落在哪一层
3. 下一步最小修复动作是什么

## 触发条件

**硬触发关键词（出现任一即命中）**：
- "体检一下" / "自检一下" / "诊断一下"
- "doctor 一下" / "跑下 doctor" / "看看 status"
- "排查 longClaw" / "longClaw 有啥问题"
- "skill 不触发" / "为什么没命中 skill"
- "hook 没生效" / "sidecar 有问题"
- "DEV LOG 乱了" / "路由不对" / "session 不对"
- "memory 检索有问题" / "state.db 有问题"
- 用户发 `/checkup` / `/doctor`

**软触发（ENGINEER 路由后 CTRL 判断）**：
- 用户描述的是运行异常、配置漂移、诊断请求，而不是代码实现需求
- 任务目标是“定位问题在哪一层”，不是立刻改代码

## 不触发条件
- 用户要改代码、修 bug、补功能：用 `research-execution-protocol` 或 `code-agent`
- 用户要接入外部 skill / 仓库并评估风险：用 `skill-safety-audit`

## 分层模型

体检时按 5 层排查，不要一上来读一堆文件。

1. **L0 总览层**
   - 看 `doctor` 和 `status`
   - 判断是否已有 FAIL / WARN / 空账本 / 路径异常

2. **L1 Skill / 配置层**
   - 看 skill registry、skill 目录层级、frontmatter、`.claude/settings.json`
   - 判断 skill 是否“根本没进 registry”或 hook dispatcher 未接入

3. **L2 Sidecar / ledger 层**
   - 看 `memory/state.db`、`sessions` / `route_decisions` / `tool_events` 计数
   - 判断是否是 sidecar 未写入、schema 异常、会话本身是 ephemeral

4. **L3 协议 / 注入层**
   - 看 `AGENTS.md`、`CTRL_PROTOCOLS.md`、`DEV_LOG.md`、相关 hook 插件
   - 判断是否是协议未重注入、`PostCompact` 补救失败、DEV LOG 模板漂移

5. **L4 定向深挖层**
   - 只在前四层发现线索后，才读具体文件 / 日志 / 插件实现

## 标准流程

### Step 1：先跑最便宜的体检

立即执行：

```bash
python3 scripts/longclaw-doctor --json
python3 scripts/longclaw-status --json
```

若命令不可执行，再退回读取：
- `runtime_sidecar/doctor/checks.py`
- `runtime_sidecar/doctor/config_check.py`
- `runtime_sidecar/state/readers.py`

### Step 2：按症状决定分支

#### 分支 A：skill 不触发 / 命中异常

优先检查：
- `skills/` 目录是否为一层目录
- 目标 skill 的 `name` / `description` / `requires`
- 是否存在 3-5 个硬触发关键词
- 若环境可用，检查 registry 中是否真的有该 skill

重点结论只回答：
- 没进 registry
- 进 registry 但触发词太软
- 命中后不执行
- `requires` 不满足

#### 分支 B：hook / sidecar / DEV LOG 异常

优先检查：
- `.claude/settings.json` 是否包含 `hook_dispatcher`
- `runtime_sidecar/plugins/` 对应事件插件是否存在
- `memory/state.db` 是否存在、是否能写入
- `scripts/hooks/` 是否与 sidecar 分发器一致
- `DEV_LOG.md` 与 hook 注入提醒是否一致

重点结论只回答：
- dispatcher 没接上
- sidecar 写账本失败
- session 是 ephemeral，不是 bug
- `PostCompact` / `SessionStart` 注入链断裂

#### 分支 C：memory / recall 异常

优先检查：
- `tools/memory_search.py` 是否存在
- `memory/heartbeat-state.json` / `memory/session-state.json` 是否可解析
- 检索异常是“没索引”还是“embedding provider 不可用”
- 是否应该 fallback 到 `read/rg` 或 fts-only

重点结论只回答：
- 索引缺失
- embedding 链路失败
- fallback 路径错误
- 其实是预期行为，不是 bug

### Step 3：输出最小诊断结论

不要输出散乱观察，统一压成以下格式：

```text
体检结论：<健康 / 有警告 / 有故障>

摘要：
- <一句话总结当前最重要的问题或“未见明显异常”>

分层结果：
- [L0] doctor/status：<PASS/WARN/FAIL + 关键信息>
- [L1] skill/config：<结论>
- [L2] sidecar/ledger：<结论>
- [L3] protocol/injection：<结论>
- [L4] targeted drilldown：<仅在实际深挖时填写>

发现的问题（按严重度）：
- [P0] ...
- [P1] ...
- [P2] ...

下一步最小动作：
1. ...
2. ...
3. ...
```

## 执行原则

- 先跑 `doctor` / `status`，不要一上来全文 review
- 先回答“哪一层坏了”，再回答“怎么修”
- 若某层已有明确故障，不继续无意义扩大排查范围
- 若当前只是 warning，不要夸大为故障
- 若现象属于预期行为，明确写“预期行为，不是 bug”

`longclaw-checkup` 负责运行时体检：
- `doctor`
- `status`
- hook
- `state.db`
- skill 发现/命中
- DEV LOG 注入链
- memory 检索退化

## 一句话心法

先跑现成体检入口，定位故障层，再做最小深挖，不把“review 文档”当成“诊断系统”。
