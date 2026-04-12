---
name: public-evidence-fetch
description: 对公开网页/论文执行只读检索与证据摘录，返回 exact query、URL、逐字片段、段落位置与简短解释。
version: 2.0.0
author: jinglong92
license: MIT
---

# Public Evidence Fetch

## Trigger

当用户要求以下任一类型任务时触发：
- 外网搜一下并给我原文片段
- 谷歌搜这篇论文，然后截取对应段落
- 给我链接 + 逐字摘录 + 段落位置
- 不要总结，给证据
- 抓取公开网页证据
- 论文原文摘录
- 给我 exact query + URL + snippet + position

## Scope

仅适用于：
- 公共网页
- 公开论文页（如 arXiv / OpenReview / 官方文档 / GitHub README / 公共博客）
- 无需登录即可访问的页面

不适用于：
- 私有文档
- 登录后内容
- 需要写操作的任务

## Authorization

如果当前 session 已有：
- `read_only_web_authorized = true`
- 且 `authorized_scopes` 包含 `public_web_read_only_evidence_fetch`

则不得重复请求授权。

## Workflow

### Step 1: Query Rewrite
至少生成 2-3 个 query 变体：
1. 原始 query
2. 带 domain/source hint 的 query
3. 带目标概念/术语的 query

### Step 2: Capability Gate
先判断当前 runtime 是否真有 public-web fetch 能力。
若没有，直接：
`blocked: no_public_web_fetch_tool`
并只给一个 fallback。

### Step 3: Search
优先顺序：
1. 官方源 / 论文源（arXiv / OpenReview / 官方文档）
2. 搜索引擎结果
3. 公共镜像源

### Step 4: Page Open
打开候选页并定位用户指定目标概念。

### Step 5: Evidence Extraction
只提取用户指定目标相关的逐字片段，不用总结代替证据。

### Step 6: Return Format
必须返回：
- exact query
- source URL
- verbatim snippet
- paragraph/section marker
- one-sentence mapping

## Failure Contract

如果拿不到：
- exact query
- source URL
- verbatim snippet
- paragraph/section marker

则不得声称完成。
只能返回：
- `blocked: no_verifiable_evidence`
或
- `need_input: direct_url_or_pdf`

## Forbidden

不得：
- 在已授权会话内重复 ask authorization
- 没有原文片段时只给总结
- 没有 URL 时声称抓取成功
- 在失败后反复在 `need_authorization` 与 `blocked` 间切换
