from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

# raw news article from the data source


class NewsArticle(BaseModel):
    id: str
    title: str
    description: str
    pub_date: datetime
    link: str
    category: Optional[str] = None

# scored article with breaking news scoring details


class ScoredArticle(BaseModel):
    article: NewsArticle
    keyword_score: float = Field(ge=0, le=1)
    velocity_score: float = Field(ge=0, le=1)
    category_score: float = Field(ge=0, le=1)
    recency_score: float = Field(ge=0, le=1)
    total_score: float = Field(ge=0, le=1)
    is_breaking: bool = False
    detected_keywords: list[str] = []
    topic: Optional[str] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# breaking news item for API response


class BreakingNewsItem(BaseModel):
    id: str
    title: str
    description: str
    link: str
    category: Optional[str]
    score: float
    detected_keywords: list[str]
    topic: Optional[str]
    pub_date: datetime
    detected_at: datetime
    time_ago: str = ""

# system statistics response


class StatsResponse(BaseModel):
    total_processed: int
    breaking_news_count: int
    active_topics: int
    processing_rate: float  # articles per second
    simulation_time: Optional[datetime]
    real_start_time: datetime
    uptime_seconds: float

# API response for breaking news endpoint


class BreakingNewsResponse(BaseModel):
    count: int
    breaking_news: list[BreakingNewsItem]
