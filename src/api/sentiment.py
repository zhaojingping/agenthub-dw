from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SentimentRequest(BaseModel):
    text: str
    brand_voice: str | None = None


class SentimentResponse(BaseModel):
    sentiment: str  # positive / negative / neutral
    score: float
    confidence: float
    keywords: list[str]


@router.post("/sentiment/analyze", response_model=SentimentResponse)
async def analyze_sentiment(req: SentimentRequest):
    """Analyze sentiment of given text."""
    # TODO: integrate with AI model
    return SentimentResponse(
        sentiment="neutral",
        score=0.5,
        confidence=0.8,
        keywords=[],
    )
