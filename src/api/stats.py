from src.models import StatsResponse
from src.state import state


# get system statistics
async def get_stats() -> StatsResponse:
    return StatsResponse(
        total_processed=state.total_processed,
        breaking_news_count=len(state.breaking_news),
        active_topics=len(state.topic_windows),
        processing_rate=state.get_processing_rate(),
        simulation_time=state.simulation_time,
        real_start_time=state.start_time,
        uptime_seconds=state.get_uptime_seconds(),
    )
