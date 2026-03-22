# Privacy and Compatibility Guardrails

## 1) 隐私防护（默认执行）

- 绝不在模板中写入真实姓名、邮箱、手机号、地址、账号 ID、密钥
- 本地状态目录 `.openclaw/` 与 `.env*` 默认被 `.gitignore` 忽略
- 证书/密钥文件（`*.pem`, `*.key`, `*.p12`, `*.pfx`）默认忽略
- 建议将个性化记忆与日志放在 `memory/private/` 或仓库外目录

推送前最小检查：

```bash
git status --short
```

如果出现任何私密文件，先移除再提交。

## 2) 兼容策略（避免本地 OpenClaw 异常）

- 本 Starter Kit 是增量层，不替换现有 `MULTI_AGENTS.md`
- 所有示例配置都遵循 `openclaw_v1` 兼容契约
- 不引入新的运行时依赖，不要求安装第三方包
- 先 `validate` 后接入，失败配置不建议上线

## 3) 建议接入流程（安全顺序）

1. 从 `examples/` 拷贝配置到本地私有路径
2. 用 `tools/validate_config.py` 校验
3. 人工映射到你现有路由规则
4. 先 dry-run 再真实使用
5. 观察 1-2 天后再进行下一轮调优
