#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT_DIR/.skill_pack_backup_$TS"

log() {
  printf '[skill-pack] %s\n' "$*"
}

require_path() {
  local p="$1"
  if [[ ! -e "$p" ]]; then
    log "missing required path: $p"
    exit 1
  fi
}

write_file() {
  local path="$1"
  mkdir -p "$(dirname "$path")"
  if [[ -f "$path" ]]; then
    mkdir -p "$BACKUP_DIR"
    cp "$path" "$BACKUP_DIR/$(basename "$path").bak"
    log "backed up existing file: $path"
  fi
  cat > "$path"
  log "wrote: $path"
}

append_if_missing() {
  local path="$1"
  local marker="$2"
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$path" ]] && grep -Fq "$marker" "$path"; then
    log "skip append, marker exists in: $path"
    rm -f "$tmp"
    return 0
  fi
  cat > "$tmp"
  if [[ -f "$path" ]]; then
    cat "$tmp" >> "$path"
  else
    mkdir -p "$(dirname "$path")"
    cat "$tmp" > "$path"
  fi
  rm -f "$tmp"
  log "appended marker section to: $path"
}

log "root: $ROOT_DIR"
require_path "$ROOT_DIR/AGENTS.md"
require_path "$ROOT_DIR/MULTI_AGENTS.md"
require_path "$ROOT_DIR/skills"

write_file "$ROOT_DIR/skills/meta/skill-safety-audit/SKILL.md" <<'SKILL'
---
name: skill-safety-audit
description: 审计外部 SKILL.md / agent 仓库 / 自动化脚本的接入风险。用于判断某个 skill 是否应原样引入、拆解学习或禁止接入 longClaw。
version: 1.0.0
author: jinglong92
license: MIT
---

# Skill Safety Audit

审计外部 skill、agent 仓库、安装脚本、hook 方案的安全性、侵入性和治理兼容性。

## 触发条件
- 用户说“这个 skill 适合装到 longClaw 吗”
- 用户给出 GitHub 仓库 / SKILL.md / shell script 让你评估
- 用户说“帮我做接入前安全审查”
- 用户准备引入新的自动化、memory、hook、daemon、遥测或日志上报机制

## 核心目标
1. 判断该能力是否值得学习
2. 判断该实现是否适合直接接入
3. 找出所有高风险点与副作用
4. 给出 longClaw 兼容改造建议

## 审计维度

### 1) 权限与副作用
检查是否存在：
- 写入 home 目录隐藏状态
- 修改 shell rc / login 配置
- 后台常驻进程 / daemon
- hook 注入（SessionStart / Stop / PostToolUse / PreCompact 等）
- 自动联网下载、自动执行远程脚本
- 覆盖或修改 workspace 根规则文件

### 2) Prompt / Persona 污染
检查是否存在：
- 强制改变全局人格与语气
- 使用羞辱、施压、PUA、操控式措辞
- 重复覆盖 AGENTS.md / MULTI_AGENTS.md 已定义的边界
- 将局部 skill 升格为全局控制层

### 3) 数据与隐私风险
检查是否存在：
- 会话日志上传
- prompt / repo / 用户数据外发
- 未明确说明的数据收集
- 默认开启遥测 / benchmark 上报

### 4) 架构兼容性
检查是否存在：
- 与 CTRL 仲裁冲突
- 与“默认单专职、按需双专职并行”冲突
- 与按需加载 skill 原则冲突
- 与 memory 分域注入协议冲突
- 与本地优先、可回滚、低侵入原则冲突

## 审计步骤
1. 识别对象类型：SKILL.md / 仓库 / shell script / hook 配置 / memory 机制
2. 抽取“它到底在增强什么”：执行协议 / 记忆 / 人格 / 路由 / 可观测性 / 自动化
3. 列出显式副作用
4. 列出隐式副作用
5. 判断是否和 longClaw 的三条约束冲突：
   - CTRL 统一仲裁
   - skill 按需加载，不长期污染上下文
   - AGENTS.md 安全边界优先
6. 输出接入建议：
   - 可直接引入
   - 可拆解学习
   - 禁止接入

## 输出格式
```text
审计结论：<可直接引入 / 可拆解学习 / 禁止接入>

对象类型：<repo / skill / script / hook>
目标能力：<它想增强什么>

主要风险：
- [P0] ...
- [P1] ...
- [P2] ...

兼容性判断：
- CTRL 仲裁：兼容 / 冲突
- Skill 按需加载：兼容 / 冲突
- Memory 分域注入：兼容 / 冲突
- 本地优先：兼容 / 冲突

建议落地方式：
1. 保留 ...
2. 删除 ...
3. 改写为 longClaw 本地 skill：...

[置信度: X.XX]
[依据: repo/skill/script 审计]
```

