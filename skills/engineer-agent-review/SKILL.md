---
name: agent-review
description: OpenClaw/longClaw workspace 代码审查——评估 AGENTS.md/MULTI_AGENTS.md/skills/ 的设计质量，发现规则冲突、token 浪费、逻辑漏洞。
version: 1.0.0
author: jinglong92
license: MIT
requires: ["file_read"]
---

# Agent Review

审查 longClaw workspace 配置文件的设计质量。
核心目标：发现规则冲突、token 浪费、逻辑漏洞，给出可执行改进建议。

## 触发条件

**硬触发关键词（出现任一即命中）**：
- "review workspace" / "review 配置" / "审查一下"
- "检查配置" / "配置有没有问题" / "规则有没有冲突"
- "agent-review" / "/review"
- 用户刚修改了 AGENTS.md / MULTI_AGENTS.md / SKILL.md 并说"帮我看看"

**软触发（ENGINEER 路由后 CTRL 判断）**：
- 用户描述了 CTRL 行为异常（如 DEV LOG 格式乱、路由不对、skill 不触发）

## 审查维度

### 1. 规则一致性
- AGENTS.md 与 MULTI_AGENTS.md 是否有冲突
- 路由规则是否有歧义（同一请求可能路由到多个专家）
- 置信度协议是否在所有专家中统一

### 2. Token 效率
- MEMORY.md 分域注入是否正确（避免全量注入）
- 哪些 SKILL.md 可以缩短（progressive disclosure 原则）
- 是否有重复定义（AGENTS.md 和 MULTI_AGENTS.md 都写了同一规则）

### 3. 逻辑漏洞
- 并行触发条件是否有遗漏场景
- Risk Audit 豁免条件是否过宽
- A2A 协议的超时和降级路径是否完整

### 4. 可维护性
- 规则是否可以被 CTRL 正确理解（避免歧义）
- 新增 SKILL.md 是否与现有角色定义冲突
- 关键变更是否有统一的变更记录机制

## 输出格式
```
审查结果：<通过/有问题>

发现的问题（按严重程度）：
- [P0] <问题描述> → <建议修复>
- [P1] <问题描述> → <建议修复>
- [P2] <问题描述> → <建议修复>

Token 效率分析：
- 当前估算：~X tokens（全量注入）
- 优化后估算：~Y tokens（分域注入）
- 节省：Z%

可执行改进清单：
1. ...
2. ...

[置信度: X.XX] [依据: 配置文件分析]
```
