import re
from datetime import datetime, timedelta
from typing import Optional

from src.config import (
    URGENCY_KEYWORDS,
    VELOCITY_WINDOW_MINUTES,
    VELOCITY_THRESHOLD,
    CATEGORY_SCORES,
    DEFAULT_CATEGORY_SCORE,
)
from src.state import state


# calculate urgency score based on keywords
def calculate_keyword_score(title: str) -> tuple[float, list[str]]:
    title_lower = title.lower()
    detected = []

    for keyword in URGENCY_KEYWORDS:
        if keyword in title_lower:
            detected.append(keyword)

    if not detected:
        return 0.0, []

    # score based on number and type of keywords
    score = min(len(detected) * 0.3, 1.0)

    # increase score for high urgency keywords
    high_urgency = {'breaking', 'just in', 'urgent', 'killed', 'attack', 'war'}
    if any(k in detected for k in high_urgency):
        score = min(score + 0.3, 1.0)

    return score, detected


# calculate topic velocity score
def calculate_velocity_score(topic: str, pub_date: datetime, article_id: str) -> float:
    # add current article to topic window
    state.topic_windows[topic].append((pub_date, article_id))

    # clean old entries outside the window
    cutoff = pub_date - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
    state.topic_windows[topic] = [
        (t, aid) for t, aid in state.topic_windows[topic]
        if t >= cutoff
    ]

    # count articles in window
    count = len(state.topic_windows[topic])

    if count >= VELOCITY_THRESHOLD:
        # velocity detected - scale score based on count
        return min((count - VELOCITY_THRESHOLD + 1) * 0.3 + 0.4, 1.0)

    return 0.0


# extract main topic from title for tracking
def extract_topic(title: str) -> str:
    title_lower = title.lower()

    # check major topics
    major_topics = [
        'ukraine', 'russia', 'putin', 'zelensky', 'kyiv', 'moscow',
        'covid', 'coronavirus', 'pandemic',
        'china', 'taiwan', 'beijing',
        'israel', 'gaza', 'palestine',
        'climate', 'earthquake', 'hurricane',
        'trump', 'biden', 'election',
    ]

    for topic in major_topics:
        if topic in title_lower:
            return topic

    # fallback: first significant word
    words = re.findall(r'\b[a-zA-Z]{4,}\b', title)
    if words:
        return words[0].lower()

    return 'general'


# calculate category score based on news category priority
def calculate_category_score(category: Optional[str]) -> float:
    if not category:
        return DEFAULT_CATEGORY_SCORE
    return CATEGORY_SCORES.get(category, DEFAULT_CATEGORY_SCORE)


# calculate recency score based on article age
def calculate_recency_score(pub_date: datetime) -> float:
    if state.simulation_time is None:
        return 1.0

    age = (state.simulation_time - pub_date).total_seconds() / 3600  # hours

    if age < 1:
        return 1.0
    elif age < 3:
        return 0.8
    elif age < 6:
        return 0.5
    else:
        return 0.2
