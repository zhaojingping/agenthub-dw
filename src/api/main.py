from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentHub 智能管理系统",
        description="公共传播 Agent Hub - AI 驱动的舆情监测与危机应对平台",
        version="0.1.0",
        debug=settings.app_debug,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "0.1.0"}

    # Register routers
    from src.api import sentiment, monitoring
    app.include_router(sentiment.router, prefix="/api/v1", tags=["sentiment"])
    app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])

    return app
