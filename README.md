# EyesChat-LensMate — AI 视觉对话助手

> 七牛云面试议题 — 题目一：AI 视觉对话助手

一款支持摄像头和麦克风实时交互的 AI 助手。AI 能"看见"摄像头画面、"听见"用户语音，并给出自然流畅的回复。

## 功能

- 📷 摄像头实时预览，智能帧采样（320×240, 2fps, JPEG 压缩）
- 🎤 端上语音识别（Web Speech API），支持中文
- 💬 流式 AI 对话（OpenAI 兼容接口，支持 GPT-4o / DeepSeek 等）
- 🔊 AI 语音回复（TTS 或浏览器语音合成兜底）
- 🔒 隐私模式（不保存画面和录音）
- 📊 实时成本仪表盘（Token / 费用 / 预算进度条）
- ⚡ 语音打断（用户说话时自动停止 AI 朗读）
- 🔙 多轮上下文记忆

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn（Python） |
| 前端 | 原生 HTML/CSS/JS SPA |
| 通信 | WebSocket 全双工 |
| AI 模型 | GPT-4o Vision / DeepSeek / 兼容 OpenAI API 的任意模型 |
| 语音识别 | Web Speech API（端上免费） |
| 语音合成 | OpenAI TTS / 浏览器 SpeechSynthesis 兜底 |

## 依赖

详见 [requirements.txt](requirements.txt)

核心依赖：
- `fastapi>=0.136`
- `uvicorn>=0.49`
- `openai>=2.41`
- `httpx>=0.28`
- `pydantic-settings>=2.14`

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY 和 OPENAI_BASE_URL

# 3. 启动后端
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# 4. 打开浏览器
# http://127.0.0.1:8001
```

## 项目结构

```
eyeschat-lensmate/
├── backend/
│   ├── .env.example              # 配置模板
│   └── app/
│       ├── main.py               # FastAPI 入口 + 静态文件托管
│       ├── core/
│       │   ├── config.py         # 配置模型（Token 预算、帧策略等）
│       │   ├── session_manager.py # 会话管理 + Token 追踪 + 帧历史
│       │   └── llm_service.py    # GPT-4o Vision + TTS + 费用估算
│       └── routers/
│           └── ws.py             # WebSocket 端点（打断/隐私/TTS）
├── frontend/
│   └── index.html                # 完整前端 SPA
├── docs/
│   ├── EyesChat_LensMate_最终方案.md
│   └── EyesChat_设计方案.md
├── requirements.txt
├── README.md
└── .gitignore
```

## 版权

本项目为原创作品，代码自主编写，仅依赖开源库（已在 requirements.txt 中列明）。
