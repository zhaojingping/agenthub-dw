# AgentHub 智能管理系统

公共传播 Agent Hub 智能管理系统 - AI 驱动的舆情监测与危机应对平台

## 技术栈

- **Web 框架**: FastAPI
- **Agent 编排**: LangGraph
- **数据库**: PostgreSQL (支持多租户 RLS)
- **可观测性**: OpenTelemetry
- **AI 模型**: 支持 OpenAI / Qwen / 文心 等

## 项目结构

```
src/
├── api/          # API 路由
├── core/         # 核心配置
├── db/           # 数据库模型和连接
├── agents/       # Agent 定义和编排
── services/     # 业务服务层
└── models/       # Pydantic 数据模型
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动服务
uvicorn src.api.main:app --reload
```
