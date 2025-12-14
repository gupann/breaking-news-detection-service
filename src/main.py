import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from dateutil import parser as date_parser

from src.config import DATA_FILE, TIME_ACCELERATION
from src.models import NewsArticle


class StreamProcessor:
    def __init__(self, data_file: str, time_acceleration: float = TIME_ACCELERATION):
        self.data_file = data_file
        self.time_acceleration = time_acceleration
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.processed_count = 0

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._process_stream())

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

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

            # create article object
            article = NewsArticle(
                id=self._generate_id(row['guid']),
                title=str(row['title']),
                description=str(row.get('description', '')),
                pub_date=article_time,
                link=str(row['link']),
                category=self._extract_category(str(row['link'])),
            )

            # track processed count and show progress
            self.processed_count += 1
            if self.processed_count % 10 == 0:
                print(f"Processed {self.processed_count} articles | "
                      f"Latest: {article.title[:50]}...")

        print(
            f"Stream processing complete. Total: {self.processed_count} articles")
        self.is_running = False

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            return date_parser.parse(date_str)
        except Exception:
            return None

    def _generate_id(self, guid: str) -> str:
        return hashlib.md5(guid.encode()).hexdigest()[:12]

    def _extract_category(self, url: str) -> Optional[str]:
        # urls like: https://www.bbc.co.uk/news/world-europe-60638042
        match = re.search(r'bbc\.co\.uk/(?:news|sport)/([a-z-]+)', url.lower())
        if match:
            category = match.group(1).split('-')[0]
            return category
        return None
