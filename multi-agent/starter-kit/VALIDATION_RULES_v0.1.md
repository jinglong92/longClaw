# Validation Rules v0.1

本规则用于 `validate_config.py` 与后续 CLI 的一致校验。

## A. 硬约束（失败即拒绝）

1. `version` 必须是 `0.1`
2. `compatibility_mode` 必须是 `openclaw_v1`
3. `controller.id` 必须是 `CTRL`
4. `controller.max_parallel_specialists` 必须在 `[1,2]`
5. `routing.parallel_limit` 必须在 `[1,2]` 且不能大于 `controller.max_parallel_specialists`
6. 角色 ID 只能是：`LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS`
7. 每个 trigger 的 `route` 长度必须在 `[1,2]`
8. trigger 引用的角色必须是启用状态
9. `output_visibility.show_routing` 必须是 `true`
10. `output_visibility.routing_format` 必须是 `User -> CTRL -> [ROLE] -> CTRL -> User`

## B. 建议约束（警告但可运行）

1. trigger 关键词建议 >= 2 个，避免误触发
2. 每个配置建议保留至少 1 个并行 trigger（用于跨域场景）
3. `risk_audit.required_fields` 建议包含 `core_gap` 与 `tail_risk`

## C. 错误码建议

- `MA001`: missing required field
- `MA002`: unsupported version or compatibility mode
- `MA003`: invalid controller settings
- `MA004`: invalid specialist role or duplicates
- `MA005`: invalid routing trigger
- `MA006`: route points to disabled role
- `MA007`: routing visibility contract broken
- `MA008`: unknown field in strict mode

## D. 兼容性保障

v0.1 的全部规则都围绕当前 OpenClaw 契约设计：

- 固定 CTRL 汇总
- 固定角色集合
- 固定并行上限
- 固定路由可见性

因此新增配置层不会直接破坏既有系统行为。
