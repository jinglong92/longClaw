# Changelog

All notable changes to longClaw are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v0.6.0] — 2026-04-18

### Added
- **LLM fallback 路由层**（`tools/llm_fallback.py` + `tools/llm_fallback_proxy.py`）：primary（OpenAI/Codex）失败时自动 fallback 到本地 Ollama（gemma4:e2b），支持 quota 耗尽、限速、超时、连接失败等场景；OpenAI-compatible proxy 让不支持 Ollama 的工具透明走 fallback
- **`runtime/model-fallback.json`**：模型路由配置，定义 primary/fallback 模型和触发/不触发条件；`runtime/model-router.json` 提供多路由规则支持
- **Playwright CLI skill**（`skills/engineer-playwright-cli/`）：浏览器自动化完整技能包，含 session 管理、元素操作、请求 mock、视频录制、tracing、测试生成等 10 个 reference 文档
- **openclaw-paperbanana skill**（`skills/openclaw-paperbanana/`）：从 Clawhub registry 引入，含完整脚本（generate.py / evaluate.py / plot.py）和 provider 参考文档；新增 `.clawhub/lock.json` 追踪 registry 依赖

### Changed
- **`runtime/model-fallback.json`**：fallback 模型从 `gemma2:2b` 修正为 `gemma4:e2b`（本机 Ollama 实际存在的模型）

### Chore
- **脚本归档**：根目录 7 个 `.sh` 脚本统一移入 `scripts/`，保持根目录整洁

---

## [v0.5.1] — 2026-04-18

### Fixed
- **Heartbeat cron 全链路修复**：从"从未真正运行"到"Gateway cron 已验证可达"
  - `setup_heartbeat_cron.sh` 修正 `openclaw --print '…'`（2026.4.15 非法用法）→ 改为 `openclaw agent --agent main --message`
  - cron 环境无 shell alias，改用完整路径 `/opt/homebrew/opt/node/bin/node .../entry.js`
  - `| crontab -` 管道在 Mac mini M4 上永久挂起，改为临时文件 + python3 subprocess 写入（5秒超时）
  - 新增 Gateway cron fallback：system crontab 失败时自动用 `openclaw cron add` 注册，已装好 `longclaw-heartbeat-am`（08:30）和 `longclaw-heartbeat-pm`（18:00）
  - 修正 Gateway URL 缺失问题：system event 需要 `--url ws://localhost:<port>` 和 `--token`，否则事件入队但 CTRL 收不到

- **DEV LOG 模板不生效修复**：新 session 第一轮用 OpenClaw 内置英文格式，而非自定义 9 字段中文模板
  - 根因：`AGENTS.md Every Session` 读取清单缺少 `DEV_LOG.md`，且 PostCompact hook 只在压缩后触发，第一轮无法注入
  - `AGENTS.md` 补充读取 `CTRL_PROTOCOLS.md` 和 `DEV_LOG.md`
  - `SessionStart` hook 新增注入：`cat CTRL_PROTOCOLS.md DEV_LOG.md >> $CLAUDE_ENV_FILE`

- **Skill 不进 registry 修复**：14 个 skill 因目录两层（`skills/<group>/<skill>/`）被 OpenClaw workspace discovery 忽略
  - 全部拍平为一层（`skills/<group>-<skill>/`），保留分类前缀语义
  - 新增 `flatten_skills.sh` 批量迁移脚本（支持 `--dry-run`）
  - 同步更新 README / README.en.md 中的路径引用

### Added
- **`docs/longclaw-practice.md` 大幅扩充**：新增 §2.0-2.3（借鉴故事）、§3.0（inbox 管道）、§6.0（Mac mini 已知问题）、问题 0（skill registry 排查）
- **配图 fig9-fig14**：6 张浅色 PPT 配图，覆盖 Harness 迭代、Claude Code 借鉴、Hermes 借鉴、自研迭代、inbox 管道、skill discovery 根因

---

## [v0.5.0] — 2026-04-17

### Added
- **个人知识摄入管道（inbox/）**：新增 `inbox/` 目录作为知识摄入入口，支持 `.md`/`.txt` 文件，可通过 YAML frontmatter 指定域/标签/重要性
- **`tools/inbox_processor.py`**：
  - 解析 inbox 文件 → 提取域/实体/重要性 → 分块（400 token，80 token 重叠）
  - 写入 `tools/artifacts/knowledge_entries.jsonl`（追加，不覆盖）
  - 处理完自动移动到 `inbox/processed/`
  - 支持 `--dry-run` / `--stats`
- **memory_search 双索引合并**：`tools/memory_search.py` 新增 `load_all()`，检索时自动合并 `memory_entries.jsonl`（对话记忆）和 `knowledge_entries.jsonl`（inbox 知识库）
- **heartbeat-agent 自动处理**：P2 系统健康巡检新增 inbox/ 扫描步骤，发现新文件自动触发处理

