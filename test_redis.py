#!/usr/bin/env python3

from src.models import NewsArticle, ScoredArticle
from src.config import REDIS_URL, USE_REDIS
from datetime import datetime, timezone
import sys
import os
from pathlib import Path

# add src to path
sys.path.insert(0, str(Path(__file__).parent))


def test_redis_connection():
    print("Testing Redis connection...")

    try:
        import redis
        client = redis.from_url(REDIS_URL or "redis://localhost:6379")
        client.ping()
        print("Redis connection successful")
        return True
    except ImportError:
        print(
            "Redis not installed. Install with: pip install redis[hiredis]")
        return False
    except redis.ConnectionError as e:
        print(f"Redis connection failed: {e}")
        print("   Make sure Redis is running: redis-server")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_redis_state_store():
    print("\nTesting Redis state store...")

    # set Redis URL for testing
    if not USE_REDIS:
        os.environ["REDIS_URL"] = "redis://localhost:6379"
        # reload config
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.state import state
    else:
        from src.state import state

    # check if we're using Redis
    if "Redis" not in type(state).__name__:
        print("Not using Redis state store. Set REDIS_URL environment variable.")
        return False

    print(f"Using {type(state).__name__}")

    # test reset
    print("\n1. Testing reset()...")
    state.reset()
    print("   Reset successful")

    # test breaking news storage
    print("\n2. Testing breaking news storage...")
    test_article = NewsArticle(
        id="test123",
        title="Test Breaking News",
        description="This is a test",
        pub_date=datetime.now(timezone.utc),
        link="https://example.com",
        category="world"
    )

    test_scored = ScoredArticle(
        article=test_article,
        keyword_score=0.8,
        velocity_score=0.7,
        category_score=0.9,
        recency_score=0.6,
        total_score=0.75,
        is_breaking=True,
        detected_keywords=["breaking", "test"],
        topic="test",
        detected_at=datetime.now(timezone.utc)
    )

    state.breaking_news["test123"] = test_scored
    retrieved = state.breaking_news["test123"]
    assert retrieved.article.title == "Test Breaking News"
    print("   Breaking news storage/retrieval works")

    # test seen hashes
    print("\n3. Testing seen hashes...")
    state.seen_hashes.add("hash123")
    assert "hash123" in state.seen_hashes
    print("   Seen hashes work")

    # test topic windows
    print("\n4. Testing topic windows...")
    state.topic_windows["test_topic"].append(
        (datetime.now(timezone.utc), "article1"))
    assert len(state.topic_windows["test_topic"]) > 0
    print("   Topic windows work")

    # test counters
    print("\n5. Testing counters...")
    state.total_processed = 100
    assert state.total_processed == 100
    print("   Counters work")

    # test timestamps
    print("\n6. Testing timestamps...")
    now = datetime.now(timezone.utc)
    state.simulation_time = now
    assert state.simulation_time == now
    print("   Timestamps work")

    # test cleanup
    print("\n7. Testing cleanup...")
    expired = state.cleanup_expired_breaking_news()
    print(f"   Cleanup works (removed {expired} expired items)")

    # cleanup test data
    state.reset()
    print("\nAll Redis state store tests passed!")
    return True


def test_service_with_redis():
    print("\n" + "="*60)
    print("Testing full service with Redis")
    print("="*60)

    # set Redis URL
    os.environ["REDIS_URL"] = "redis://localhost:6379"

    # reload modules to pick up new config
    import importlib
    import src.config
    import src.state
    importlib.reload(src.config)
    importlib.reload(src.state)

    from src.state import state

    if "Redis" not in type(state).__name__:
        print("Service not using Redis. Check configuration.")
        return False

    print(f"Service is using {type(state).__name__}")

    # test that state persists across "restarts" (new state object)
    print("\nTesting state persistence...")
    state.total_processed = 50
    state.breaking_news["persist_test"] = ScoredArticle(
        article=NewsArticle(
            id="persist_test",
            title="Persistent Test",
            description="Test",
            pub_date=datetime.now(timezone.utc),
            link="https://example.com"
        ),
        keyword_score=0.5,
        velocity_score=0.5,
        category_score=0.5,
        recency_score=0.5,
        total_score=0.6,
        is_breaking=True,
        detected_at=datetime.now(timezone.utc)
    )

    # simulate restart by creating new state instance
    from src.state_redis import RedisStateStore
    new_state = RedisStateStore(redis_url="redis://localhost:6379")

    assert new_state.total_processed == 50
    assert "persist_test" in new_state.breaking_news
    print("   State persists across restarts!")

    # cleanup
    new_state.reset()
    print("\nFull service test passed!")
    return True


def main():
    print("="*60)
    print("Redis Integration Test")
    print("="*60)

    # check if Redis URL is set
    if not USE_REDIS:
        print("\nREDIS_URL not set. Using default: redis://localhost:6379")
        print("   Set REDIS_URL environment variable to use custom Redis instance")

    # test connection
    if not test_redis_connection():
        print("\nRedis connection test failed. Please start Redis first.")
        print("\nTo start Redis:")
        print("  # macOS (Homebrew):")
        print("  brew services start redis")
        print("  # or run directly:")
        print("  redis-server")
        print("\n  # Linux:")
        print("  sudo systemctl start redis")
        print("\n  # Docker:")
        print("  docker run -d -p 6379:6379 redis:latest")
        return 1

    # test state store
    if not test_redis_state_store():
        return 1

    # test full service
    if not test_service_with_redis():
        return 1

    print("\n" + "="*60)
    print("All Redis tests passed!")
    print("="*60)
    print("\nTo use Redis with the service:")
    print("  REDIS_URL=redis://localhost:6379 python3 -m uvicorn src.main:app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
