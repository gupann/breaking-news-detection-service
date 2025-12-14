from typing import Optional

from fastapi import Query

from src.models import BreakingNewsItem, BreakingNewsResponse
from src.state import state
from src.api.utils import format_time_ago


# get current breaking news
async def get_breaking_news(
    topic: Optional[str] = Query(None, description="Filter by topic"),
) -> BreakingNewsResponse:
    breaking_items = []

    for article_id, scored in state.breaking_news.items():
        # filter by topic
        if topic and scored.topic != topic:
            continue

        # convert to API response format
        item = BreakingNewsItem(
            id=scored.article.id,
            title=scored.article.title,
            description=scored.article.description,
            link=scored.article.link,
            category=scored.article.category,
            score=scored.total_score,
            detected_keywords=scored.detected_keywords,
            topic=scored.topic,
            pub_date=scored.article.pub_date,
            detected_at=scored.detected_at,
            time_ago=format_time_ago(scored.detected_at),
        )
        breaking_items.append(item)

    # sort by score (highest first)
    breaking_items.sort(key=lambda x: x.score, reverse=True)

    return BreakingNewsResponse(
        count=len(breaking_items),
        breaking_news=breaking_items,
    )
