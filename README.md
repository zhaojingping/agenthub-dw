# 公共传播 Agent Hub

AI 驱动的舆情监测与危机应对智能管理系统

## 技术栈

- **Web 框架**: FastAPI
- **Agent 编排**: LangGraph
- **数据库**: PostgreSQL (支持多租户 RLS)
- **可观测性**: OpenTelemetry
- **AI 模型**: 支持 OpenAI / Qwen / 文心 等

## 项目结构

```
src/
├── api/              # API 路由
│   ├── main.py       # 应用入口
│   └── monitoring.py # 舆情监测 API
├── core/             # 核心配置
├── db/               # 数据库连接
├── agents/           # Agent 定义和编排
├── services/         # 业务服务层
│   ├── base_collector.py  # 采集器基类
│   ├── collectors.py      # 采集器实现
│   ├── sentiment.py       # 情感分析
│   ├── smart_filter.py    # 智能过滤
│   └── scheduler.py       # 7x24 调度器
└── models/           # 数据模型
```

## API 接口

### 工作台
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboard/overview` | 工作台概览（今日舆情、待处理预警、进行中项目、本月产出） |
| GET | `/api/v1/dashboard/trend` | 舆情趋势（近 N 天） |

### 监测任务
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks` | 创建监测任务 |
| GET | `/api/v1/tasks` | 列出任务 |
| GET | `/api/v1/tasks/{id}` | 任务详情 |
| PUT | `/api/v1/tasks/{id}` | 更新任务 |
| DELETE | `/api/v1/tasks/{id}` | 删除任务 |

### 舆情数据
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/mentions` | 舆情列表（支持关键词搜索、平台/情感筛选） |
| GET | `/api/v1/mentions/{id}` | 舆情详情 |
| GET | `/api/v1/mentions/stats` | 舆情统计 |
| POST | `/api/v1/collect` | 手动触发采集 |

### 预警管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/alerts` | 预警列表 |
| PUT | `/api/v1/alerts/{id}/resolve` | 处理预警 |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 启动服务
uvicorn src.api.main:app --reload
```

启动后访问 http://localhost:8000/docs 查看 API 文档
