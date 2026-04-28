# Skills Index

> longClaw 当前启用 Skill 清单（权威索引）。
> `CTRL_PROTOCOLS.md` 仅定义 Skill 运行协议，不再内嵌完整清单。

| Skill | Role | 用途 |
|------|------|------|
| `paper-deep-dive` | `LEARN` | 论文深度解读 |
| `jd-analysis` | `JOB` | 分析岗位 JD，匹配度评级 |
| `longclaw-checkup` | `ENGINEER` | longClaw 运行时体检/诊断 |
| `research-build` | `ENGINEER` | 需求→实现闭环 |
| `research-execution-protocol` | `ENGINEER` | 复杂排障/修 bug |
| `fact-check-latest` | `SEARCH` | 核查最新信息 |
| `public-evidence-fetch` | `SEARCH` | 公开网页证据摘录 |
| `skill-safety-audit` | `META` | 外部 skill 接入审计 |
| `session-compression-flow` | `META` | 会话压缩归档 |
| `multi-agent-bootstrap` | `META` | 多代理架构初始化 |
| `paperbanana` | `LEARN` | 学术论文配图自动生成（需本地安装） |
| `deep-research` | `SEARCH` | 并发多源深度调研（spawn SearchAgent×2-3） |
| `code-agent` | `ENGINEER` | Coding Agent 完整工作流（spawn repo-explorer→执行→验证） |
| `memory-companion` | `BRO/SIS` | 记忆增强陪伴（自动注入近期记忆，BRO/SIS路由时触发） |
| `proactive-heartbeat` | `META` | 主动心跳巡检（cron触发+SessionStart呈现） |

## 维护规则

- Skill 新增或下线时，必须同步更新本索引。
- Skill 重命名时，必须同轮更新 `CTRL_PROTOCOLS.md` 的引用说明（如数量变更）。
- 合并前做一次一致性检查：`rg --files skills | rg "SKILL\\.md$"`，确认目录与本索引无遗漏。
