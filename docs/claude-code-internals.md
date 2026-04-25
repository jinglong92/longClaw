# Claude Code 内部架构解析

> 来源：claude-code-from-source（alejandrobalderas，基于 npm sourcemap 逆向，v2.1.88）
> 性质：教育目的的伪代码分析，非 Anthropic 官方内容
> 参考链接：
> - 架构书（18章）：https://github.com/alejandrobalderas/claude-code-from-source
> - 源码还原：https://github.com/ChinaSiro/claude-code-sourcemap
> - 可运行版本：https://github.com/oboard/claude-code-rev

---

## 一、10 个核心设计模式

这是整个架构的骨架，理解这 10 个模式就理解了 Claude Code 的本质：

| 模式 | 一句话描述 |
|------|-----------|
| AsyncGenerator Loop | 用生成器函数驱动 agent loop，天然背压 + 类型化终止原因 |
| Speculative Execution | 模型流式输出期间提前执行工具，节省 16%+ 壁钟时间 |
| Concurrent-Safe Batching | 按安全性分批并发，同一工具不同参数可能不同分类 |
| Fork Agents | 子 agent 继承父 agent 的完整 context，实现 90% 缓存折扣 |
| 4-Layer Compression | 四层渐进式压缩，从轻到重按需触发 |
| LLM-Based Memory Recall | 用 Sonnet 侧查询做记忆检索，而不是关键词匹配或向量数据库 |
| Two-Phase Skill Loading | 启动时只加载 frontmatter，命中时才加载全文 |
| Sticky Latches | 关键状态（如 prompt cache key）一旦设定不再变化 |
| Slot Reservation | 默认 8K 输出 token，需要时升级到 64K |
| Hook Config Snapshots | 启动时冻结 hook 配置，防止运行时注入攻击 |

---

## 二、Agent Loop（核心）

### 架构

整个 agent 系统核心是 `query.ts` 里的一个**单一 async generator 函数**，而不是分散的回调。

**为什么用 generator**：
1. 天然背压：生成器的 yield 机制自动处理流量控制
2. 类型化返回：终止原因是明确的 discriminated union，不是模糊的 error
3. 可组合委托：`yield*` 可以把控制权委托给子生成器

```typescript
// 伪代码：agent loop 的骨架
async function* query(state: AgentState): AsyncGenerator<AgentMessage, TerminalReason> {
  while (true) {
    // 1. 压缩 context（4层）
    state = await compressContext(state);

    // 2. 调用 API（流式）
    const stream = await callAPI(state);

    // 3. 并发执行工具（Speculative Execution）
    const executor = new StreamingToolExecutor();
    for await (const chunk of stream) {
      if (chunk.type === 'tool_call') {
        executor.submit(chunk);  // 立即开始执行，不等流结束
      }
      yield chunk;
    }

    // 4. 收集工具结果
    const results = await executor.drain();

    // 5. 判断终止或继续
    const decision = evaluateTermination(state, results);
    if (decision.terminal) return decision.reason;
    state = transition(state, results, decision);
  }
}
```

### 四层压缩（4-Layer Context Compression）

每次 API 调用前，messages 经过四层渐进式压缩，**从轻到重，前一层不够才用下一层**：

```
Layer 1：Tool Result Budgeting
  → 每条工具结果设置 token 上限，超出的截断
  → 最轻量，保留所有消息结构

Layer 2：Snip Compacting
  → 物理删除旧消息（保留首尾）
  → 比 Layer 1 更激进

Layer 3：Microcompacting
  → 删除不必要的工具结果（已完成的工具调用）
  → 保留对话流但去掉中间产物

Layer 4：Auto-compacting（spawn 子 agent 做摘要）
  → 完整对话摘要，spawn 一个专用 summarizer agent
  → 最重，但保留语义完整性
```

**对 longClaw 的启发**：
- longClaw 的 Layer A（轻量摘要）对应 Layer 2-3
- longClaw 的 Layer B（话题归档）对应 Layer 4 的语义
- 缺少 Layer 1（工具结果 token 预算）——这是下一个可以加的

