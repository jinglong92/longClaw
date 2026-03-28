# OpenClaw 迭代方案 v1（可落地）

- Version: `v1.0`
- Date: `2026-03-28`
- Owner: `CTRL / ENGINEER`
- Status: `Draft for Review`

---

## 1. 目标与约束

### 1.1 优化目标

定义：

- \(Q\)：任务质量（事实正确 + 可执行性 + 完整性）
- \(S\)：稳定性（同输入多次运行的一致性）
- \(R\)：可追溯性（日志字段完备率）
- \(C\)：成本（Token + 外部工具调用）
- \(T\)：时延（P95）

目标函数：

\[
\max J = 0.4Q + 0.2S + 0.2R - 0.1\log C - 0.1T
\]

约束：

\[
R \ge 0.95,\quad T_{p95} \le 20s,\quad C \le C_{budget}
\]

### 1.2 非目标

- 不追求“默认多代理”。
- 不在无追踪（trace）条件下上线新路由。
- 不引入超过 2 个并行专职（保持系统复杂度可控）。

---

## 2. 路由与回环判定（形式化）

### 2.1 路由函数

设请求复杂度估计函数为 \(\kappa(x)\)，阈值为 \(\tau_1, \tau_2\)：

\[
\text{mode}(x)=
\begin{cases}
\text{single}, & \kappa(x)<\tau_1\\
\text{parallel-2}, & \tau_1\le\kappa(x)<\tau_2\\
\text{iterative}, & \kappa(x)\ge\tau_2
\end{cases}
\]

### 2.2 Continue/Exit 判定

第 \(t\) 轮是否继续：

\[
\text{continue}_t = (\Delta Q_t > \epsilon) \land (C_t < C_{max}) \land (t < t_{max})
\]

其中：

- \(\Delta Q_t\)：本轮综合后质量增益估计
- \(\epsilon\)：最小有效增益阈值（建议 `0.03`）
- \(t_{max}\)：最大迭代轮数（建议 `3`）

---

## 3. 方法选择对比（决策表）

| Core Mechanism | Pros | Cons | Inductive Bias |
|---|---|---|---|
| 单专职直出 | 成本低、时延低、实现简单 | 易漏检跨域风险 | 问题单域且信息充分 |
| 双专职并行 + CTRL 仲裁 | 覆盖更广、抗盲区 | 成本上升、冲突仲裁复杂 | 问题跨域但不需多轮 |
| 迭代式 Orchestrator-Worker | 质量上限高、可控回环 | 工程复杂度最高 | 高价值高不确定任务 |

决策原则：默认 `single`，满足复杂度条件后再升级到 `parallel-2` 或 `iterative`。

---

## 4. 目标架构与执行时序

统一时序：

`Route -> Plan -> Delegate -> Evaluate -> Synthesize -> Continue/Exit -> Cite -> Persist`

### 4.1 模块职责

1. `Router v2`
- 输入：请求文本 + 用户偏好 + 历史摘要
- 输出：`mode`、候选专职、原因

2. `Planner`
- 输入：目标、约束、mode
- 输出：任务 DAG（子任务目标/工具白名单/停止条件）

3. `Worker Executor`
- 输入：子任务定义
- 输出：结构化结果（结论、证据、风险）

4. `Evaluator`
- 输入：worker 结果与证据
- 输出：`Q_t`、`risk_score`、`citation_score`

5. `Synthesizer`
- 输入：多 worker 结果
- 输出：单一答案 + 冲突裁决记录

6. `CitationAgent`
- 输入：最终草稿 + 证据集合
- 输出：引用位置与插入后的结果

7. `Memory Writer`
- 输入：会话结果
- 输出：working memory、long-term memory 增量写入

8. `Trace + Replay`
- 输入：全链路事件
- 输出：可回放报告与波动分析

---

## 5. 数据契约（必须先落地）

### 5.1 统一事件 Schema

```json
{
  "trace_id": "uuid",
  "request_id": "uuid",
  "stage": "route|plan|delegate|evaluate|synthesize|gate|cite|persist",
  "agent": "CTRL|SPECIALIST_A|SPECIALIST_B|CITATION",
  "mode": "single|parallel-2|iterative",
  "input_hash": "sha256",
  "decision": "continue|exit|single|parallel-2|iterative",
  "latency_ms": 0,
  "token_in": 0,
  "token_out": 0,
  "tool_calls": 0,
  "cost_usd": 0.0,
  "quality_score": 0.0,
  "risk_score": 0.0,
  "citation_score": 0.0,
  "ts": "2026-03-28T10:00:00+08:00"
}
```

### 5.2 子任务输出 Schema

```json
{
  "task_id": "string",
  "claim": "string",
  "evidence": ["string"],
  "risk": ["string"],
  "confidence": 0.0,
  "next_action": ["string"]
}
```

---

## 6. 参考实现（Python，类型标注）

```python
from dataclasses import dataclass

@dataclass
class GateConfig:
    epsilon: float = 0.03
    c_max: float = 1.0
    t_max: int = 3


def route_mode(complexity: float, tau1: float = 0.35, tau2: float = 0.7) -> str:
    if complexity < tau1:
        return "single"
    if complexity < tau2:
        return "parallel-2"
    return "iterative"


def should_continue(delta_q: float, cost: float, t: int, cfg: GateConfig) -> bool:
    return (delta_q > cfg.epsilon) and (cost < cfg.c_max) and (t < cfg.t_max)
```

---

## 7. 验收标准（DoD）

1. 路由解释性
- 95% 以上请求可输出 `mode + reason`。

2. 可追溯性
- `trace` 字段完备率 \(R \ge 0.95\)。

3. 成本控制
- 升级策略上线后，总成本不高于预算 \(C_{budget}\)。

4. 稳定性
- 固定 30 条黄金样本，每晚回放；关键指标方差下降。

5. 质量提升
- 高复杂任务集合中，质量得分 \(Q\) 相对基线提升 >= 15%。

---

## 8. 实施顺序（按依赖，不按周）

1. `P0`：事件 Schema + Trace 落地（无此项不进入下一步）
2. `P1`：Router v2 + Planner + Continue/Exit Gate
3. `P2`：Evaluator + CitationAgent + Memory 分层写入
4. `P3`：Replay Harness + A/B 灰度 + 成本闸门

---

## 9. 风险审计（Risk Audit）

1. 逻辑漏洞
- 如果先上并行不先上评估器，系统只会更贵，不会更稳。

2. 确认偏误
- 看到少量成功样本就默认“多代理总更优”。

3. 自我合理化
- 把架构复杂化当作能力提升，而忽略可回放与可证伪。

4. 尾部风险
- 无引用约束时，高置信错误会在最终答案中固化。

---

## 10. Review 决策清单（需要你拍板）

1. 是否接受三档路由：`single / parallel-2 / iterative`
2. 是否接受默认参数：`epsilon=0.03, t_max=3`
3. `C_budget` 预算上限（USD/请求）
4. 高风险任务是否强制 `CitationAgent`
5. 是否执行“无 Trace 不上线”硬门槛
