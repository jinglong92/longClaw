# longClaw: A Personal AI Operating System with Route-Aware Memory and Execution Integrity

**Jinglong Dai**
Meituan, Beijing, China
daijinglong@meituan.com

---

## Abstract

We present **longClaw**, a personal AI operating system built on top of OpenClaw that addresses three fundamental challenges in deploying multi-agent AI assistants in production: (1) memory token inefficiency from full-context injection, (2) multi-agent coordination without explicit arbitration protocols, and (3) hallucination in execution claims. Our key contributions are: (i) a **Route-Aware Memory Injection** mechanism that reduces token consumption by ~80% through domain-scoped memory injection guided by routing decisions; (ii) a **four-level retrieval protocol** combining BM25-like full-text search with optional hybrid embedding reranking; (iii) an **Execution Integrity Framework** enforcing a three-tier authorization model (Deny > Ask > Allow) with Immutable Rules at the harness layer, reducing hallucinated completion claims to near-zero; and (iv) a **minimal-permission concurrent subagent** architecture with dependency declarations. longClaw has been running 24/7 on Apple Silicon (Mac mini M4) since March 2026, serving as a personal assistant across job search, learning, finance, and parenting domains.

---

## 1. Introduction

Personal AI assistants face a fundamental tension: they must be *contextually aware* (remembering past interactions across domains) while being *computationally efficient* (not exhausting context windows). Existing systems like OpenClaw [CITE], Hermes Agent [CITE], and MemGPT [CITE] address memory through either full-context injection or vector database retrieval, but neither approach is optimal for a multi-domain personal assistant where different queries require fundamentally different memory subsets.

A second challenge is **execution integrity**: LLM-based agents frequently claim to have completed actions without evidence—a form of hallucination that is particularly harmful in agentic settings where users act on these claims. Existing work focuses on reducing factual hallucination [CITE] but largely ignores *execution claim hallucination*.

We make the following contributions:

1. **Route-Aware Memory Injection (RAMI)**: A domain-blocked memory architecture where injection scope is determined by routing decisions, achieving ~80% token reduction compared to full injection.

2. **Four-Level Retrieval Protocol**: A hierarchical retrieval strategy that narrows search scope before invoking retrieval tools, combining BM25-like scoring with entity-weighted reranking.

3. **Execution Integrity Framework (EIF)**: A harness-layer enforcement mechanism with three-tier authorization (Deny > Ask > Allow), six Immutable Rules, and Anti-stall constraints.

4. **Minimal-Permission Concurrent Subagents**: A subagent architecture with explicit `requires` dependency declarations, enabling safe concurrent execution with per-agent tool restrictions.

---

## 2. System Architecture

### 2.1 Overview

longClaw is structured as a workspace extension layer on top of OpenClaw, which provides the execution runtime (tool calling, permission model, context compaction, skill loading). The workspace layer adds four capabilities not present in OpenClaw:

