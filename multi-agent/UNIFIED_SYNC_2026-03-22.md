# Multi-Agent Unified Sync (2026-03-22)

目的：执行一次全体专职代理统一交流（对齐边界、口径、路由与记忆写入规范），并将结论回写全局配置。

## 参与代理
- CTRL（总控）
- LIFE
- JOB
- WORK
- PARENT
- LEARN
- MONEY
- BRO
- SIS

## 统一结论（全体签署）

1. **路由可见性强制启用**
   - 每条回复必须展示 Routing。
   - 格式：`Routing: User -> CTRL -> [ROLE] -> CTRL -> User`
   - 并行格式：`Routing: User -> CTRL -> ([ROLE_A] || [ROLE_B]) -> CTRL -> User`

2. **角色标签固定**
   - 仅允许：`LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS`
   - 禁止用泛标签（如 PLAN）。

3. **多代理默认开启（轻量）**
   - 至少经过 `CTRL + 1 专职`。
   - 跨域问题允许双专职并行，默认不超过 2 个。

4. **输出口径统一**
   - 专职提供视角，CTRL 负责最终对外汇总。
   - 禁止专职越权修改路由规则或安全边界。

5. **配置优先级**
   - 安全与行为边界：`AGENTS.md` 最高。
   - 路由与角色分工：`MULTI_AGENTS.md`。
   - 长期偏好与连续性：`MEMORY.md`。

6. **记忆写入规则**
   - 用户明确要求“记住”的多代理偏好，必须落盘到 `MEMORY.md`。
   - 结构性变更必须落盘到 `MULTI_AGENTS.md` 与（必要时）`AGENTS.md`。

## 当前执行状态
- [x] 统一交流完成
- [x] 配置规则更新完成
- [x] 全局记忆更新完成
- [x] 已提交版本控制
