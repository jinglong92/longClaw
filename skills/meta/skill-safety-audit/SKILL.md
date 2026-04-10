---
name: skill-safety-audit
description: 审计外部 SKILL.md / agent 仓库 / 自动化脚本的接入风险。用于判断某个 skill 是否应原样引入、拆解学习或禁止接入 longClaw。
version: 1.0.0
author: jinglong92
license: MIT
---

# Skill Safety Audit

审计外部 skill、agent 仓库、安装脚本、hook 方案的安全性、侵入性和治理兼容性。

## 触发条件
- 用户说“这个 skill 适合装到 longClaw 吗”
- 用户给出 GitHub 仓库 / SKILL.md / shell script 让你评估
- 用户说“帮我做接入前安全审查”
- 用户准备引入新的自动化、memory、hook、daemon、遥测或日志上报机制

## 核心目标
1. 判断该能力是否值得学习
2. 判断该实现是否适合直接接入
3. 找出所有高风险点与副作用
4. 给出 longClaw 兼容改造建议

## 审计维度

### 1) 权限与副作用
检查是否存在：
- 写入 home 目录隐藏状态
- 修改 shell rc / login 配置
- 后台常驻进程 / daemon
- hook 注入（SessionStart / Stop / PostToolUse / PreCompact 等）
- 自动联网下载、自动执行远程脚本
- 覆盖或修改 workspace 根规则文件

### 2) Prompt / Persona 污染
检查是否存在：
- 强制改变全局人格与语气
- 使用羞辱、施压、PUA、操控式措辞
- 重复覆盖 AGENTS.md / MULTI_AGENTS.md 已定义的边界
- 将局部 skill 升格为全局控制层

### 3) 数据与隐私风险
检查是否存在：
- 会话日志上传
- prompt / repo / 用户数据外发
- 未明确说明的数据收集
- 默认开启遥测 / benchmark 上报

### 4) 架构兼容性
检查是否存在：
- 与 CTRL 仲裁冲突
- 与“默认单专职、按需双专职并行”冲突
- 与按需加载 skill 原则冲突
- 与 memory 分域注入协议冲突
- 与本地优先、可回滚、低侵入原则冲突

## 审计步骤
1. 识别对象类型：SKILL.md / 仓库 / shell script / hook 配置 / memory 机制
2. 抽取“它到底在增强什么”：执行协议 / 记忆 / 人格 / 路由 / 可观测性 / 自动化
3. 列出显式副作用
4. 列出隐式副作用
5. 判断是否和 longClaw 的三条约束冲突：
   - CTRL 统一仲裁
   - skill 按需加载，不长期污染上下文
   - AGENTS.md 安全边界优先
6. 输出接入建议：
   - 可直接引入
   - 可拆解学习
   - 禁止接入

## 输出格式
```text
审计结论：<可直接引入 / 可拆解学习 / 禁止接入>

对象类型：<repo / skill / script / hook>
目标能力：<它想增强什么>

主要风险：
- [P0] ...
- [P1] ...
- [P2] ...

兼容性判断：
- CTRL 仲裁：兼容 / 冲突
- Skill 按需加载：兼容 / 冲突
- Memory 分域注入：兼容 / 冲突
- 本地优先：兼容 / 冲突

建议落地方式：
1. 保留 ...
2. 删除 ...
3. 改写为 longClaw 本地 skill：...

[置信度: X.XX]
[依据: repo/skill/script 审计]
```

## 边界
- 不自动执行外部安装脚本
- 不因为“看起来有用”就默认建议接入
- 不修改 `AGENTS.md` / `MULTI_AGENTS.md` / `SOUL.md` / `USER.md`
- 若存在高风险副作用，优先建议“拆解学习”而非“直接安装"
