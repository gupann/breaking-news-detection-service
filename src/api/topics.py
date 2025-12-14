from src.state import state

# major topics that should always be shown
MAJOR_TOPICS = {
    'ukraine', 'russia', 'putin', 'zelensky', 'kyiv', 'moscow',
    'covid', 'coronavirus', 'pandemic',
    'china', 'taiwan', 'beijing',
    'israel', 'gaza', 'palestine',
    'climate', 'earthquake', 'hurricane',
    'trump', 'biden', 'election',
    'general',
}


# get list of active topics with article counts
async def get_topics():
    topics = []

    # get topics from breaking news (more relevant)
    breaking_topics = set()
    for scored in state.breaking_news.values():
        if scored.topic:
            breaking_topics.add(scored.topic)

    for topic, windows in state.topic_windows.items():
        if len(windows) > 0:
            is_major = topic in MAJOR_TOPICS
            has_breaking = topic in breaking_topics
            has_velocity = len(windows) >= 2

            if is_major or has_breaking or has_velocity:
                topics.append({
                    "topic": topic,
                    "article_count": len(windows),
                })

    # sort by article count (highest first), then by major topics
    topics.sort(key=lambda x: (
        x["topic"] not in MAJOR_TOPICS,  # major topics first
        -x["article_count"]  # then by count descending
    ))

    return {
        "count": len(topics),
        "topics": topics,
    }