---

## [v0.4.2] — 2026-04-17

### Changed
- **DEV LOG `unavailable` → `ephemeral`**：语义修正，反映"临时会话字段未持久化"的预期行为而非系统异常；`📂 Session` 加注释说明 ephemeral session 为本次运行内轮次，跨 session 统计由 heartbeat-agent 负责
- **压缩层重命名**：Layer 0/A/B 统一改为数字编号（Layer 1 Trim / Layer 2 Summarize / Layer 3 Compact / Layer 4 Archive），含义更直觉

### Added
- **heartbeat-agent 跨 session 统计**：P2 巡检新增聚合统计（近 7 天活跃天数、各域 memory 条目数、skill 触发频率），写入 `heartbeat-state.json` 的 `session_stats` 字段
- **记忆机制 Mermaid 原理图**（`docs/memory-compression-guide.md`）：三层记忆架构总览、分域注入原理、四级检索流程、四层压缩协作全景，可直接截图放 PPT
- **Skill 触发条件优化**：`deep-research` 加硬触发关键词（"深度调研"/"多个来源"等），`memory-companion` 收紧为仅 BRO/SIS 路由时触发

---

## [v0.4.1] — 2026-04-16

### Added
- **`/new` 命令支持**：微信发 `/new` 触发 `openclaw gateway restart`，真正清空 context window，等价于原生 `/new` 命令。推荐用法：需要归档时先手动要求归档，再发 `/new` 开启干净新会话。

---

## [v0.4.0] — 2026-04-16

### Added
- **介绍站点**：README 顶部添加可视化介绍页面链接，便于读者快速概览
- **arXiv 技术报告草稿**：`docs/arxiv-paper/longclaw-paper.md`，完整 9 节结构，含 Route-Aware Memory Injection 形式化公式
- **面试故事卡片**：`docs/interview-story-card.md`，三层递进故事 + JD 对照 + 5 个高频追问标准答案
- **技术深度解析整合文档**：`docs/longclaw-technical-deep-dive.md`，716 行，整合记忆/压缩/多模型/Harness/Coding Agent 五个方向

---

## [v0.3.0] — 2026-04-14

### Added
- **Coding Agent 架构**
  - `repo-explorer` subagent：自主探索 codebase，返回结构化文件地图（只读，5步流程）
  - `code-agent` skill：完整工作流（探索→计划→执行→验证→交付），最多重试 2 次
  - 学习计划文档：`docs/coding-agent-learning-plan.md`，含 SWE-agent/Aider/SWE-bench 学习路径和 5 个里程碑

- **Claude Code 内部架构解析**：`docs/claude-code-internals.md`，基于 sourcemap 逆向分析，含 10 个核心设计模式、Agent Loop 伪代码、Fork Agent 缓存经济学

- **Proactive Heartbeat Agent**
  - `heartbeat-agent` subagent：cron 08:30/18:00 定时巡检，P0/P1 事项写入 `heartbeat-state.json`
  - `proactive-heartbeat` skill：SessionStart hook 读取状态，用户开口时呈现待处理事项
  - `setup_heartbeat_cron.sh`：一键安装 cron job

- **AI 搜索（并发 SearchAgent）**
  - `search-agent` subagent：并发多源搜索，只有 WebFetch/Read/Grep 权限
  - `deep-research` skill：拆解问题 → spawn search-agent×2-3 → RRF 融合 → 综合报告

- **AI 陪伴（MemoryAgent 注入）**
  - `memory-agent` subagent：BRO/SIS 路由时后台检索近期记忆，只读
  - `memory-companion` skill：注入情绪状态/上次话题，让陪伴有"记得你"的感觉

- **paperbanana skill**：学术论文配图自动生成（Apache-2.0，5.8k ⭐），需本地安装

- **Harness 工程改造**（`.claude/settings.json`）
  - `PostCompact` hook：原生压缩后自动重注入 CTRL_PROTOCOLS.md + DEV_LOG.md
  - `FileChanged` hook：配置文件变更时自动感知
  - `PreToolUse` hook：`rm` 命令自动改写为 `trash`（updatedInput 机制）
  - `SessionStart` hook：检测 heartbeat-state.json，有 P0/P1 时提示 CTRL 呈现

- **Skill 依赖声明**：所有 SKILL.md 新增 `requires` frontmatter 字段，命中前验证工具可用性
- **SOUL.md 公开**：从 .gitignore 移出，补充 Multi-Agent Context 节
- **USER.md.example / MEMORY.md.example**：公开模板，包含所有字段说明

