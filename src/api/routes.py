from fastapi import APIRouter

from src.api import breaking, health, stats, topics
from src.models import BreakingNewsResponse, StatsResponse

# create API router
api_router = APIRouter(prefix="/api", tags=["api"])

# register endpoints
api_router.get("/health")(health.health_check)
api_router.get(
    "/breaking", response_model=BreakingNewsResponse)(breaking.get_breaking_news)
api_router.get("/stats", response_model=StatsResponse)(stats.get_stats)
api_router.get("/topics")(topics.get_topics)
