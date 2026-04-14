---
name: paper-deep-dive
description: 论文深度解读——Fact/Inference 分离、方法论、SOTA 对比、Reviewer#2 批判、工业落地评估、面试压缩版。
version: 1.0.0
author: jinglong92
license: MIT
---

# Paper Deep Dive

当用户发送论文标题/链接/摘要/方法/实验片段时，自动应用完整深度解读协议。
无需用户二次提醒。

## 触发条件
- 用户发送论文标题 / arXiv 链接 / 摘要 / 方法段落 / 实验结果片段
- 用户发送技术博客文章 / preprint / 技术报告链接，并希望深度解读
- 用户说"解读这篇论文" / "帮我看看这个方法" / "这篇 paper 怎么样"
- 用户说"看看这篇文章" / "分析一下这个" / "这个方法有什么问题"（上下文为技术内容时）
- 用户说"帮我准备面试问题" / "这篇怎么讲" / "能 review 一下吗"（上下文为论文/技术文章时）

## 输出结构（8 个模块，按需展开）

### 1. Essence（精华提炼）
- 一句话：这篇论文解决了什么问题，用了什么方法，效果如何
- Fact vs Inference 标注（F: 论文明确陈述 / I: 解读推断）

### 2. Methodology（方法论）
- 核心公式（LaTeX）
- ASCII 流程图
- Python 伪代码（向量化，有类型标注）

### 3. SOTA Comparison（对比表）
| 方法 | 核心机制 | 优势 | 局限 | 适用场景 |
|------|---------|------|------|---------|

### 4. Reviewer #2 批判
- 最可能被拒的 2-3 个理由
- 实验设计的潜在漏洞
- 泛化性质疑

### 5. Deployment Assessment（工业落地）
- 落地难度评级（Easy/Medium/Hard/Research-only）
- 主要工程障碍
- 与换电/调度场景的关联性

### 6. Insights（洞察）
- 对当前工作的启发
- 值得跟进的 follow-up 方向

### 7. Decision Card（要不要读完整篇）
- 推荐指数（1-5星）
- 建议阅读深度（摘要/方法/全文/代码）

### 8. Interview Compression（面试压缩版）
- 30 秒能说清楚的版本
- 面试官最可能追问的 2 个问题 + 标准答案

## 参考文件
`PAPER_DEEP_DIVE_PROMPT.md`（如存在，优先使用最新版本）
