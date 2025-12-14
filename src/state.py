from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

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


# global state instance
state = StateStore()