### 错误恢复阶梯

```
Context collapse drainage
    ↓ 失败
Reactive compaction on demand
    ↓ 失败
Output token escalation（8K → 64K）
    ↓ 失败
Multi-turn recovery（最多 3 次）
    ↓ 失败
Terminal: max_recovery_attempts
```

**电路断路器**：
- 单次 reactive compact 标记（不触发第二次）
- 失败计数器
- 显式检查防止恢复触发恢复（无限循环保护）

---

## 三、并发工具执行

### Partition Algorithm（最重要的设计）

**核心洞察：安全性是 per-call 的，不是 per-tool-type 的。**

同一个 Bash 工具，`cat file.txt` 是安全的，`rm file.txt` 是不安全的。所以必须解析参数才能判断。

```typescript
function partitionToolCalls(calls: ToolCall[]): Batch[] {
  const batches: Batch[] = [];
  let currentBatch: ToolCall[] = [];

  for (const call of calls) {
    const tool = lookupTool(call.name);
    const parsed = tool.schema.parse(call.input);  // 解析失败 → 串行
    const safe = tool.isConcurrencySafe(parsed);   // 判断安全性

    if (safe) {
      currentBatch.push(call);  // 累积到当前并发批次
    } else {
      if (currentBatch.length > 0) batches.push({ type: 'concurrent', calls: currentBatch });
      batches.push({ type: 'serial', calls: [call] });
      currentBatch = [];
    }
  }
  if (currentBatch.length > 0) batches.push({ type: 'concurrent', calls: currentBatch });
  return batches;
}

// 示例变换：
// 输入：  [Read, Read, Grep, Edit, Read]
// 输出：  [Batch(并发): [Read, Read, Grep], Batch(串行): [Edit], Batch(并发): [Read]]
```

**各工具的安全性分类**：

| 工具 | 安全性 | 条件 |
|------|--------|------|
| Read, Grep, Glob, WebFetch | 始终安全 | 纯读操作 |
| Bash | 条件安全 | 所有子命令都是只读时 |
| Edit, Write | 始终不安全 | 文件修改 |

### Speculative Execution（投机执行）

不等模型流式输出完成，一旦有工具调用就立即开始执行：

```
时间轴：
0ms    → 模型开始流式输出
500ms  → 第一个工具调用解析完成 → 立即开始执行 Tool 1
1200ms → 第二个工具调用解析完成 → 立即开始执行 Tool 2
2500ms → 流式输出完成
2600ms → Tool 1 执行完成（已经执行了 2100ms）
2700ms → Tool 2 执行完成
→ 节省约 16%+ 壁钟时间
```

**结果顺序保证**：结果按提交顺序返回，不按完成顺序。Tool C 先完成也要等 Tool A 完成后才输出。

---

## 四、Multi-Agent 架构

### 统一 runAgent() 生命周期（15 步）

所有 agent 类型（Explore/Plan/Verification/General/Guide）都用同一个 `runAgent()` 函数，通过参数化区分：

```
Step 1：Model Resolution
  → Caller override > agent definition > parent model > default

Step 2：Agent ID Creation
  → 唯一标识符，用于生命周期追踪

Step 3：Context Preparation
  → Fork agent：克隆父 agent 的完整历史
  → Fresh agent：从空白开始

Step 4：CLAUDE.md Stripping
  → 只读 agent 省略项目配置，节省 token

Step 5：Permission Isolation
  → 自定义 getAppState() 包装器，叠加安全边界

Step 6：Tool Resolution
  → 按 agent 类型和权限过滤工具池

Step 7：System Prompt
  → Fork agent 复用父 agent 的精确 prompt（缓存效率）
  → Fresh agent 重新生成

Step 8：Abort Controller
  → Sync agent 共享父 agent 的控制器
  → Async agent 获得独立控制器

Step 9：Hook Registration
  → 加载 agent 作用域的 plugin

Step 10：Skill Preloading
  → 任务专用 skill 作为 user messages 注入

Step 11：MCP Initialization
  → 服务器初始化 + 清理追踪

Step 12：Context Creation
  → 独立的 ToolUseContext，选择性共享状态

Step 13：Cache-Safe Params
  → 支持后台摘要的回调

Step 14：Query Loop
  → 标准对话迭代

Step 15：Cleanup
  → 跨所有子系统的资源释放
```

