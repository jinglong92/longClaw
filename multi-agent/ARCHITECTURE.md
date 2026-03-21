# Multi-Agent Architecture (Current)

```mermaid
flowchart TD
    U[User 龙哥]

    subgraph C[Controller Layer]
      CTRL[CTRL\nController / Router / Arbiter]
    end

    subgraph S[Specialist Layer]
      LIFE[LIFE\n生活助理]
      JOB[JOB\n求职助手]
      WORK[WORK\n职场顾问]
      PARENT[PARENT\n育儿顾问]
      LEARN[LEARN\n学习教练]
      MONEY[MONEY\n理财顾问]
      BRO[BRO\n闲聊哥们]
      SIS[SIS\n姐妹视角顾问]
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
    CTRL --> PARENT
    CTRL --> LEARN
    CTRL --> MONEY
    CTRL --> BRO
    CTRL --> SIS

    LIFE --> CTRL
    JOB --> CTRL
    WORK --> CTRL
    PARENT --> CTRL
    LEARN --> CTRL
    MONEY --> CTRL
    BRO --> CTRL
    SIS --> CTRL

    CTRL --> U

    %% Optional cross-specialist controlled collaboration
    JOB -. 触发式协作 .- PARENT
    JOB -. 触发式协作 .- LIFE
    BRO -. 轻松闲聊 .- SIS
```

## Routing Rule
- 默认：`User -> CTRL -> [Single Specialist] -> CTRL -> User`
- 跨域阻塞时：`User -> CTRL -> [Role A + Role B] -> CTRL -> User`（最多2个专职）

## Notes
- 所有最终输出由 CTRL 统一口径。
- 专职角色不越权；跨域协作必须受协议约束。
- 偏好与安全要求由 Preference + Memory 层长期生效。
