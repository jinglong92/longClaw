# Multi-Agent Starter Kit (v0.1)

目标：让已经安装 OpenClaw 的用户，在 **10 分钟内**完成多代理配置并跑通一次可解释路由。

本 Starter Kit 仅新增文档、模板、校验工具和本地 CLI shim，**不改动现有运行时逻辑**，默认不会影响你当前本地 OpenClaw 行为。

## 你会得到什么

- `schema/`：`multi-agent.schema.v0.1.json`
- `examples/`：3 套可直接改的配置模板
- `tools/validate_config.py`：零依赖配置体检器
- `bin/openclaw`：可执行的 `openclaw ma validate` 本地命令入口
- `CLI_SPEC_v0.1.md`：CLI 规范（`validate` 已落地）
- `VALIDATION_RULES_v0.1.md`：校验规则与错误码建议

## 10 分钟上手（兼容模式）

1. 拷贝一个模板到你自己的配置目录（建议在仓库外或私有目录）
2. 修改关键词和启用角色
3. 运行校验
4. 通过后再映射到你当前 `MULTI_AGENTS.md` 规则

示例命令：

```bash
python3 multi-agent/starter-kit/tools/validate_config.py \
  --config multi-agent/starter-kit/examples/general-assistant.json --strict
```

或使用命令形态（和规划一致）：

```bash
./multi-agent/starter-kit/bin/openclaw ma validate \
  --config multi-agent/starter-kit/examples/general-assistant.json --strict
```

## 为什么是 JSON 而不是 YAML

- v0.1 优先“零依赖可运行”，避免给开源用户增加安装门槛
- 后续可以平滑加 YAML 支持，但 v0.1 先保证可校验、可复制、可回滚

## 兼容承诺（避免把本地系统弄崩）

- 不修改 `MULTI_AGENTS.md` 的现有契约
- 角色标签保持 `LIFE/JOB/WORK/PARENT/LEARN/MONEY/BRO/SIS`
- 并行上限固定 `<=2`
- 输出路由格式保持：`User -> CTRL -> [ROLE] -> CTRL -> User`

## 隐私承诺（防止误提交）

- 根目录新增 `.gitignore`，默认忽略 `.openclaw/`, `.env*`, 证书密钥文件
- 建议将含个人信息的运行日志放在 `memory/private/` 或仓库外目录
- 推送前执行：`git status --short`，只提交显式白名单文件