### 内置 Agent 类型

| Agent            | 模型    | 工具          | 特点                                                      |
| ---------------- | ----- | ----------- | ------------------------------------------------------- |
| **Explore**      | Haiku | 只读          | 每周 3400 万次调用，激进 tokenization（每周节省 46 亿字符）               |
| **Plan**         | 继承    | 只读          | 四步结构化架构指导                                               |
| **Verification** | 继承    | 完整          | 始终 async，反规避提示（"recognize excuses and do the opposite"） |
| **General**      | 继承    | 完整（除 Agent） | 默认委托目标                                                  |
| **Guide**        | Haiku | 文档获取        | Claude Code 生态感知                                        |

### Fork Agent 的缓存经济学

**核心洞察**：当父 agent spawn 多个子 agent 时，每个子 agent 的 API 请求有 99.75% 是相同的（system prompt + tools + 对话历史）。

```
典型场景：
  共享 token：80,000（system prompt + 历史）
  每个子 agent 独特 token：200（具体指令）

  不优化：5 个子 agent = 5 × 80,200 token = 401,000 token
  Fork 优化：1 × 80,200 + 4 × 200（缓存命中 90% 折扣）≈ 80,200 + 80 = ~$0.50 vs ~$4.00
  节省：约 87.5%
```

**实现字节级相同前缀的三个机制**：
1. **System Prompt Threading**：复用父 agent 已渲染的 prompt，不重新生成
2. **Exact Tool Passthrough**：传递父 agent 的完整工具数组，不重排序或过滤
3. **Structured Message Construction**：占位符结果在所有子 agent 中完全相同

**对 longClaw 的启发**：
- longClaw 的 A2A 并行（JOB ∥ PARENT）如果用 fork agent 模式，可以大幅降低 token 成本
- 当前实现没有利用缓存共享，每个专职代理都独立生成 context

---

## 五、记忆系统

### 设计哲学

**文件而不是数据库**，Markdown 格式，人类可读可编辑。

核心原则：**"简单存储 + 智能检索 > 复杂存储 + 复杂检索"**

### 四类记忆分类

只有四种类型，用一个标准过滤：**这个信息能从当前项目状态推导出来吗？**

| 类型 | 内容 | 示例 |
|------|------|------|
| **User** | 角色、专业水平、目标 | "用户是 Go 专家，刚接触 React" |
| **Feedback** | 纠正和验证（含 Why + How） | "不要 mock 数据库，原因：上季度 mock/prod 分歧导致线上故障" |
| **Project** | 活跃工作上下文（绝对日期） | "合并冻结从 2026-03-05 开始，移动团队发布" |
| **Reference** | 外部系统书签 | "bug 在 Linear 项目 INGEST 追踪" |

**明确排除**：代码模式、git 历史、调试方案、已在代码库里的内容。

### 检索机制（两层）

```
Layer 1（始终加载）：
  MEMORY.md index（前 200 行或 25KB）
  → 提供定向，让模型知道有哪些记忆文件

Layer 2（按需加载）：
  LLM 侧查询（用 Sonnet）
  → 分析相关性，每轮最多选 5 个记忆文件
  → 与主模型并行运行（异步，不增加延迟）
```

**为什么用 LLM 做检索而不是关键词/向量**：
- 关键词：词面不重叠就找不到
- 向量：需要额外基础设施
- LLM 侧查询：理解语义，且 Sonnet 的成本在整体 token 消耗里很小

### 老化管理

不删除旧记忆，而是**附加人类可读的时间警告**：

```markdown
用户偏好：直接回答，不要废话（47天前）← 自动附加
```

