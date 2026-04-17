# inbox/ — 个人知识摄入入口

把任何想入库的内容放到这个目录，heartbeat-agent 会定时处理并建立索引。

## 支持的格式

| 格式 | 处理方式 |
|------|---------|
| `.md` / `.txt` | 直接解析，分块入库 |
| `.url` | 一行 URL，自动抓取正文（需 web_fetch）|
| （计划）`.pdf` | 需要 pdfplumber |

## 使用方式

1. 把文件拖入 `inbox/`
2. 文件名建议加日期前缀：`2026-04-17-文章标题.md`
3. 可选：在文件顶部加 frontmatter 指定域和标签：
   ```yaml
   ---
   domain: LEARN
   tags: [Agent, RL, 论文]
   importance: high
   ---
   ```
4. heartbeat-agent 每天 08:30/18:00 自动处理
5. 也可手动触发：`python3 tools/inbox_processor.py`

## 处理结果

- 内容写入 `tools/artifacts/knowledge_entries.jsonl`
- 原文件移动到 `inbox/processed/`
- 可通过 `memory_search.py` 检索（自动合并 memory 和 knowledge 两个索引）

## 示例文件

```
inbox/
├── 2026-04-17-agentic-rl-notes.md    ← 笔记
├── 2026-04-17-paper-link.url         ← 链接（计划）
└── processed/                         ← 已处理
    └── 2026-04-10-old-article.md
```
