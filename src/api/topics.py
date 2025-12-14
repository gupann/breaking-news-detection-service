from src.state import state


# get list of active topics with article counts
async def get_topics():
    topics = []

    for topic, windows in state.topic_windows.items():
        if len(windows) > 0:
            topics.append({
                "topic": topic,
                "article_count": len(windows),
            })

    # sort by article count (highest first)
    topics.sort(key=lambda x: x["article_count"], reverse=True)

    return {
        "count": len(topics),
        "topics": topics,
    }
