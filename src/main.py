import asyncio
import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from dateutil import parser as date_parser

from src.config import (
    TIME_ACCELERATION,
    BREAKING_SCORE_THRESHOLD,
    WEIGHT_KEYWORD,
    WEIGHT_VELOCITY,
    WEIGHT_CATEGORY,
    WEIGHT_RECENCY,
)
from src.models import NewsArticle, ScoredArticle
from src.scoring import (
    calculate_keyword_score,
    calculate_velocity_score,
    calculate_category_score,
    calculate_recency_score,
    extract_topic,
)
from src.state import state


class StreamProcessor:
    def __init__(self, data_file: str, time_acceleration: float = TIME_ACCELERATION):
        self.data_file = data_file
        self.time_acceleration = time_acceleration
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.processed_count = 0

    # start processing the news stream
    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._process_stream())

    # stop processing
    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # loads CSV and processes articles chronologically
    async def _process_stream(self):
        print(f"Loading data from {self.data_file}...")

        try:
            df = pd.read_csv(self.data_file)
        except Exception as e:
            print(f"Failed to load data: {e}")
            return

        print(f"Loaded {len(df)} articles")

        # parse dates and sort chronologically
        df['parsed_date'] = df['pubDate'].apply(self._parse_date)
        df = df.dropna(subset=['parsed_date'])
        df = df.sort_values('parsed_date')

        # filter to most recent week of data
        if len(df) > 0:
            max_date = df['parsed_date'].max()
            min_date = max_date - timedelta(days=7)
            df = df[(df['parsed_date'] >= min_date) &
                    (df['parsed_date'] <= max_date)]
            print(f"Processing week: {min_date.date()} to {max_date.date()}")
            print(f"{len(df)} articles in time range")

        # process articles with time simulation
        prev_article_time = None

        for idx, row in df.iterrows():
            if not self.is_running:
                break

            article_time = row['parsed_date']

            # simulate time delay between articles
            if prev_article_time is not None:
                time_diff = (article_time - prev_article_time).total_seconds()
                if time_diff > 0:
                    sleep_time = time_diff / self.time_acceleration
                    # cap to avoid long waits
                    sleep_time = min(sleep_time, 0.5)
                    if sleep_time > 0.001:
                        await asyncio.sleep(sleep_time)

            prev_article_time = article_time

            # update simulation time
            state.simulation_time = article_time

            # create article object
            article = NewsArticle(
                id=self._generate_id(row['guid']),
                title=str(row['title']),
                description=str(row.get('description', '')),
                pub_date=article_time,
                link=str(row['link']),
                category=self._extract_category(str(row['link'])),
            )

            # process the article
            await self._process_article(article)

            # show progress
            if state.total_processed % 10 == 0:
                print(f"Processed {state.total_processed} articles | "
                      f"Breaking: {len(state.breaking_news)} | "
                      f"Latest: {article.title[:50]}...")

        print(
            f"Stream processing complete. Total: {state.total_processed} articles")
        self.is_running = False

    # process a single article
    async def _process_article(self, article: NewsArticle):
        # deduplication
        content_hash = self._hash_content(article.title)
        if content_hash in state.seen_hashes:
            return  # skip duplicate
        state.seen_hashes.add(content_hash)

        # extract topic for tracking
        topic = extract_topic(article.title)

        # calculate keyword score
        keyword_score, detected_keywords = calculate_keyword_score(
            article.title)

        # calculate velocity score
        velocity_score = calculate_velocity_score(
            topic, article.pub_date, article.id)

        # calculate category score
        category_score = calculate_category_score(article.category)

        # calculate recency score
        recency_score = calculate_recency_score(article.pub_date)

        # calculate total score
        total_score = (
            keyword_score * WEIGHT_KEYWORD +
            velocity_score * WEIGHT_VELOCITY +
            category_score * WEIGHT_CATEGORY +
            recency_score * WEIGHT_RECENCY
        )

        # create scored article
        scored = ScoredArticle(
            article=article,
            keyword_score=keyword_score,
            velocity_score=velocity_score,
            category_score=category_score,
            recency_score=recency_score,
            total_score=total_score,
            is_breaking=total_score >= BREAKING_SCORE_THRESHOLD,
            detected_keywords=detected_keywords,
            topic=topic,
            detected_at=datetime.now(timezone.utc),
        )

        # store if breaking
        if scored.is_breaking:
            state.breaking_news[article.id] = scored

        state.total_processed += 1

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            return date_parser.parse(date_str)
        except Exception:
            return None

    # generate a short ID from the GUID
    def _generate_id(self, guid: str) -> str:
        return hashlib.md5(guid.encode()).hexdigest()[:12]

    # create a hash for deduplication
    def _hash_content(self, title: str) -> str:
        normalized = title.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    # extract category from BBC URL path
    # urls like: https://www.bbc.co.uk/news/world-europe-60638042
    def _extract_category(self, url: str) -> Optional[str]:
        match = re.search(r'bbc\.co\.uk/(?:news|sport)/([a-z-]+)', url.lower())
        if match:
            category = match.group(1).split('-')[0]
            return category
        return None
