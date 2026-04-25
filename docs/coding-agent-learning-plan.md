# Coding Agent 学习计划

> 版本：2026-04-14
> 基础：longClaw（底层 OpenClaw + Codex）
> 目标：从"ENGINEER 角色给建议"升级到"自主执行代码修改的 Coding Agent"

---

## 一、你现在在哪里，要去哪里

### 现状：ENGINEER 角色模式

```
用户："帮我修这个 bug"
    ↓
ENGINEER 专职
    → 分析问题
    → 给出修改建议
    → 用户自己去改
```

**瓶颈**：ENGINEER 不知道代码在哪里，每次都要用户告诉它；它只能"建议"，不能"执行"。

### 目标：Coding Agent 模式

```
用户："帮我修这个 bug"
    ↓
code-agent skill
    → repo-explorer 自主探索 codebase
    → 制定修改计划（用户确认）
    → 自主执行修改
    → 运行测试验证
    → 失败自动换路
    → 交付可验证的 diff
```

**核心差异**：从"告诉你怎么做"变成"帮你做完"。

---

## 二、Coding Agent 的核心能力拆解

一个真正的 coding agent 需要五个能力，你目前有哪些：

| 能力 | 描述 | longClaw 现状 |
|------|------|--------------|
| **Codebase 理解** | 自主探索 repo，定位相关文件 | ❌ 缺，需要用户指定文件 |
| **修改计划制定** | 分析影响范围，列出改动清单 | ⚠️ 有但依赖用户提供上下文 |
| **代码执行修改** | 多文件 Edit/Write，保持一致性 | ✅ OpenClaw 原生支持 |
| **测试验证** | 运行测试，解读结果 | ⚠️ 能跑，但没有结构化流程 |
| **失败换路** | 测试失败后系统性换策略 | ✅ research-execution-protocol 覆盖 |

**最大缺口是"Codebase 理解"**——这是本次改造的核心。

---

## 三、本次改造：repo-explorer + code-agent

### 3.1 repo-explorer subagent

**文件**：`.claude/agents/repo-explorer.md`

**设计思路**：

传统 coding agent（如 SWE-agent）用 ACI（Agent-Computer Interface）解决"LLM 看代码"的问题——专门设计适合 LLM 操作的命令行界面。longClaw 的方案是用 subagent 隔离探索过程：

```
用户问题
    ↓
repo-explorer（独立 context，只读工具）
    Step 1：结构扫描（find/ls）
    Step 2：关键词定位（grep）
    Step 3：深度读取（read）
    Step 4：依赖追踪（import 关系）
    ↓
返回结构化文件地图
    ↓
ENGINEER / code-editor 使用文件地图执行修改
```

**为什么用 subagent 而不是直接让 ENGINEER 探索**：

1. **上下文隔离**：探索过程会产生大量中间结果（文件列表、grep 输出），用 subagent 隔离后这些噪声不会污染主 context
2. **并发可能性**：未来可以同时 spawn 多个 repo-explorer 探索不同方向
3. **可复用**：repo-explorer 的结果可以被 code-agent / longclaw-checkup / research-execution-protocol 共用

**关键设计**：结构化输出

repo-explorer 不输出自然语言总结，而是输出固定格式的文件地图：

```
1. <文件路径> [核心]
   - 作用：<一句话>
   - 关键代码：<片段>
   - 依赖：<import 关系>
   - 被依赖：<反向依赖>

修改建议入口：<文件:行号>
风险点：<副作用>
```

这让 ENGINEER 可以直接"消费"结果，而不需要再次理解。

### 3.2 code-agent skill

**文件**：`skills/engineer/code-agent/SKILL.md`

**工作流**：

```
Step 1：spawn repo-explorer → 获取文件地图
Step 2：制定修改计划 → 等用户确认（关键：不自行扩大范围）
Step 3：执行修改 → 每文件改完立即 readback
Step 4：运行测试 → 最多重试 2 次
Step 5：交付报告
```

**换路策略**（借鉴 research-execution-protocol）：

```
第 1 次失败 → 检查是否测试本身的问题
第 2 次失败 → 缩小修改范围，只保留最核心改动
第 3 次失败 → 停止，报告 blocked，附失败日志
```

**与现有 skills 的关系**：

```
code-agent（编排层）
    ├── 探索阶段 → repo-explorer（subagent）
    ├── 排障阶段 → research-execution-protocol（优先级更高）
    └── 诊断阶段 → longclaw-checkup（workspace 运行体检）
```

---

## 四、学习路径：三个阶段

### 阶段一：理解经典 Coding Agent 架构（2 周）

**目标**：搞清楚业界怎么做，建立认知框架。