把记忆当作"假设"而不是"事实"，提示验证而不是盲目信任。

### KAIROS 持续模式

长期 session 的日志系统：
- append-only 的每日日志，记录时间戳观察
- 后台整合进程定期把日志合并为结构化记忆
- 更新 index 同时保持 200 行上限

**对 longClaw 的启发**：
- longClaw 的 memory_entry.py + MEMORY.md 是这个架构的简化版
- 缺少 LLM 侧查询（目前用 FTS + BM25）——这是下一个升级方向
- KAIROS 日志 = longClaw 的 memory/YYYY-MM-DD.md

---

## 六、五个架构赌注

Anthropic 在设计 Claude Code 时做的五个非显而易见的选择：

### 赌注 1：Generator Loop 而不是 Callbacks

> "开发者拥有循环"

把 1700 行控制流集中在一个函数里，而不是分散在回调中。
代价：单文件很长。收益：可读性和可调试性远超分散架构。

### 赌注 2：文件记忆而不是数据库

> "透明度优于能力"

用户可以直接打开 `~/.claude/projects/myapp/memory/MEMORY.md` 看到 agent 记住了什么。
代价：检索能力受限。收益：用户信任（可观察 = 可信任）。

### 赌注 3：自描述工具而不是中央编排器

每个工具携带自己的名称、描述、schema 和执行逻辑。
收益：MCP 外部工具和内置工具对模型完全无差别。

### 赌注 4：Fork Agent 做缓存共享

子 agent 继承父 agent 的完整 context，实现 90% token 折扣。
代价：子 agent 继承了可能不相关的历史。收益：并发委托在经济上可行。

### 赌注 5：Hooks 而不是 Plugins

外部进程通过 exit code 和 JSON 通信，而不是在进程内运行插件。
收益：进程隔离，hook 崩溃不会影响主进程，内存泄漏不会累积。

---

## 七、对 longClaw 的直接改造价值

### 立即可借鉴（改 workspace 配置）

| Claude Code 设计 | longClaw 现状 | 改造方向 |
|-----------------|--------------|---------|
| Hook Config Snapshot（启动时冻结） | settings.json 运行时可修改 | 加 PreToolUse hook 检查配置完整性 |
| Tool Result Budgeting（Layer 1 压缩） | 无 | 在 Layer A 里加工具输出 token 上限 |
| Verification Agent（反规避提示） | 无 | 新建 `.claude/agents/verifier.md`，加"recognize excuses" prompt |

### 中期可借鉴（需要代码）

| Claude Code 设计 | 改造方向 |
|-----------------|---------|
| LLM 侧查询做记忆检索 | 用 Codex 替代 memory_search.py 的 FTS，做语义检索 |
| Fork Agent 缓存共享 | A2A 并行时让子 agent 继承父 context，降低 token 成本 |
| Partition Algorithm | code-agent 里加并发工具执行，Read/Grep 并发，Edit 串行 |

### 长期参考（架构级）

| Claude Code 设计 | 参考价值 |
|-----------------|---------|
| AsyncGenerator Loop | 预留优化闭环的 trace 收集可以用 generator 重写 |
| 4-Layer Compression | longClaw Layer A/B 是其子集，可以补 Layer 1 和 Layer 3 |
| Discriminated Union 终止原因 | code-agent 的失败处理可以用类似的类型化终止原因 |

---

## 八、推荐阅读顺序

1. **ch05-agent-loop.md**：理解 generator loop 和 4 层压缩（最重要）
2. **ch07-concurrency.md**：理解 partition algorithm 和 speculative execution
3. **ch08-sub-agents.md**：理解 15 步生命周期和 agent 类型
4. **ch09-fork-agents.md**：理解缓存共享的经济学
5. **ch11-memory.md**：理解文件记忆 + LLM 检索
6. **ch18-epilogue.md**：5 个架构赌注，最后读，有整体视角

完整书地址：https://github.com/alejandrobalderas/claude-code-from-source/tree/main/book