## 边界
- 不自动执行外部安装脚本
- 不因为“看起来有用”就默认建议接入
- 不修改 `AGENTS.md` / `MULTI_AGENTS.md` / `SOUL.md` / `USER.md`
- 若存在高风险副作用，优先建议“拆解学习”而非“直接安装"
SKILL

write_file "$ROOT_DIR/skills/engineer/research-execution-protocol/SKILL.md" <<'SKILL'
---
name: research-execution-protocol
description: 研究型工程执行协议。用于复杂实现、排障、代码修改、配置修复与实验验证。强调先证据后判断、先验证后宣称完成、失败后系统性换路，不改变全局人格。
version: 1.0.0
author: jinglong92
license: MIT
---

# Research Execution Protocol

用于高不确定性、易反复失败、需要多轮验证的工程任务。

## 触发条件
满足任一条件时启用：
- 用户要求修 bug、改代码、补功能、排查配置、修环境
- 任务涉及多文件修改、外部依赖、工具调用或实验验证
- 第一次方案失败，且仍存在可继续验证的路径
- 用户明确表达：继续查、继续修、别停在分析、给我闭环

## 核心原则

### 1. 证据先于判断
先收集最小必要证据，再下结论。
不要在没有日志、代码位置、配置状态、返回结果的情况下断言根因。

### 2. 验证先于完成
除非已有可见证据，否则不要说“已经修好”“完成了”。
只有在满足至少一项时，才可宣称完成：
- 测试通过
- 命令成功执行
- 输出结果与目标一致
- 用户提供的失败路径被复现后已消失

### 3. 失败后不重复原思路
一次失败后，必须显式切换策略之一：
- 换根因假设
- 换检查位置
- 换工具路径
- 缩小问题规模
- 先做最小可复现
- 先绕过再回补

### 4. 局部改动优先
优先做最小、可验证、可回滚的改动。
避免在根因未明时大面积重构。

### 5. 显式区分事实与推断
输出中区分：
- [FACT] 已观察到的事实
- [HYP] 当前假设
- [TEST] 为验证假设采取的动作
- [RESULT] 动作结果
- [NEXT] 下一步

### 6. 不把压力转嫁给用户
能自己做的检查先自己做。
只有在缺失关键输入、权限不足、或所有合理备用路径都失败后，才向用户索取额外信息。

## 标准流程
1. 定义目标与完成标准
2. 建立最小问题模型：失败层、复现性、最低成本证据、最快排除路径
3. 先做低成本高信息量检查：代码 / 配置 / 文档 / 错误 / 最小复现
4. 维护 1-3 个主假设，每个假设绑定验证动作与证伪条件
5. 改动后立即验证：单测 / 命令 / smoke test / 样例回放
6. 失败时升级策略：缩小范围 / 换假设 / 换观测 / 换路径 / 临时绕过
7. 以“已验证完成 / 已部分完成 / 未完成但阻塞明确”之一结束

## 输出协议
复杂任务默认按以下结构输出：
```text
结论：<已验证完成 / 已部分完成 / 未完成>
目标：<本轮目标>
已确认事实：
- [FACT] ...
当前假设：
- [HYP] ...
已执行验证：
- [TEST] ...
- [RESULT] ...
改动：
- ...
风险与边界：
- ...
下一步：
1. ...
完成判定：
- <哪项证据表明任务真的完成>
```

短任务可压缩为：
```text
结论：
事实：
验证：
改动：
下一步：
```

## 边界
- 不使用羞辱、施压、PUA、人格操控式措辞
- 不把“继续尝试”伪装成“已经解决”
- 不在证据不足时编造成功状态
- 不未经说明进行大面积重构
- 不静默修改 `AGENTS.md` / `SOUL.md` / `USER.md` / `MULTI_AGENTS.md`

## 一句话心法
更少臆测，更快验证，更小改动，更清楚地结束。
SKILL

write_file "$ROOT_DIR/skills/engineer/research-build/SKILL.md" <<'SKILL'
---
name: research-build
description: 面向实现闭环的工程 workflow。用于把“需求/思路/方案”转成可交付改动，强调验收标准、最小改动、立即验证、明确回滚点。
version: 1.0.0
author: jinglong92
license: MIT
---

# Research Build

把“分析”推进到“实现闭环”的工程 skill。

## 触发条件
- 用户说“直接帮我实现”
- 用户说“不要只分析，给我落地”
- 用户提供明确目标、代码位置或设计方向，希望生成改动计划或直接修改
- 任务需要从需求走到 patch / script / config / docs / test

