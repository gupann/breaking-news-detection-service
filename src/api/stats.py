from src.models import StatsResponse
from src.state import state


# get system statistics
async def get_stats() -> StatsResponse:
    processing_status = "complete" if state.processing_complete else "processing"
    return StatsResponse(
        total_processed=state.total_processed,
        breaking_news_count=len(state.breaking_news),
        active_topics=len(state.topic_windows),
        processing_rate=state.get_processing_rate(),
        processing_status=processing_status,
        final_processing_rate=state.final_processing_rate,
        simulation_time=state.simulation_time,
        real_start_time=state.start_time,
        uptime_seconds=state.get_uptime_seconds(),
    )
