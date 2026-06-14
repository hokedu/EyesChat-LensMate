# EyesChat-LensMate — AI 视觉对话助手

> 七牛云面试议题 — 题目一：AI 视觉对话助手

一款支持摄像头和麦克风实时交互的 AI 助手。AI 能"看见"摄像头画面、"听见"用户语音，并给出自然流畅的回复。

## 功能

- 📷 摄像头实时预览，智能帧采样（320×240, 2fps, JPEG 压缩，可配置分辨率）
- 🎤 端上语音识别（Web Speech API），支持中文
- 💬 流式 AI 对话（OpenAI 兼容接口，支持 GPT-4o / DeepSeek 等）
- 🔊 AI 语音回复（TTS 或浏览器语音合成兜底）
- 🔒 隐私模式（不保存画面和录音）
- 📊 实时成本仪表盘（Token / 费用 / 预算进度条）
- ⚡ 语音打断（用户说话时自动停止 AI 朗读）
- 🔙 多轮上下文记忆

## Demo 视频

> [📺 观看演示视频](TODO)（待上传，完成后替换此链接）

## 用户故事

### 计划实现 vs 最终实现

| 编号 | 用户故事 | 优先级 | 状态 |
|------|---------|--------|------|
| US-01 | 打开摄像头，让 AI 看到我面前的画面 | P0 | ✅ 已实现 |
| US-02 | 用语音与 AI 对话，无需打字 | P0 | ✅ 已实现 |
| US-03 | 用文字与 AI 对话 | P0 | ✅ 已实现 |
| US-04 | AI 能基于摄像头画面回答我的问题 | P0 | ✅ 已实现 |
| US-05 | 看到实时的 Token 消耗和费用估算 | P1 | ✅ 已实现 |
| US-06 | 看到对话历史记录 | P1 | ✅ 已实现 |
| US-07 | 语音识别的文字实时显示在输入框中 | P1 | ✅ 已实现 |
| US-08 | AI 的回复是流式输出的 | P1 | ✅ 已实现 |
| US-09 | 系统能在预算耗尽时友好提示 | P2 | ✅ 已实现 |
| US-10 | 手动控制摄像头和麦克风的开关 | P0 | ✅ 已实现 |
| US-11 | 会话有 Token 预算限制 | P1 | ✅ 已实现 |
| US-12 | 支持多轮对话中引用历史画面 | P3 | ❌ 技术限制（Token 消耗过大） |
| US-13 | AI 主动发起对话 | P3 | ❌ 超出 MVP 范围 |
| US-14 | 画面中物体识别高亮 | P3 | ❌ 超出 MVP 范围 |

## 运营成本控制策略

### 思考过的策略

| 策略 | 描述 | 采用 |
|------|------|------|
| 低分辨率帧采样 | 320x240, 2fps，大幅减少 Vision API 图片 Token | ✅ |
| JPEG 压缩 | 质量 0.6，平衡画质和带宽 | ✅ |
| 会话级 Token 预算 | 默认 500,000 Token / 会话上限 | ✅ |
| 轮次限制 | 默认 50 轮对话上限 | ✅ |
| 流式响应 | stream=True，用户无需等待完整回复 | ✅ |
| 上下文窗口管理 | 只保留最近 5 轮对话，控制输入 Token | ✅ |
| 端上语音识别 | Web Speech API，免费且无需云端调用 | ✅ |
| 预估费用仪表盘 | 实时展示 Token 使用和费用估算 | ✅ |
| 多模型定价兼容 | 支持 GPT-4o / DeepSeek / Qwen VL 等多模型定价表 | ✅ |
| 场景变化检测（差异帧） | 增加浏览器端计算复杂度，2fps 已足够 | ❌ |
| 动态 JPEG 质量调节 | 需要客户端网络检测，与帧率调节重叠 | ❌ |



## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Uvicorn（Python） |
| 前端 | 原生 HTML/CSS/JS SPA |
| 通信 | WebSocket 全双工 |
| AI 模型 | 硅基流动 Qwen3-VL-8B / GPT-4o Vision / DeepSeek / OpenAI 兼容模型 |
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

## 设计文档

- [设计文档](docs/design_document.md) — 用户故事与成本控制详情
- [EyesChat 设计方案](docs/EyesChat_设计方案.md) — 完整技术架构与决策记录
- [EyesChat LensMate 最终方案](docs/EyesChat_LensMate_最终方案.md) — 需求分析与功能规划

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp backend/.env.example backend/.env
# 编辑 backend/.env，填入 OPENAI_API_KEY 和 OPENAI_BASE_URL
# 当前默认使用硅基流动 (SiliconFlow) 的 Qwen3-VL-8B-Instruct

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
│   ├── .env                       # 配置文件（API Key、模型等）
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

本项目为原创作品，代码自主编写。仅依赖以下开源库（均已列明于 requirements.txt）：

| 依赖 | 用途 | 许可证 |
|------|------|--------|
| FastAPI + Uvicorn | Web 框架与 ASGI 服务器 | MIT |
| OpenAI Python SDK | LLM 与 TTS API 调用 | Apache 2.0 |
| Pydantic Settings | 类型安全的配置管理 | MIT |
| python-dotenv | 环境变量加载 | BSD-3 |
| httpx | HTTP 客户端 | BSD-3 |
| Web Speech API | 浏览器端语音识别与合成 | 浏览器内置（免费） |