### Changed
- **AGENTS.md 重构**：583 行 → 189 行，合并重复规则；新增 Deny > Ask > Allow 三层权限 + 6 条 Immutable Rules；修复行动死锁（`doing:` 收紧为同轮已发起工具调用）
- **MULTI_AGENTS.md 拆分为三文件**（解决幻觉问题）
  - `MULTI_AGENTS.md`（175 行）：专职代理定义 + 路由规则
  - `CTRL_PROTOCOLS.md`（177 行）：Skill 加载 / 压缩 / 检索 / Skill 提议
  - `DEV_LOG.md`（149 行）：DEV LOG 9 字段格式 + 强制输出规则
- **DEV LOG 新增 🛠️ 工具字段**：PostToolUse 强制注入，工具调用结果可观测
- **Skill 命中即触发**：新增空转禁止规则，Skill 执行期间每步必须当轮完成
- **压缩阈值**：Layer A 触发轮数从 12 → 20
- **Subagent model**：全部改为 `inherit`，继承主 session 的 Codex（Mac mini 未购 Haiku）
- **架构描述修正**：明确 longClaw 是 OpenClaw workspace 改造层，原生能力直接可用
- **README 全面更新**：中英文同步，补充 Subagent 架构、Harness 改造、14 个 skill 描述

### Fixed
- 修复四级检索扩展阈值：从差值判断（top1-top2 < 0.05）改为绝对分数（top1 < 0.3），避免低分区间过敏感
- 修复 memory_entry.py 域块解析：兼容 `[JOB]` / `## [JOB]` / `# [JOB]` 三种格式
- 修复 session_id 无生成规则：明确格式 `openclaw_{domain}_{YYYY-MM-DD}`
- 修复 Layer A 与 OpenClaw 原生 compaction 边界模糊问题
- 修复 multi-agent-bootstrap/SKILL.md 引用不存在路径（references/ → tools/）
- 修正 PROFILE_CONTRACT.md 过时字段（Codex → 正确标注）

---

## [v0.2.0] — 2026-04-12

### Added
- **Workspace 完整性加固**：执行完整性硬规则、Web evidence gate 边界、Session state contract
- **DEV LOG 模板正式化**：8 字段结构、两种分档（normal debug / blocked/fix-now）、最低合格线
- **CTRL 协议从 AGENTS.md 迁移**：Skill 加载、Context Compression、Memory Retrieval Scope、Proactive Skill Creation 统一归 MULTI_AGENTS.md
- **memory_search.py 升级**：实体提取扩展（Shopee/longClaw/Codex/camelCase），扩展停止条件优化

### Changed
- 授权模型收口：禁止使用"Anything you're uncertain about"类模糊规则
- AGENTS.md 作用域边界明确：只管安全约束，不管路由/专职/CTRL 协议

---

## [v0.1.0] — 2026-04-10

### Added
- **10 个 Workflow Skills**（Progressive Disclosure）
  - `jd-analysis`：JD 分析，匹配度评级
  - `paper-deep-dive`：论文 8 模块深度解读
  - `agent-review`：workspace 配置审查
  - `fact-check-latest`：多源交叉验证最新信息
  - `research-execution-protocol`：证据驱动工程执行协议
  - `research-build`：需求→实现闭环
  - `skill-safety-audit`：外部 skill 接入安全审计（优先级最高）
  - `session-compression-flow`：压缩落盘 + 新会话衔接
  - `multi-agent-bootstrap`：多代理架构初始化
  - `public-evidence-fetch`：公开网页证据抓取
- **Memory 检索工具**：`tools/memory_entry.py`（JSONL 索引构建）+ `tools/memory_search.py`（route-aware FTS + Hybrid Embedding）
- **openclaw_substrate 训练底座**：Trace → Judge → Dataset → MLX/LLaMA-Factory 完整 pipeline 设计
- **PROFILE_CONTRACT.md**：用户背景、风险优先级、简历快照，各专职代理解释口径统一
- **CONTRIBUTING.md**：贡献指南
- **Privacy**：MEMORY.md / memory/ / USER.md 加入 .gitignore

### Changed
- README 重构：三系统定位对比（OpenClaw / Hermes / longClaw）、核心差异矩阵、Quick Start

---

## [v0.0.1] — 2026-03-21 ~ 2026-04-09

### Initial Setup
- 基于 OpenClaw 建立 multi-agent workspace
- CTRL 总控 + 10 专职代理（LIFE/JOB/WORK/ENGINEER/PARENT/LEARN/MONEY/BRO/SIS/SEARCH）
- 语义路由关键词表、A2A 协议、置信度仲裁协议（P0-P4）
- SOUL.md 人格契约（truth-first advisor）
- 用户偏好记录（称呼龙哥、直接挑战式顾问风格）
- MEMORY.md 分域块设计（[SYSTEM]/[JOB]/[WORK]/[LEARN] 等）
- 多代理架构图（Mermaid）
- LEARNING_GUIDE_FOR_JINGLONG.md：多代理系统设计原理学习手册
