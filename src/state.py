from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.config import BREAKING_NEWS_TTL_HOURS, VELOCITY_WINDOW_MINUTES
from src.models import ScoredArticle


class StateStore:
    def __init__(self):
        self.reset()

    # reset all state
    def reset(self):
        # active breaking news: id -> ScoredArticle
        self.breaking_news: dict[str, ScoredArticle] = {}
        # topic velocity tracking: topic -> list of (timestamp, article_id)
        self.topic_windows: dict[str,
                                 list[tuple[datetime, str]]] = defaultdict(list)
        # deduplication: set of content hashes
        self.seen_hashes: set[str] = set()
        # statistics
        self.total_processed: int = 0
        self.start_time: datetime = datetime.now(timezone.utc)
        self.simulation_time: Optional[datetime] = None
        self.last_processed_time: Optional[datetime] = None
        self.last_cleanup_time: Optional[datetime] = None

    # get processing rate (articles per second)
    def get_processing_rate(self) -> float:
        if self.total_processed == 0:
            return 0.0
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return self.total_processed / elapsed

    # get uptime in seconds
    def get_uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    # cleanup expired breaking news
    def cleanup_expired_breaking_news(self) -> int:
        if self.simulation_time is None:
            current_time = datetime.now(timezone.utc)
        else:
            current_time = self.simulation_time

        cutoff_time = current_time - timedelta(hours=BREAKING_NEWS_TTL_HOURS)
        expired_ids = []

        for article_id, scored in self.breaking_news.items():
            if scored.detected_at < cutoff_time:
                expired_ids.append(article_id)

        for article_id in expired_ids:
            del self.breaking_news[article_id]

        return len(expired_ids)

    # cleanup old topic windows
    def cleanup_topic_windows(self) -> int:
        if self.simulation_time is None:
            current_time = datetime.now(timezone.utc)
        else:
            current_time = self.simulation_time

        cutoff = current_time - timedelta(minutes=VELOCITY_WINDOW_MINUTES * 2)
        cleaned_topics = 0

        for topic in list(self.topic_windows.keys()):
            original_count = len(self.topic_windows[topic])
            self.topic_windows[topic] = [
                (t, aid) for t, aid in self.topic_windows[topic]
                if t >= cutoff
            ]
            if len(self.topic_windows[topic]) < original_count:
                cleaned_topics += 1

        return cleaned_topics


# global state instance
state = StateStore()
