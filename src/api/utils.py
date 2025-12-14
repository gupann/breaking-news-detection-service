from datetime import datetime, timezone

from src.state import state


def format_time_ago(dt: datetime) -> str:
    if state.simulation_time is None:
        now = datetime.now(timezone.utc)
    else:
        now = state.simulation_time

    diff = now - dt

    if diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())}s ago"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}h ago"
    else:
        return f"{int(diff.total_seconds() / 86400)}d ago"
