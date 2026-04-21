# TOOLS.md - Local Capability Bindings

本文件绑定 longClaw skills 到 Mac mini M4 的实际命令、路径和能力边界。
更新规则：skill 反复失败时先更新本文件，不改 SKILL.md。

---

## 环境概览

- 设备：Mac mini M4（24/7 在线）
- 系统：macOS（Apple Silicon，arm64）
- Shell：zsh
- Python：`uv` 管理（`~/.local/bin/uv`），系统 python3 备用
- Node：默认运行时为 `~/.longclaw/node20/current/bin` 下的 Node 20（当前观测：v20.20.2）
- 备用 Node：Homebrew 另有 Node 25（当前观测：`/opt/homebrew/Cellar/node/25.8.2/bin`），部分 OpenClaw 命令需显式 PATH 覆盖使用
- 包管理：Homebrew（`/opt/homebrew/bin/brew`）

---

## Skill 本机绑定

### paper-deep-dive
- 触发路由：LEARN
- 依赖工具：无外部工具，纯 LLM 推理
- 论文获取：若用户给 arXiv 链接，可用 `curl` 或 WebFetch 获取摘要页
- 已知限制：无法直接下载 PDF 正文；若需全文，请用户提供 PDF 或粘贴关键段落

### jd-analysis
- 触发路由：JOB
- 依赖工具：无外部工具，纯 LLM 推理
- 输入支持：JD 文本 / 截图文字 / 招聘网站链接（需 WebFetch 能力）

### agent-review
- 触发路由：ENGINEER
- 依赖工具：本地文件读取（`Read` / `cat`）
- 工作路径：`~/longClaw/`（当前 workspace 根目录）
- 核心文件：`AGENTS.md` / `MULTI_AGENTS.md` / `skills/**/SKILL.md`

### research-build / research-execution-protocol
- 触发路由：ENGINEER
- 依赖工具：文件读写、shell 命令执行
- Python 执行：优先 `uv run python` 或 `python3`
- Node 执行：`node` / `npx`
- 验证命令：`python3 -c "..."` 或直接运行脚本

### fact-check-latest / public-evidence-fetch
- 触发路由：SEARCH
- 依赖工具：WebFetch / WebSearch（需运行时支持）
- 若 WebFetch 不可用：返回 `blocked: no_public_web_fetch_tool`，提示用户提供直链或 PDF

### skill-safety-audit
- 触发路由：META / ENGINEER
- 依赖工具：本地文件读取、可选 WebFetch（审查外部仓库时）
- 冲突优先级最高：与其他 engineer skill 同时命中时，先执行本 skill

### session-compression-flow
- 触发路由：META / CTRL
- 依赖工具：文件读写（写入 `memory/YYYY-MM-DD.md` 和 `MEMORY.md`）
- 压缩落盘路径：`memory/` 目录

### multi-agent-bootstrap
- 触发路由：META / CTRL
- 依赖工具：文件读写
- 核心目标文件：`AGENTS.md` / `MULTI_AGENTS.md`

---

## 能力注册表

### Browser / Web
- Public web fetch：依赖运行时 WebFetch 工具，不保证可用
- Browser automation：Playwright 已安装（`npx playwright`）
- 注意：WebFetch 不可用时不要反复询问授权，直接返回 `blocked: no_public_web_fetch_tool`

### Git / Repo
- 默认 remote：`origin`（GitHub）
- Push 策略：需单独授权（不随文件修改授权自动生效）
- 常用命令：`git status` / `git diff` / `git add` / `git commit` / `git push`

### Python
- 优先：`uv run python` 或 `python3`（系统 python3 在 `/usr/bin/python3`）
- 包管理：`uv pip install` 或 `pip3 install`
- 训练相关：`openclaw_substrate` 模块在 `~/longClaw/openclaw_substrate/`

### Node / npm
- 默认 Node：`~/.longclaw/node20/current/bin/node`，`node --version` 当前观测为 v20.20.2
- Homebrew Node：`brew list --versions node` 当前观测为 25.8.2；若走 Homebrew 路径会变成 Node 25，不等于默认运行时
- 已确认全局包：`@anthropic-ai/claude-code`、`@playwright/cli`
- 未确认存在：`@openai/codex`（不要再假定已全局安装）
- 运行：`node script.js` / `npx <tool>`
- OpenClaw 主会话模型由 OpenClaw 配置决定，不要把本机全局 npm 包是否存在，等同为实际主 LLM 路由事实

### 内存工具
- 索引构建：`python3 tools/memory_entry.py`
- 检索：`python3 tools/memory_search.py --query "..." --domain <DOMAIN>`
- 混合检索（需 Ollama）：加 `--hybrid` 参数
- Ollama：若已安装，`ollama serve` 启动，模型 `nomic-embed-text`

### 文件系统
- workspace 根：`~/longClaw/`（即 `/Users/daijinglong/longClaw/` 或安装位置）
- memory 目录：`memory/`（相对 workspace 根）
- session state：`memory/session-state.json`
- skill 目录：`skills/`

---

## 已知失败模式

| 场景 | 失败原因 | 处理方式 |
|------|---------|---------|
| WebFetch 返回 302 / 认证错误 | 目标页需登录（如美团 KM） | 使用本地 `km` CLI：`~/.local/bin/km -f plain get <DOC_ID>` |
| `uv` 找不到 | PATH 未包含 `~/.local/bin` | 用 `~/.local/bin/uv` 全路径，或 `python3` 备用 |
| Playwright 失败 | 浏览器未安装 | `npx playwright install chromium` |
| memory_search 返回空 | index 未构建 | 先运行 `python3 tools/memory_entry.py` |
| OpenClaw 内置 `memory_search` unavailable / timeout | embedding provider 链路失败（当前已见 Node→Gemini 超时） | 不得表述为“没搜到”；立即 fallback 到 `memory_get` + `read/rg`，如需本地 hybrid 则优先 `python3 tools/memory_search.py`，其 embedding 不可用时自动退回 fts-only |

---

## 维护规则

- skill 反复失败 → 先更新本文件的"已知失败模式"，不改 SKILL.md
- 本机路径/工具变更 → 只改本文件，SKILL.md 保持通用
- 新增本机工具 → 在"能力注册表"中登记