#### 必读：SWE-agent（Princeton）

**核心贡献**：ACI（Agent-Computer Interface）设计

传统 shell 命令对 LLM 不友好（输出太长、格式不一致）。SWE-agent 设计了专门的工具接口：

```python
# 普通 bash（LLM 不友好）
$ cat large_file.py  # 输出 2000 行，LLM 看不完

# SWE-agent 的 ACI 工具
open("large_file.py")           # 显示前 100 行 + 行号
scroll_down()                   # 翻页，每次 100 行
goto(150)                       # 跳到第 150 行
search_file("def process")      # 在当前文件搜索
```

**对 longClaw 的启发**：
- repo-explorer 的 Bash 工具调用应该模仿这种"LLM 友好"的模式
- 每次读文件不超过 100 行，用 grep 定位后再精确读取
- 输出格式要结构化，不要原始 shell 输出

**必读内容**：
- 论文：[SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- GitHub：https://github.com/SWE-agent/SWE-agent
- 重点看：`tools/` 目录下的工具定义，理解 ACI 设计

**评估基准：SWE-bench**

SWE-bench 是 coding agent 的标准评测集，包含 2294 个真实 GitHub issue（需要修改代码来修复）。

关键指标：
- **Resolved rate**：成功修复的比例（GPT-4 约 2%，Claude Sonnet 约 13%，最好的专用系统约 50%）
- **Pass@1**：一次尝试通过率
- **Avg. turns**：平均需要几轮对话

这个基准对你有两个用途：
1. 理解问题的难度（大多数 issue 需要跨 3-5 个文件的修改）
2. 未来可以用预留优化闭环在小规模版本上评估 longClaw 的 coding agent 效果

#### 必读：Aider（最实用的开源实现）

**核心贡献**：repo-map 技术

Aider 用 tree-sitter 解析代码 AST，提取所有函数/类的签名，生成一个压缩版的"代码地图"：

```
# repo-map 示例（只有签名，没有实现）
src/auth.py:
  class AuthManager:
    def __init__(self, db_url: str)
    def login(self, username: str, password: str) -> Token
    def logout(self, token: Token) -> bool

src/models.py:
  class User:
    id: int
    username: str
    created_at: datetime
```

这个地图只有几百 token，但能让 LLM 快速理解整个 repo 的结构。

**对 longClaw 的启发**：
- repo-explorer 目前用 grep + read 模拟这个功能，效果有限
- 未来可以给 repo-explorer 加一个 `python3 tools/repo_map.py` 工具，用 tree-sitter 生成真正的代码地图
- 这是 repo-explorer 的下一个升级方向

**必读内容**：
- GitHub：https://github.com/Aider-AI/aider
- 重点看：`aider/repomap.py`（repo-map 实现）和 `aider/coders/`（edit format 设计）
- 文档：https://aider.chat/docs/repomap.html

**Edit Format 设计**（重要）：

Aider 有三种 edit format，针对不同场景：

| Format | 适用场景 | Token 消耗 |
|--------|---------|-----------|
| `whole` | 小文件（<200行） | 高（输出整个文件） |
| `diff` | 中等文件 | 中（unified diff 格式） |
| `search/replace` | 精确修改 | 低（只输出修改块） |

longClaw 的 code-agent 目前直接用 OpenClaw 的 Edit 工具，相当于 `search/replace` 模式。这是合理的起点。

#### 必读：Claude Code 自身（你最熟悉的）

你已经深入研究过 harness 架构，重点补充两个设计：

**Plan Mode**：
- 用户说 `/plan` 进入 plan mode
- Claude 只能读文件，不能写文件
- 制定完整计划后，用户确认才能执行
- 这正是 code-agent Step 2 的设计来源

**Worktree 隔离**：
- 每个 coding task 在独立的 git worktree 里执行
- 主分支不受影响
- 任务失败可以直接丢弃 worktree
- longClaw 目前没有这个，是一个重要的升级方向

---

### 阶段二：在 longClaw 里迭代 Coding Agent（3-4 周）

按优先级排序的改造任务：

#### 改造 1：repo-explorer 升级（已完成基础版，可迭代）

**当前版本**：用 grep + read 定位文件

**下一版**：加 repo-map 生成

```python
# tools/repo_map.py（新增工具）
# 用 tree-sitter 解析 AST，生成压缩版代码地图
# 输出：文件名 + 函数/类签名（不含实现）
# 依赖：pip install tree-sitter
```

在 repo-explorer 的 Step 2 里加一步：
```bash
python3 tools/repo_map.py --path . --lang python
```

**改造 2：code-agent 的 git 集成**

当前 code-agent 直接修改文件，没有 git 保护。加上：

```bash
# Step 0（新增）：创建临时分支
git checkout -b code-agent/task-$(date +%Y%m%d-%H%M%S)

# Step 5（修改）：交付时提供 diff
git diff HEAD
# 询问用户：合并到主分支？
```

**改造 3：测试命令自动发现**

code-agent 目前需要用户告诉它测试命令。加上自动发现：

```python
# 检测项目类型 → 推断测试命令
if os.path.exists("pytest.ini") or os.path.exists("pyproject.toml"):
    test_cmd = "pytest"
elif os.path.exists("package.json"):
    test_cmd = "npm test"
elif os.path.exists("go.mod"):
    test_cmd = "go test ./..."
```

**改造 4：Worktree 隔离（中期目标）**

```bash
# 每次 code-agent 任务开始时
git worktree add .worktrees/task-$(date +%s) -b code-agent/task
cd .worktrees/task-xxx

# 任务完成后
git worktree remove .worktrees/task-xxx
```

---

### 阶段三：评估与优化（持续）

#### 用预留优化闭环评估 coding agent 效果

你已经有完整的 Trace → Judge → Dataset 流水线，可以这样用：

```python
# judge_plane.py 加入 coding agent 专用指标
class CodingAgentJudge:
    def score(self, trace):
        return {
            "test_pass_rate": ...,      # 测试通过率（最重要）
            "files_modified": ...,       # 修改文件数（越少越好）
            "turns_to_complete": ...,    # 完成轮数（越少越好）
            "need_human": ...,           # 是否需要人工介入（越低越好）
            "plan_accuracy": ...,        # 计划与实际执行的一致性
        }
```

#### 小规模 SWE-bench 评测

从 SWE-bench-lite（300 个 issue）里选 20-30 个 Python 项目的 issue，用 code-agent 跑，统计 resolved rate。

这不是为了和 GPT-4 比较，而是建立你自己的 baseline，知道改造前后效果的变化。

---

## 五、推荐阅读清单

### 论文（按优先级）

1. **SWE-agent**（必读）
   - [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
   - 重点：ACI 设计原则，工具接口设计

2. **SWE-bench**（必读）
   - [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)
   - 重点：评测方法，难度分析

3. **Agentless**（推荐）
   - [Agentless: Demystifying LLM-based Software Engineering Agents](https://arxiv.org/abs/2407.01489)
   - 重点：不用 agent loop 也能做 coding，简单有时候更好

4. **CodeAct**（推荐）
   - [Executable Code Actions Elicit Better LLM Agents](https://arxiv.org/abs/2402.01030)
   - 重点：用 Python 代码作为 action 空间，比 JSON 工具调用更灵活

5. **RepoGraph**（进阶）
   - [RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph](https://arxiv.org/abs/2410.14684)
   - 重点：图结构的代码理解，是 repo-map 的升级版

### 开源项目（按优先级）

1. **Aider**：https://github.com/Aider-AI/aider
   - 重点读：`repomap.py`，`coders/` 目录

2. **SWE-agent**：https://github.com/SWE-agent/SWE-agent
   - 重点读：`tools/` 目录，`agent/` 目录

3. **OpenHands**（前 OpenDevin）：https://github.com/All-Hands-AI/OpenHands
   - 重点读：sandbox 设计，多 agent 编排

4. **Agentless**：https://github.com/OpenAutoCoder/Agentless
   - 重点读：三阶段流水线（localize → repair → validate）

---

## 六、当前改造文件清单

```
.claude/agents/
└── repo-explorer.md          ← 新增：Codebase 探索子代理（只读）

skills/engineer/
├── code-agent/
│   └── SKILL.md              ← 新增：Coding Agent 完整工作流编排
├── research-execution-protocol/  ← 已有：排障闭环（code-agent 失败时降级）
└── research-build/               ← 已有：简单实现闭环

docs/
└── coding-agent-learning-plan.md  ← 本文件
```

---

## 七、里程碑

| 里程碑     | 目标                             | 验证方式                                            |
| ------- | ------------------------------ | ----------------------------------------------- |
| M1（已完成） | repo-explorer + code-agent 基础版 | 能自主探索 longClaw 自身的 codebase 并修改                 |
| M2（2周）  | repo-map 工具（tree-sitter）       | repo-explorer 能生成 500 token 内的代码地图              |
| M3（4周）  | git worktree 隔离                | code-agent 任务在独立分支执行，失败可安全丢弃                    |
| M4（6周）  | 预留优化闭环评估接入        | 能跑 10 个 SWE-bench-lite issue，有 resolved rate 数据 |
| M5（持续）  | 迭代优化                           | resolved rate 持续提升                              |
