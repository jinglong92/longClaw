# Multi-Agent Architecture (Current)

> 权威配置见 `MULTI_AGENTS.md`。本文件为可视化架构图，与 MULTI_AGENTS.md 保持同步。

```mermaid
flowchart TD
    U[User 龙哥]

    subgraph C[Controller Layer]
      CTRL[CTRL\nController / Router / Arbiter]
    end

    subgraph S[Specialist Layer - 10 专职]
      LIFE[LIFE\n生活助理]
      JOB[JOB\n求职助手]
      WORK[WORK\n职场顾问]
      ENGINEER[ENGINEER\n工程顾问]
      PARENT[PARENT\n育儿顾问]
      LEARN[LEARN\n学习教练]
      MONEY[MONEY\n理财顾问]
      BRO[BRO\n闲聊哥们]
      SIS[SIS\n姐妹视角顾问]
      SEARCH[SEARCH\n信息检索助手]
    end

    subgraph G[Governance Layer]
      POLICY[Policy Engine\n默认单代理 / 并行<=2 / 冲突裁决P0-P4]
      PROTO[Protocol\n固定输出4段 / 受控交流<=2轮]
      PREF[Preference Manager\n坦诚顾问 / 称呼龙哥 / 安全偏好]
      MEM[Memory\nMEMORY.md + memory/YYYY-MM-DD.md]
    end

    U --> CTRL
    CTRL --> POLICY
    CTRL --> PROTO
    CTRL --> PREF
    CTRL --> MEM

    CTRL --> LIFE
    CTRL --> JOB
    CTRL --> WORK
    CTRL --> ENGINEER
    CTRL --> PARENT
    CTRL --> LEARN
    CTRL --> MONEY
    CTRL --> BRO
    CTRL --> SIS
    CTRL --> SEARCH

    LIFE --> CTRL
    JOB --> CTRL
    WORK --> CTRL
    ENGINEER --> CTRL
    PARENT --> CTRL
    LEARN --> CTRL
    MONEY --> CTRL
    BRO --> CTRL
    SIS --> CTRL
    SEARCH --> CTRL

    CTRL --> U

    %% A2A 触发式协作（受控，最多2轮）
    JOB -. A2A .- PARENT
    JOB -. A2A .- MONEY
    ENGINEER -. A2A .- LEARN
    SEARCH -. A2A .- JOB
```

## Routing Rule
- 默认：`User -> CTRL -> [Single Specialist] -> CTRL -> User`
- 跨域时：`User -> CTRL -> ([Role A] || [Role B]) -> CTRL -> User`（最多2个专职并行）

## Notes
- 所有最终输出由 CTRL 统一口径。
- 专职角色不越权；A2A 协作最多2轮，必须受协议约束。
- 偏好与安全要求由 Preference + Memory 层长期生效。
- 合法路由标签：`LIFE/JOB/WORK/ENGINEER/PARENT/LEARN/MONEY/BRO/SIS/SEARCH`
