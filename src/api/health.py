from datetime import datetime, timezone


# health check endpoint
async def health_check():
    from src.main import processor
    from src.state import state
    from src.config import USE_REDIS, REDIS_URL

    # determine state store type
    state_store_type = "redis" if USE_REDIS else "in-memory"
    state_store_info = REDIS_URL if USE_REDIS else None

    return {
        "status": "healthy",
        "processor_running": processor.is_running if processor else False,
        "state_store": state_store_type,
        "redis_url": state_store_info,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
