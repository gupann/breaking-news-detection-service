import json
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from src.config import BREAKING_NEWS_TTL_HOURS, VELOCITY_WINDOW_MINUTES
from src.models import ScoredArticle


class RedisStateStore:
    def __init__(self, redis_url: Optional[str] = None):
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis is not available. Install with: pip install redis[hiredis]")

        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis_client: Optional[redis.Redis] = None

        # key prefixes
        self.PREFIX_BREAKING = "breaking_news:"
        self.PREFIX_TOPIC = "topic_windows:"
        self.PREFIX_SEEN = "seen_hashes"
        self.KEY_TOTAL = "total_processed"
        self.KEY_START = "start_time"
        self.KEY_SIMULATION = "simulation_time"
        self.KEY_LAST_PROCESSED = "last_processed_time"
        self.KEY_LAST_CLEANUP = "last_cleanup_time"

        # initialize connection
        self._ensure_connection()

    def _ensure_connection(self):
        if self.redis_client is None:
            # create Redis client (synchronous)
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # test connection
            try:
                self.redis_client.ping()
            except redis.ConnectionError as e:
                raise ConnectionError(
                    f"failed to connect to Redis at {self.redis_url}: {e}")

    def reset(self):
        if not self.redis_client:
            self._ensure_connection()

        # delete all keys with our prefixes
        for key in self.redis_client.scan_iter(match=f"{self.PREFIX_BREAKING}*"):
            self.redis_client.delete(key)
        for key in self.redis_client.scan_iter(match=f"{self.PREFIX_TOPIC}*"):
            self.redis_client.delete(key)

        self.redis_client.delete(self.PREFIX_SEEN)
        self.redis_client.delete(self.KEY_TOTAL)
        self.redis_client.delete(self.KEY_START)
        self.redis_client.delete(self.KEY_SIMULATION)
        self.redis_client.delete(self.KEY_LAST_PROCESSED)
        self.redis_client.delete(self.KEY_LAST_CLEANUP)

        # set start time
        self.redis_client.set(
            self.KEY_START,
            datetime.now(timezone.utc).isoformat()
        )

    @property
    def breaking_news(self):
        return RedisDict(self.redis_client, self.PREFIX_BREAKING)

    @property
    def topic_windows(self):
        return RedisTopicWindows(self.redis_client, self.PREFIX_TOPIC)

    @property
    def seen_hashes(self):
        return RedisSet(self.redis_client, self.PREFIX_SEEN)

    @property
    def total_processed(self):
        result = self.redis_client.get(self.KEY_TOTAL)
        return int(result) if result else 0

    @total_processed.setter
    def total_processed(self, value: int):
        self.redis_client.set(self.KEY_TOTAL, str(value))

    @property
    def start_time(self):
        result = self.redis_client.get(self.KEY_START)
        if result:
            return datetime.fromisoformat(result)
        now = datetime.now(timezone.utc)
        self.redis_client.set(self.KEY_START, now.isoformat())
        return now

    @property
    def simulation_time(self):
        result = self.redis_client.get(self.KEY_SIMULATION)
        if result:
            return datetime.fromisoformat(result)
        return None

    @simulation_time.setter
    def simulation_time(self, value: Optional[datetime]):
        if value is None:
            self.redis_client.delete(self.KEY_SIMULATION)
        else:
            self.redis_client.set(self.KEY_SIMULATION, value.isoformat())

    @property
    def last_processed_time(self):
        result = self.redis_client.get(self.KEY_LAST_PROCESSED)
        if result:
            return datetime.fromisoformat(result)
        return None

    @last_processed_time.setter
    def last_processed_time(self, value: Optional[datetime]):
        if value is None:
            self.redis_client.delete(self.KEY_LAST_PROCESSED)
        else:
            self.redis_client.set(self.KEY_LAST_PROCESSED, value.isoformat())

    @property
    def last_cleanup_time(self):
        result = self.redis_client.get(self.KEY_LAST_CLEANUP)
        if result:
            return datetime.fromisoformat(result)
        return None

    @last_cleanup_time.setter
    def last_cleanup_time(self, value: Optional[datetime]):
        if value is None:
            self.redis_client.delete(self.KEY_LAST_CLEANUP)
        else:
            self.redis_client.set(self.KEY_LAST_CLEANUP, value.isoformat())

    def get_processing_rate(self) -> float:
        total = self.total_processed
        if total == 0:
            return 0.0
        elapsed = (datetime.now(timezone.utc) -
                   self.start_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return total / elapsed

    def get_uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def cleanup_expired_breaking_news(self) -> int:
        if self.simulation_time is None:
            current_time = datetime.now(timezone.utc)
        else:
            current_time = self.simulation_time

        cutoff_time = current_time - timedelta(hours=BREAKING_NEWS_TTL_HOURS)
        expired_count = 0

        for key in self.redis_client.scan_iter(match=f"{self.PREFIX_BREAKING}*"):
            data = self.redis_client.get(key)
            if data:
                try:
                    scored_dict = json.loads(data)
                    detected_at_str = scored_dict.get("detected_at")
                    if detected_at_str:
                        detected_at = datetime.fromisoformat(detected_at_str)
                        if detected_at < cutoff_time:
                            self.redis_client.delete(key)
                            expired_count += 1
                except (json.JSONDecodeError, ValueError):
                    # invalid data, delete it
                    self.redis_client.delete(key)

        return expired_count

    def cleanup_topic_windows(self) -> int:
        if self.simulation_time is None:
            current_time = datetime.now(timezone.utc)
        else:
            current_time = self.simulation_time

        cutoff = current_time - timedelta(minutes=VELOCITY_WINDOW_MINUTES * 2)
        cutoff_timestamp = cutoff.timestamp()
        cleaned_topics = 0

        for key in self.redis_client.scan_iter(match=f"{self.PREFIX_TOPIC}*"):
            removed = self.redis_client.zremrangebyscore(
                key, "-inf", cutoff_timestamp)
            if removed > 0:
                cleaned_topics += 1

        return cleaned_topics


class RedisDict:
    def __init__(self, client, prefix: str):
        self.client = client
        self.prefix = prefix

    def __getitem__(self, key: str) -> ScoredArticle:
        result = self.client.get(f"{self.prefix}{key}")
        if result is None:
            raise KeyError(key)
        data = json.loads(result)
        return ScoredArticle(**data)

    def __setitem__(self, key: str, value: ScoredArticle):
        data = value.model_dump_json()
        self.client.set(f"{self.prefix}{key}", data)

    def __delitem__(self, key: str):
        self.client.delete(f"{self.prefix}{key}")

    def __contains__(self, key: str) -> bool:
        result = self.client.exists(f"{self.prefix}{key}")
        return bool(result)

    def __len__(self) -> int:
        count = 0
        for _ in self.client.scan_iter(match=f"{self.prefix}*"):
            count += 1
        return count

    def items(self):
        items = []
        for key in self.client.scan_iter(match=f"{self.prefix}*"):
            article_id = key[len(self.prefix):]
            data = self.client.get(key)
            if data:
                scored_dict = json.loads(data)
                items.append((article_id, ScoredArticle(**scored_dict)))
        return items

    def values(self):
        return [v for _, v in self.items()]

    def keys(self):
        keys = []
        for key in self.client.scan_iter(match=f"{self.prefix}*"):
            keys.append(key[len(self.prefix):])
        return keys


class RedisSet:
    def __init__(self, client, key: str):
        self.client = client
        self.key = key

    def add(self, value: str):
        self.client.sadd(self.key, value)

    def __contains__(self, value: str) -> bool:
        result = self.client.sismember(self.key, value)
        return bool(result)

    def __len__(self) -> int:
        result = self.client.scard(self.key)
        return result or 0


class RedisTopicWindows:
    def __init__(self, client, prefix: str):
        self.client = client
        self.prefix = prefix

    def __getitem__(self, topic: str) -> "RedisTopicList":
        return RedisTopicList(self.client, f"{self.prefix}{topic}")

    def __setitem__(self, topic: str, value: list):
        key = f"{self.prefix}{topic}"
        # delete existing
        self.client.delete(key)
        # add new items
        if value:
            mapping = {}
            for timestamp, article_id in value:
                score = timestamp.timestamp()
                member = f"{score}|{article_id}"
                mapping[member] = score
            if mapping:
                self.client.zadd(key, mapping)

    def items(self):
        topics = {}
        for key in self.client.scan_iter(match=f"{self.prefix}*"):
            topic = key[len(self.prefix):]
            topics[topic] = self[topic]
        return topics.items()

    def keys(self):
        keys = []
        for key in self.client.scan_iter(match=f"{self.prefix}*"):
            keys.append(key[len(self.prefix):])
        return keys

    def __len__(self) -> int:
        count = 0
        for _ in self.client.scan_iter(match=f"{self.prefix}*"):
            count += 1
        return count


class RedisTopicList:
    def __init__(self, client, key: str):
        self.client = client
        self.key = key

    def append(self, item: tuple):
        timestamp, article_id = item
        score = timestamp.timestamp()
        member = f"{score}|{article_id}"
        self.client.zadd(self.key, {member: score})

    def __iter__(self):
        results = self.client.zrange(self.key, 0, -1, withscores=True)
        for value, score in results:
            parts = value.split("|", 1)
            if len(parts) == 2:
                timestamp = datetime.fromtimestamp(
                    float(parts[0]), tz=timezone.utc)
                article_id = parts[1]
                yield (timestamp, article_id)

    def __len__(self) -> int:
        return self.client.zcard(self.key) or 0

    def __getitem__(self, index: int) -> tuple:
        results = self.client.zrange(self.key, index, index, withscores=True)
        if not results:
            raise IndexError("list index out of range")
        value, score = results[0]
        parts = value.split("|", 1)
        if len(parts) == 2:
            timestamp = datetime.fromtimestamp(
                float(parts[0]), tz=timezone.utc)
            article_id = parts[1]
            return (timestamp, article_id)
        raise IndexError("list index out of range")

    def __setitem__(self, index, value):
        if isinstance(index, slice) and index == slice(None):
            # full list assignment: state.topic_windows[topic] = [...]
            # delete existing
            self.client.delete(self.key)
            # add new items
            if value:
                mapping = {}
                for timestamp, article_id in value:
                    score = timestamp.timestamp()
                    member = f"{score}|{article_id}"
                    mapping[member] = score
                if mapping:
                    self.client.zadd(self.key, mapping)
        else:
            raise NotImplementedError(
                "use append() to add items or assign full list")

    def __repr__(self) -> str:
        return f"RedisTopicList({list(self)})"
