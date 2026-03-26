# 多代理系统配置（新手模板）

## 1) 角色集合
- LIFE：生活
- WORK：职场
- LEARN：学习
- ENGINEER：工程

## 2) 路由规则
- 默认：`User -> CTRL -> [单专职] -> CTRL -> User`
- 并行：`User -> CTRL -> ([专职A] || [专职B]) -> CTRL -> User`
- 并行上限：2

## 3) 输出可见性
每条回复必须包含 Routing 行：
- 单专职：`Routing: User -> CTRL -> [ROLE] -> CTRL -> User`
- 并行：`Routing: User -> CTRL -> ([ROLE_A] || [ROLE_B]) -> CTRL -> User`

## 4) 仲裁规则（CTRL）
1. 冲突时优先低风险、可执行方案
2. 信息不足时最多追问 1-3 个关键问题
3. 不可逆风险必须显式警示

## 5) 新手默认
- 先单专职，必要时并行
- 只由 CTRL 对外输出
- 每周做一次路由漂移检查
