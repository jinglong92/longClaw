# CLI Spec v0.1

说明：本规范中 `openclaw ma validate` 已在 starter-kit 中提供本地可执行版本：

`./multi-agent/starter-kit/bin/openclaw ma validate --config <file> [--strict]`

其余命令仍为规划项。

## 实现状态

- `validate`: implemented (starter-kit local shim)
- `init`: planned
- `run`: planned
- `migrate`: planned

## 命令目标

- 降低配置门槛（init）
- 提前发现配置问题（validate）
- 快速跑通首个路由请求（run）
- 提供向后兼容迁移（migrate）

## Command 1: `openclaw ma init`

用途：从模板生成可编辑配置。

```bash
openclaw ma init --profile general-assistant --out ./multi-agent.config.json
```

参数：

- `--profile`：`general-assistant | coding-copilot | research-analyst`
- `--out`：输出路径（默认 `./multi-agent.config.json`）
- `--compat`：兼容模式，默认 `openclaw_v1`

预期输出：

- 生成配置文件
- 输出下一步校验命令

## Command 2: `openclaw ma validate`

用途：做静态体检，不执行真实请求。

```bash
openclaw ma validate --config ./multi-agent.config.json
```

参数：

- `--config`：待校验配置路径
- `--strict`：开启严格模式（禁止未知字段）

预期输出：

- `VALID` 或 `INVALID`
- 失败时给出错误码、定位路径、修复建议

## Command 3: `openclaw ma run`

用途：用该配置执行一次请求（dry-run 或 real-run）。

```bash
openclaw ma run --config ./multi-agent.config.json --input "明天面试和接娃冲突怎么办"
```

参数：

- `--config`：配置路径
- `--input`：请求文本
- `--dry-run`：仅展示路由，不执行业务动作

预期输出：

- 角色路由链
- 是否并行
- CTRL 汇总输出

## Command 4: `openclaw ma migrate`

用途：处理版本升级与配置迁移。

```bash
openclaw ma migrate --from 0.1 --to 0.2 --config ./multi-agent.config.json
```

参数：

- `--from`：源版本
- `--to`：目标版本
- `--config`：配置路径
- `--write`：是否写回（默认只预览）

预期输出：

- 变更摘要（新增字段、废弃字段、默认值补齐）
- 迁移后校验结果
