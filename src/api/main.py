from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.services.scheduler import scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await scheduler.start()
    yield
    # Shutdown
    await scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentHub 智能管理系统",
        description="公共传播 Agent Hub - AI 驱动的舆情监测与危机应对平台",
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
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
    from src.api import monitoring
    app.include_router(monitoring.router, prefix="/api/v1", tags=["monitoring"])

    return app
