---
name: paperbanana
description: 学术论文配图自动生成——输入方法描述文本和图注，通过 Retriever→Planner→Stylist→Visualizer→Critic 五代理流水线生成发表级配图。需本地安装 PaperBanana（https://github.com/dwzhu-pku/PaperBanana）。
version: 1.0.0
author: jinglong92
license: MIT
requires: ["file_write", "shell_exec"]
upstream: https://github.com/dwzhu-pku/PaperBanana
upstream_license: Apache-2.0
---

# PaperBanana

为学术论文自动生成发表级配图（方法架构图 / 统计图）。

## 触发条件
- 用户说"帮我画论文配图" / "生成方法架构图" / "帮我出一张 figure"
- 用户提供论文方法段落 + 图注（caption），希望生成配图
- 用户说"paperbanana" / "用 PaperBanana 生成"

## 前置检查（执行前必须确认）

### 1. 安装检查
```bash
ls ~/PaperBanana/app.py 2>/dev/null && echo "installed" || echo "not installed"
```
若未安装，提示用户：
```bash
git clone https://github.com/dwzhu-pku/PaperBanana.git ~/PaperBanana
cd ~/PaperBanana && uv venv && source .venv/bin/activate
uv python install 3.12 && uv pip install -r requirements.txt
cp configs/model_config.template.yaml configs/model_config.yaml
# 然后编辑 configs/model_config.yaml，填入 google_api_key 或 openrouter_api_key
```

### 2. API Key 检查
确认 `~/PaperBanana/configs/model_config.yaml` 中至少有一个 API key（`google_api_key` 或 `openrouter_api_key`）。
**不得把 API key 输出到对话中。**

## 执行流程

### Step 1：收集输入
需要用户提供：
- **方法描述文本**（Method section，建议 200-500 字）
- **图注**（Figure caption，1-2 句话说明图的目的）
- **可选**：候选数量（默认 5）、宽高比（默认 16:9）、pipeline 模式（conceptual / statistical）

### Step 2：生成命令
```bash
cd ~/PaperBanana && source .venv/bin/activate
python run_pipeline.py \
  --method_text "<方法描述文本>" \
  --caption "<图注>" \
  --num_candidates 5 \
  --mode conceptual
```
或使用 Streamlit UI（更直观）：
```bash
cd ~/PaperBanana && source .venv/bin/activate && streamlit run streamlit_app.py
```

### Step 3：输出结果
- 生成图片保存在 `~/PaperBanana/outputs/` 目录
- 告知用户输出路径和候选数量
- 若需要高清放大（2K/4K），告知用户使用 Gradio app 的 upscaling 功能

## 五代理流水线说明（供用户理解）

| 代理 | 职责 |
|------|------|
| Retriever | 从参考集中检索风格最相近的示例图 |
| Planner | 将方法文本转化为详细的图形描述 |
| Stylist | 按学术审美标准优化描述（配色、布局、字体风格） |
| Visualizer | 调用图像生成模型（Gemini / OpenRouter）生成图片 |
| Critic | 评审生成结果，反馈给 Visualizer 迭代改进（多轮） |

## 已知限制
- 需要 Google Gemini API key 或 OpenRouter API key（不支持 Codex/OpenAI 直接生成图片）
- 参考集目前主要覆盖 CS 领域，其他领域效果可能较弱
- 统计图生成代码尚未开源（TODO）
- 首次运行需下载 PaperBananaBench 数据集（可选，不下载则跳过 Retriever）

## 输出约定
执行完成后告知：
- 生成的候选图片路径列表
- 使用的 pipeline 模式
- 是否触发了 Critic 迭代（几轮）
- 若失败，给出具体错误原因和修复建议
