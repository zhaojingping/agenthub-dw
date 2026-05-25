from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MonitorRequest(BaseModel):
    keywords: list[str]
    platforms: list[str] | None = None


class MonitorResponse(BaseModel):
    items: list[dict]
    total: int


@router.post("/monitoring/search", response_model=MonitorResponse)
async def search_mentions(req: MonitorRequest):
    """Search mentions across platforms."""
    # TODO: integrate with data collection service
    return MonitorResponse(items=[], total=0)


@router.get("/monitoring/alerts")
async def get_alerts():
    """Get active alerts."""
    return {"alerts": []}
