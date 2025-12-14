from datetime import datetime, timezone


# health check endpoint
async def health_check():
    from src.main import processor

    return {
        "status": "healthy",
        "processor_running": processor.is_running if processor else False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