## 目标
在不污染全局规则的前提下，生成一条可执行的交付路径：
- 明确目标
- 明确验收标准
- 选择最小改动面
- 逐步实现
- 改动后立即验证
- 说明风险与回滚点

## 执行流程

### 1) 定义交付对象
先判断本轮交付属于哪类：
- 代码实现
- 配置修复
- skill 新增/改写
- 文档补充
- 测试补齐
- 脚本自动化

### 2) 写清验收标准
在动手前明确：
- 什么行为会发生变化
- 什么命令 / 测试 / 例子可证明完成
- 哪些路径本轮不覆盖

### 3) 设计最小改动方案
优先级：
1. 局部 patch
2. 增量文件
3. 小范围重构
4. 大改（只有在前 3 项不可行时才进入）

### 4) 执行改动
对每类改动都给出：
- 修改文件
- 修改原因
- 与现有规则的兼容性
- 潜在副作用

### 5) 立即验证
至少执行一项：
- 单元测试
- lint / 静态检查
- 样例输入回放
- 命令执行
- 人工 smoke test

### 6) 生成交付说明
输出中必须包含：
- 改了什么
- 为什么这样改
- 如何验证
- 风险在哪
- 如何回滚

## 输出格式
```text
交付结论：<已完成 / 部分完成 / 未完成>

目标：
- ...

验收标准：
- ...

改动方案：
1. 文件：...
   原因：...
   风险：...

验证：
- 执行：...
- 结果：...

回滚点：
- ...

后续建议：
1. ...

[置信度: X.XX]
[依据: 代码/配置/验证结果]
```

## 边界
- 不跳过验收标准直接宣称完成
- 不默认修改全局人格与安全边界文件
- 不用“大重构”掩盖定位不清
- 若需求显著扩大，先按最小闭环交付，再给下一阶段建议
SKILL

write_file "$ROOT_DIR/docs/skills-roadmap-v1.md" <<'DOC'
# longClaw Skills Roadmap v1

本轮新增：
- `skills/meta/skill-safety-audit/SKILL.md`
- `skills/engineer/research-execution-protocol/SKILL.md`
- `skills/engineer/research-build/SKILL.md`

## 设计原则
- 不改 `AGENTS.md` / `MULTI_AGENTS.md` / `SOUL.md` / `USER.md`
- 只做局部增强，不引入后台常驻与高侵入 hook
- 保持 CTRL 仲裁、按需加载 skill、本地优先

## 建议下一步
1. 新增 `skills/meta/skill-audit`
2. 新增 `skills/meta/post-session-review`
3. 新增 `skills/engineer/runtime-watch`
4. 视需要补 `skills/meta/high-stakes-council`
DOC

append_if_missing "$ROOT_DIR/README.md" "## Skills Roadmap v1 (local extension)" <<'README'

## Skills Roadmap v1 (local extension)

本地新增三类增强 skill：

- `skill-safety-audit`：评估外部 skill / 仓库 / 安装脚本的接入风险
- `research-execution-protocol`：复杂工程任务的证据驱动执行协议
- `research-build`：从需求到实现闭环的最小交付 workflow

原则：
- 不替代 CTRL
- 不改变全局人格
- 不常驻污染上下文
- 优先局部增强、可验证、可回滚
README

write_file "$ROOT_DIR/tools/check_skill_pack.sh" <<'CHECK'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${1:-$(pwd)}"

check_file() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    printf '[check] missing: %s\n' "$f"
    exit 1
  fi
  printf '[check] ok: %s\n' "$f"
}

check_file "$ROOT_DIR/skills/meta/skill-safety-audit/SKILL.md"
check_file "$ROOT_DIR/skills/engineer/research-execution-protocol/SKILL.md"
check_file "$ROOT_DIR/skills/engineer/research-build/SKILL.md"
check_file "$ROOT_DIR/docs/skills-roadmap-v1.md"

printf '\n[check] preview names:\n'
grep -R "^name:" "$ROOT_DIR/skills/meta/skill-safety-audit/SKILL.md" "$ROOT_DIR/skills/engineer/research-execution-protocol/SKILL.md" "$ROOT_DIR/skills/engineer/research-build/SKILL.md"
CHECK
chmod +x "$ROOT_DIR/tools/check_skill_pack.sh"

chmod +x "$ROOT_DIR/tools/check_skill_pack.sh" || true

cat <<'NEXT'

Done.

Recommended next commands:
  bash tools/check_skill_pack.sh
  git status
  git diff -- skills docs README.md

If everything looks good:
  git add skills docs README.md tools/check_skill_pack.sh
  git commit -m "feat(skills): add safety audit and research engineering workflows"
NEXT