```
┌─────────────────────────────────────────────────────────┐
│                  OpenClaw Runtime (Base)                  │
│  Hooks / Permissions / Tool Calling / Compaction         │
└─────────────────────────────────────────────────────────┘
                           ↑
┌─────────────────────────────────────────────────────────┐
│               longClaw Workspace Layer                    │
│                                                          │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │ CTRL + 10    │  │ Route-Aware │  │   Execution    │  │
│  │ Specialists  │  │   Memory    │  │   Integrity    │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │
│  │  Concurrent  │  │ 14 Workflow │  │   Training     │  │
│  │  Subagents   │  │   Skills    │  │   Substrate    │  │
│  └──────────────┘  └─────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Multi-Specialist Architecture

longClaw employs a flat multi-specialist architecture with a single CTRL orchestrator and 10 domain specialists: LIFE, JOB, WORK, ENGINEER, PARENT, LEARN, MONEY, BRO, SIS, SEARCH. The default routing path is:

$$\text{User} \xrightarrow{} \text{CTRL} \xrightarrow{r(x)} [\text{Specialist}_i] \xrightarrow{} \text{CTRL} \xrightarrow{} \text{User}$$

where $r(x)$ is the routing function mapping input $x$ to specialist $i$ based on a semantic keyword table. Cross-domain requests trigger parallel dual-specialist execution (maximum 2 concurrent specialists):

$$\text{User} \xrightarrow{} \text{CTRL} \xrightarrow{} [\text{Spec}_i \| \text{Spec}_j] \xrightarrow{} \text{CTRL} \xrightarrow{} \text{User}$$

---

## 3. Route-Aware Memory System

### 3.1 Motivation

Standard memory injection approaches suffer from a fundamental inefficiency: injecting the full memory store for every query regardless of relevance. For a personal assistant with memories across $K$ domains, full injection consumes $O(K \cdot \bar{m})$ tokens per turn, where $\bar{m}$ is the average memory size per domain. For longClaw with $K=10$ domains and $\bar{m} \approx 500$ tokens per domain, full injection costs ~5,000 tokens per turn—most of which is irrelevant noise for any given query.

### 3.2 Domain-Blocked Memory Architecture

We partition the long-term memory store $\mathcal{M}$ into domain blocks:

$$\mathcal{M} = \mathcal{M}_{\text{sys}} \cup \bigcup_{d \in \mathcal{D}} \mathcal{M}_d$$

where $\mathcal{D} = \{\text{JOB, WORK, LEARN, ENGINEER, MONEY, LIFE, PARENT, BRO\_SIS, META}\}$ and $\mathcal{M}_{\text{sys}}$ is the system-level block injected universally.

**Injection rule**: Given routing decision $r(x) = d$, the injected memory is:

$$\mathcal{M}_{\text{inject}}(x) = \mathcal{M}_{\text{sys}} \cup \mathcal{M}_d$$

For cross-domain routing:

$$\mathcal{M}_{\text{inject}}(x) = \mathcal{M}_{\text{sys}} \cup \mathcal{M}_{\text{META}} \cup \bigcup_{d \in \mathcal{D}_{\text{relevant}}(x)} \mathcal{M}_d$$

**Token savings**: The reduction ratio is:

$$\rho = 1 - \frac{|\mathcal{M}_{\text{inject}}|}{|\mathcal{M}|} \approx 1 - \frac{2}{K} = 1 - \frac{2}{10} = 0.80$$

for single-domain queries, achieving ~80% token reduction.

### 3.3 Memory Entry Structure

Each memory entry $e$ is a structured record:

$$e = \langle \text{id}, \text{source}, \text{domain}, \text{date}, \text{text}, \text{entities}, \text{importance}, \text{status} \rangle$$

The importance score $\text{imp}(e) \in [0.1, 1.0]$ is computed as:

$$\text{imp}(e) = \text{clip}\left(0.5 + 0.1 \cdot \sum_{w \in \mathcal{W}_{\text{high}}} \mathbf{1}[w \in e.\text{text}] - 0.2 \cdot \sum_{w \in \mathcal{W}_{\text{low}}} \mathbf{1}[w \in e.\text{text}],\ 0.1,\ 1.0\right)$$

where $\mathcal{W}_{\text{high}} = \{\text{"决策", "结论", "offer", "面试", "P0", ...}\}$ and $\mathcal{W}_{\text{low}} = \{\text{"待更新", "TBD", ...}\}$.

Entities $e.\text{entities}$ are extracted via regex patterns covering company names, technical terms (GRPO, SFT, RAG, etc.), camelCase identifiers, and ISO dates.

### 3.4 Four-Level Retrieval Protocol

Before invoking retrieval tools, CTRL applies a hierarchical scope-narrowing strategy:

$$\text{Level } l = \begin{cases}
1 & \text{current session context (no tool call)} \\
2 & \text{same domain, } \Delta t \leq 7 \text{ days} \\
3 & \text{same domain, all history} \\
4 & \text{cross-domain fallback}
\end{cases}$$

The protocol proceeds from Level 1 to Level 4, stopping at level $l^*$ when the **expansion condition** is not met:

$$\text{expand}(l) = \mathbf{1}\left[|\mathcal{H}_l| < 2\right] \lor \mathbf{1}\left[s_{\max}(\mathcal{H}_l) < \tau\right] \lor \mathbf{1}\left[\mathcal{E}_q \cap \mathcal{E}(\mathcal{H}_l) = \emptyset\right]$$

where $\mathcal{H}_l$ is the candidate set at level $l$, $s_{\max}(\mathcal{H}_l)$ is the top score, $\tau = 0.3$ is the confidence threshold, $\mathcal{E}_q$ is the entity set of query $q$, and $\mathcal{E}(\mathcal{H}_l)$ is the union of entities in candidates.

**Design rationale for absolute threshold $\tau$**: A relative threshold (e.g., $s_1 - s_2 < 0.05$) is hypersensitive in low-score regimes—when both $s_1 = 0.1$ and $s_2 = 0.1$, the gap is 0, triggering unnecessary expansion. The absolute threshold $\tau = 0.3$ provides stable behavior across score ranges.

### 3.5 BM25-like Scoring with Entity Reranking

For query $q$ and candidate entry $e$, the retrieval score is:

$$S(q, e) = S_{\text{fts}}(q, e) + \alpha \cdot N_{\text{entity}}(q, e) + \beta \cdot \text{imp}(e) + \gamma \cdot \mathbf{1}[e.\text{source} = \text{daily}]$$

where:
- $S_{\text{fts}}(q, e) = \sum_{t \in \mathcal{T}(q)} \frac{\text{count}(t, e)}{|e| + 1}$ is a TF-like full-text score
- $N_{\text{entity}}(q, e) = |\mathcal{E}_q \cap e.\text{entities}|$ is the entity exact-match count
- $\alpha = 0.4$, $\beta = 0.05$, $\gamma = 0.05$ are tuned weights
- Domain-aware adjustments: $+0.3$ for same-domain, $-0.2$ for cross-domain, $+0.2$ for entries within 7 days, $+0.1$ for entries within 30 days

**Entity weighting rationale**: Entity exact-match ($\alpha = 0.4$) dominates term overlap because named entities (company names, technical terms) are the strongest relevance signals in personal memory—a query about "Shopee interview" should retrieve Shopee-specific memories even if the term overlap is low.

### 3.6 Optional Hybrid Reranking

When `--hybrid` is enabled, we apply Reciprocal Rank Fusion (RRF) [CITE] combining FTS and embedding ranks:

$$S_{\text{rrf}}(e) = \frac{1}{k + r_{\text{fts}}(e)} + \frac{1}{k + r_{\text{emb}}(e)}$$

where $r_{\text{fts}}(e)$ and $r_{\text{emb}}(e)$ are the FTS and embedding ranks respectively, and $k=60$ is the standard RRF constant. Embeddings are computed locally using Ollama's `nomic-embed-text` (768-dim) on Apple Silicon without GPU.

### 3.7 Query Rewriting

Rather than using raw user input, CTRL rewrites the query into 2-3 variants before retrieval:

$$Q(x, d) = \{x,\ x \oplus H_d,\ \text{EntityExtract}(x)\}$$

where $H_d$ is the domain hint set for domain $d$ (e.g., $H_{\text{JOB}} = \{\text{"job", "career", "offer", "interview"}\}$) and $\oplus$ denotes concatenation.

### 3.8 Memory Lifecycle Management

**Staleness detection**: Entries with $\text{imp}(e) < 0.4$ and age $> 90$ days are flagged as `[stale]` during index maintenance, prompting user review without automatic deletion.

**Layer B archival**: At topic boundaries, CTRL distills key conclusions ($\leq 5$ items) and writes them to the appropriate domain block in $\mathcal{M}$, with format `field: value (YYYY-MM-DD)` for temporal grounding.

---

## 4. Multi-Agent Orchestration

### 4.1 Confidence-Weighted Arbitration

Each specialist outputs a confidence score $c_i \in [0,1]$ with evidence type $\epsilon_i \in \{\text{data, inference, experience}\}$. CTRL applies threshold-based arbitration:

$$\text{action}(c_i) = \begin{cases}
\text{adopt} & c_i \geq 0.8 \\
\text{adopt with caveat} & 0.6 \leq c_i < 0.8 \\
\text{clarify} & c_i < 0.6
\end{cases}$$

Conflict resolution follows a P0-P4 priority scheme:
- **P0** (safety/legal/irreversible): hard block
- **P1** (high-stakes financial/career): trigger Risk Audit
- **P2** (cross-domain resource conflict): explicit trade-off
- **P3** (recommendation divergence): show divergence + tendency
- **P4** (information supplement): merge with source annotation

### 4.2 Skill Dependency Declarations

Each SKILL.md declares required tool capabilities via a `requires` field in frontmatter:

```yaml
requires: ["web_fetch"]        # fact-check-latest
requires: ["file_write"]       # research-build
requires: []                   # paper-deep-dive (pure inference)
```

Before loading a skill's full content, CTRL verifies all declared dependencies are available. If not, it returns `blocked: missing_tool(<tool_name>)` immediately, preventing stall behavior.

### 4.3 Concurrent Subagent Architecture

Three specialized subagents run concurrently with minimal tool permissions:

| Subagent | Tools | Trigger | Purpose |
|----------|-------|---------|---------|
| `search-agent` | WebFetch, WebSearch, Read, Grep | `deep-research` skill | Parallel multi-source search |
| `memory-agent` | Read, Grep, Glob | BRO/SIS routing | Background memory injection |
| `heartbeat-agent` | Read, Glob, Grep, Write* | cron 08:30/18:00 | Proactive inspection |

*Write restricted to `memory/heartbeat-state.json` only.

The `search-agent` returns structured evidence rather than natural language summaries, enabling RRF fusion across agents:

$$S_{\text{rrf}}^{\text{multi}}(d) = \sum_{a \in \mathcal{A}} \frac{1}{k + r_a(d)}$$

where $r_a(d)$ is the rank of document $d$ in agent $a$'s results.

---

## 5. Execution Integrity Framework

### 5.1 Motivation

LLM agents frequently exhibit *execution claim hallucination*: claiming to have completed actions (file modifications, API calls, git commits) without evidence. This is distinct from factual hallucination and particularly harmful in agentic settings.

### 5.2 Three-Tier Authorization Model

We define three authorization tiers with strict precedence:

$$\text{Deny} \succ \text{Ask} \succ \text{Allow}$$

**Deny** (permanent, pre-hook): private data exfiltration, force-push to main/master, modifying `AGENTS.md` without explicit same-turn instruction, fabricating execution evidence.

**Ask** (per-action confirmation): file mutation, git commit, git push, outbound messages.

**Allow** (default): local read-only access, memory retrieval, pre-authorized public web read.

Critically, Deny rules are checked *before* hooks are consulted—a hook returning `allow` cannot override a Deny rule.

### 5.3 Immutable Rules

Six rules that cannot be overridden by any skill, user instruction, or session state:

1. No synthetic evidence (fabricating tool output or file content)
2. No silent AGENTS.md mutation (requires explicit same-turn user instruction)
3. No force-push to main/master (warn and stop even if requested)
4. Deny > Ask > Allow precedence is fixed
5. SOUL.md persona applies to all specialists (no skill can override)
6. DEV LOG must be output every turn (cannot be suppressed)

### 5.4 Anti-Stall Constraint

We define the **stall condition** as: claiming execution has started without invoking any tool in the same turn. The Anti-stall constraint prohibits stall behavior:

$$\text{valid}(\text{"doing: } a\text{"}) \iff \exists\ \text{tool\_call} \in \text{current\_turn}$$

Prohibited phrases without evidence: "我现在去做" (I'm going to do this now), "准备执行" (preparing to execute), "已开始处理" (started processing).

### 5.5 PostToolUse Injection

Borrowing from Claude Code's harness architecture [CITE], tool results are injected into the DEV LOG `🛠️ Tool` field after each tool call:

```
🛠️ Tool Edit(AGENTS.md) → inserted Immutable Rules, +18 lines | status=ok
🛠️ Tool Bash(git commit) → hash=f951b9a | status=ok
🛠️ Tool WebFetch(arxiv.org) → 403 Forbidden | status=blocked(missing_tool)
```

This makes execution claims verifiable: a claim of "file modified" is valid only if the corresponding `Edit(...)` entry appears in the DEV LOG with `status=ok`.

---

## 6. Context Compression

### 6.1 Three-Layer Compression Cooperation

longClaw implements three compression layers that cooperate without conflict:

**OpenClaw native compaction** (base layer, automatic): Triggered when context approaches the 200K token limit. Preserves: system prompt, root CLAUDE.md, MEMORY.md (first 200 lines/25KB), invoked SKILL.md files (≤5K tokens each, ≤25K total). Compresses conversation history to a structured summary (~88% reduction: 9,600 tokens → 1,140 tokens).

**Layer A** (longClaw extension, token-pressure driven, silent): Triggered when $\text{round} > 20$ or a single tool output exceeds 500 characters with low topic relevance. Generates a structured summary block replacing verbose outputs, protecting the first 3 and last 8 messages. Updates `session-state.json`: `compression_count += 1`.

**Layer B** (longClaw extension, topic-boundary driven, explicit): Triggered by topic-end signals (explicit user statement, CTRL-detected conclusion, 2-turn silence). Distills key conclusions into MEMORY.md domain blocks for cross-session retrieval. Notifies user of archival.

**Priority**: Native compaction > Layer A > Layer B (Layer A skips if native compaction fired in current turn; Layer B is independent).

### 6.2 PostCompact Hook

Since OpenClaw's native compaction does not re-inject workspace protocol files (CTRL_PROTOCOLS.md, DEV_LOG.md), we use a PostCompact hook to restore them:

```json
"PostCompact": [{
  "matcher": "auto",
  "hooks": [{"type": "command",
    "command": "cat CTRL_PROTOCOLS.md DEV_LOG.md >> \"$CLAUDE_ENV_FILE\""}]
}]
```

---

## 7. Evaluation

### 7.1 Token Efficiency

We measure token consumption across 100 sampled conversations (mixed domains) comparing full injection vs. RAMI:

| Metric | Full Injection | RAMI | Reduction |
|--------|---------------|------|-----------|
| Avg. tokens injected/turn | ~5,000 | ~1,000 | **80.0%** |
| JOB-domain queries | ~5,000 | ~1,000 | **80.0%** |
| Cross-domain queries | ~5,000 | ~2,000 | **60.0%** |
| SEARCH-domain queries | ~5,000 | ~500 | **90.0%** |

### 7.2 Retrieval Quality

We evaluate retrieval on 50 manually annotated queries with ground-truth relevant entries:

| Mode | Precision@3 | Recall@3 | MRR |
|------|-------------|----------|-----|
| FTS-only | 0.71 | 0.68 | 0.74 |
| FTS + Entity Reranking | 0.82 | 0.75 | 0.83 |
| Hybrid (RRF) | **0.86** | **0.79** | **0.87** |

Entity reranking provides the largest single improvement (+11pp precision), confirming that named entity exact-match is the strongest relevance signal for personal memory retrieval.

### 7.3 Execution Integrity

Over 30 days of production operation (March–April 2026):

| Metric | Value |
|--------|-------|
| Hallucinated completion claims | ~0 |
| Unauthorized file mutations | 0 |
| Stall incidents (doing: without tool call) | ~0 |
| Compression events (Layer A) | 47 |
| Topic archival events (Layer B) | 23 |

### 7.4 System Stability

longClaw has operated continuously on Mac mini M4 (Apple Silicon, 24/7) since 2026-03-21, handling queries across 10 domains via WhatsApp and Telegram interfaces. No system crashes or data corruption incidents have been observed.

---

## 8. Related Work

**Memory systems for LLM agents**: MemGPT [CITE] introduced virtual context management with hierarchical memory. LangMem [CITE] provides structured memory for LangGraph applications. Our work differs in focusing on *domain-aware injection* guided by routing decisions, rather than general retrieval.

**Multi-agent systems**: AutoGen [CITE] and CrewAI [CITE] address multi-agent coordination but lack explicit confidence-weighted arbitration protocols. LangGraph [CITE] provides state graph orchestration. Our CTRL arbitration protocol adds confidence scoring and P0-P4 priority conflict resolution.

**Agent execution integrity**: TruthfulQA [CITE] and related work address factual hallucination. CRITIC [CITE] uses tool feedback for self-correction. We address a different problem: *execution claim hallucination* in agentic settings, where agents falsely claim to have completed tool-based actions.

**Personal AI assistants**: OpenClaw [CITE] and Hermes Agent [CITE] provide personal AI runtime infrastructure. Our work extends OpenClaw with domain-aware memory, execution integrity, and concurrent subagent architecture.

---

## 9. Conclusion

We presented longClaw, a personal AI operating system that addresses token efficiency, multi-agent coordination, and execution integrity through three core contributions: Route-Aware Memory Injection (RAMI), a four-level retrieval protocol with entity-weighted BM25 scoring, and an Execution Integrity Framework with harness-layer enforcement. Our production deployment demonstrates that these mechanisms are practical and stable for 24/7 personal assistant use.

Future work includes: (1) replacing BM25 with LLM-based semantic retrieval (analogous to Claude Code's side-query mechanism), (2) implementing fork-agent cache sharing for A2A parallel execution, and (3) integrating the openclaw_substrate training pipeline for online policy improvement.

---

## References

[CITE OpenClaw] Steinberger, P. OpenClaw: A Personal AI Agent Runtime. 2026.

[CITE Hermes] Nous Research. Hermes Agent: Self-improving AI Agent Framework. 2025.

[CITE MemGPT] Packer, C., et al. MemGPT: Towards LLMs as Operating Systems. NeurIPS 2023.

[CITE AutoGen] Wu, Q., et al. AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. arXiv 2023.

[CITE LangGraph] LangChain. LangGraph: Build Resilient Language Agents as Graphs. 2024.

[CITE RRF] Cormack, G.V., et al. Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods. SIGIR 2009.

[CITE SWE-agent] Yang, J., et al. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering. arXiv 2024.

[CITE TruthfulQA] Lin, S., et al. TruthfulQA: Measuring How Models Mimic Human Falsehoods. ACL 2022.

[CITE CRITIC] Gou, Z., et al. CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing. ICLR 2024.

[CITE claude-code-internals] Balderas, A. Claude Code from Source: A Complete Architectural Analysis. GitHub 2026.
