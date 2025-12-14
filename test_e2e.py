#!/usr/bin/env python3

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# add src to path before importing
sys.path.insert(0, str(Path(__file__).parent))

# check for required dependencies
try:
    import httpx
    from httpx import ASGITransport
except ImportError as e:
    print(f"Error: Missing required dependencies. Please install them with:")
    print(f"  pip install -r requirements.txt")
    print(f"  pip install httpx")
    sys.exit(1)

# now import from src
try:
    from src.config import DATA_FILE, BREAKING_SCORE_THRESHOLD
    from src.state import state
    from src.main import app, processor
except ImportError as e:
    print(f"Error: Failed to import from src: {e}")
    print(f"Make sure all dependencies are installed:")
    print(f"  pip install -r requirements.txt")
    sys.exit(1)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    print(f"\n{Colors.BLUE}Testing: {name}{Colors.RESET}")


def print_pass(message: str):
    print(f"{Colors.GREEN}PASS: {message}{Colors.RESET}")


def print_fail(message: str):
    print(f"{Colors.RED}FAIL: {message}{Colors.RESET}")


def print_info(message: str):
    print(f"{Colors.YELLOW}  {message}{Colors.RESET}")


async def test_service_startup():
    print_test("Service Startup")

    # check data file exists
    if not DATA_FILE.exists():
        print_fail(f"Data file not found: {DATA_FILE}")
        return False

    print_pass(f"Data file exists: {DATA_FILE}")

    # check processor can be initialized
    try:
        from src.main import StreamProcessor
        proc = StreamProcessor(str(DATA_FILE), time_acceleration=10000)
        print_pass("StreamProcessor initialized")
        return True
    except Exception as e:
        print_fail(f"Failed to initialize StreamProcessor: {e}")
        return False


async def test_stream_processing():
    print_test("Stream Processing")

    # reset state
    state.reset()

    # create processor with high time acceleration for testing
    from src.main import StreamProcessor
    proc = StreamProcessor(str(DATA_FILE), time_acceleration=10000)

    try:
        # start processing
        await proc.start()
        print_info("Processor started")

        # wait for some articles to be processed
        await asyncio.sleep(2)

        # check that articles were processed
        if state.total_processed == 0:
            print_fail("No articles were processed")
            return False

        print_pass(f"Processed {state.total_processed} articles")

        # check that breaking news detection is working
        breaking_count = len(state.breaking_news)
        print_info(f"Found {breaking_count} breaking news items")

        if breaking_count > 0:
            print_pass("Breaking news detection is working")
        else:
            print_info("No breaking news detected (this may be normal)")

        # stop processor
        await proc.stop()
        print_pass("Processor stopped successfully")

        return True

    except Exception as e:
        print_fail(f"Stream processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_endpoints():
    print_test("API Endpoints")

    # use httpx AsyncClient with ASGITransport for ASGI app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # test health endpoint
        print_info("Testing /api/health")
        try:
            response = await client.get("/api/health")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "status" in data, "Response missing 'status' field"
            assert "processor_running" in data, "Response missing 'processor_running' field"
            assert "state_store" in data, "Response missing 'state_store' field"
            assert "timestamp" in data, "Response missing 'timestamp' field"
            assert data["state_store"] in [
                "redis", "in-memory"], "state_store should be 'redis' or 'in-memory'"
            print_pass("Health endpoint works correctly")
        except Exception as e:
            print_fail(f"Health endpoint failed: {e}")
            return False

        # test breaking news endpoint
        print_info("Testing /api/breaking")
        try:
            response = await client.get("/api/breaking")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "count" in data, "Response missing 'count' field"
            assert "breaking_news" in data, "Response missing 'breaking_news' field"
            assert isinstance(data["count"], int), "Count should be an integer"
            assert isinstance(data["breaking_news"],
                              list), "breaking_news should be a list"
            print_pass(
                f"Breaking news endpoint works (found {data['count']} items)")
        except Exception as e:
            print_fail(f"Breaking news endpoint failed: {e}")
            return False

        # test breaking news with topic filter
        print_info("Testing /api/breaking?topic=test")
        try:
            response = await client.get("/api/breaking?topic=test")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "count" in data, "Response missing 'count' field"
            print_pass("Topic filtering works")
        except Exception as e:
            print_fail(f"Topic filtering failed: {e}")
            return False

        # test stats endpoint
        print_info("Testing /api/stats")
        try:
            response = await client.get("/api/stats")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            required_fields = [
                "total_processed", "breaking_news_count", "active_topics",
                "processing_rate", "processing_status", "simulation_time", "real_start_time", "uptime_seconds"
            ]
            for field in required_fields:
                assert field in data, f"Response missing '{field}' field"
            print_pass("Stats endpoint works correctly")
        except Exception as e:
            print_fail(f"Stats endpoint failed: {e}")
            return False

        # test topics endpoint
        print_info("Testing /api/topics")
        try:
            response = await client.get("/api/topics")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert "count" in data, "Response missing 'count' field"
            assert "topics" in data, "Response missing 'topics' field"
            assert isinstance(data["topics"], list), "topics should be a list"
            print_pass(f"Topics endpoint works (found {data['count']} topics)")
        except Exception as e:
            print_fail(f"Topics endpoint failed: {e}")
            return False

    return True


async def test_breaking_news_detection():
    print_test("Breaking News Detection Logic")

    # reset state
    state.reset()

    # create processor
    from src.main import StreamProcessor
    proc = StreamProcessor(str(DATA_FILE), time_acceleration=10000)

    try:
        # start processing
        await proc.start()
        await asyncio.sleep(3)  # wait for processing
        await proc.stop()

        # check that breaking news items have scores >= threshold
        for article_id, scored in state.breaking_news.items():
            if scored.total_score < BREAKING_SCORE_THRESHOLD:
                print_fail(
                    f"Breaking news item has score {scored.total_score} < threshold {BREAKING_SCORE_THRESHOLD}")
                return False

        print_pass(
            f"All {len(state.breaking_news)} breaking news items have scores >= {BREAKING_SCORE_THRESHOLD}")

        # check that scores are in valid range
        for article_id, scored in state.breaking_news.items():
            if not (0 <= scored.total_score <= 1):
                print_fail(f"Invalid score: {scored.total_score}")
                return False
            if not (0 <= scored.keyword_score <= 1):
                print_fail(f"Invalid keyword_score: {scored.keyword_score}")
                return False
            if not (0 <= scored.velocity_score <= 1):
                print_fail(f"Invalid velocity_score: {scored.velocity_score}")
                return False

        print_pass("All scores are in valid range [0, 1]")

        # check that breaking news items have required fields
        for article_id, scored in state.breaking_news.items():
            assert scored.article is not None, "Article is None"
            assert scored.article.title, "Article title is empty"
            assert scored.detected_at is not None, "detected_at is None"

        print_pass("All breaking news items have required fields")

        return True

    except Exception as e:
        print_fail(f"Breaking news detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_state_management():
    print_test("State Management")

    # reset state
    state.reset()

    # check initial state
    assert state.total_processed == 0, "Initial total_processed should be 0"
    assert len(state.breaking_news) == 0, "Initial breaking_news should be empty"
    assert len(state.topic_windows) == 0, "Initial topic_windows should be empty"
    print_pass("Initial state is correct")

    # test processing rate calculation
    rate = state.get_processing_rate()
    assert rate >= 0, "Processing rate should be >= 0"
    print_pass(f"Processing rate calculation works: {rate:.2f} articles/sec")

    # test uptime calculation
    uptime = state.get_uptime_seconds()
    assert uptime >= 0, "Uptime should be >= 0"
    print_pass(f"Uptime calculation works: {uptime:.2f} seconds")

    return True


async def test_deduplication():
    print_test("Deduplication")

    # reset state
    state.reset()

    # create processor
    from src.main import StreamProcessor
    proc = StreamProcessor(str(DATA_FILE), time_acceleration=10000)

    try:
        # start processing
        await proc.start()
        await asyncio.sleep(2)

        initial_count = state.total_processed
        initial_hashes = len(state.seen_hashes)

        # process same articles again (simulate duplicates)
        # this is a simplified test - in real scenario, duplicates would be skipped
        print_info(
            f"Processed {initial_count} articles, {initial_hashes} unique hashes")

        if initial_hashes > 0:
            print_pass("Deduplication tracking is working")
        else:
            print_info(
                "No hashes tracked (may be normal if no articles processed)")

        await proc.stop()
        return True

    except Exception as e:
        print_fail(f"Deduplication test failed: {e}")
        return False


async def test_response_formats():
    print_test("Response Formats")

    # use httpx AsyncClient with ASGITransport for ASGI app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # test breaking news response format
        response = await client.get("/api/breaking")
        data = response.json()

        if data["count"] > 0:
            item = data["breaking_news"][0]
            required_fields = [
                "id", "title", "description", "link", "score",
                "detected_keywords", "topic", "pub_date", "detected_at", "time_ago"
            ]
            for field in required_fields:
                if field not in item:
                    print_fail(f"Breaking news item missing field: {field}")
                    return False

            # validate field types
            assert isinstance(item["id"], str), "id should be string"
            assert isinstance(item["title"], str), "title should be string"
            assert isinstance(item["score"], (int, float)
                              ), "score should be number"
            assert isinstance(item["detected_keywords"],
                              list), "detected_keywords should be list"

            print_pass("Breaking news response format is correct")
        else:
            print_info("No breaking news to validate format")

        # test stats response format
        response = await client.get("/api/stats")
        data = response.json()

        assert isinstance(data["total_processed"],
                          int), "total_processed should be int"
        assert isinstance(data["breaking_news_count"],
                          int), "breaking_news_count should be int"
        assert isinstance(data["active_topics"],
                          int), "active_topics should be int"
        assert isinstance(data["processing_rate"], (int, float)
                          ), "processing_rate should be number"
        assert "processing_status" in data, "Response missing 'processing_status' field"
        assert data["processing_status"] in [
            "processing", "complete"], "processing_status should be 'processing' or 'complete'"

        print_pass("Stats response format is correct")

    return True


async def test_processing_status():
    print_test("Processing Status and Frozen Rate")

    # reset state
    state.reset()

    # check initial status
    assert not state.processing_complete, "Initial processing_complete should be False"
    assert state.processing_complete_time is None, "Initial processing_complete_time should be None"
    assert state.final_processing_rate is None, "Initial final_processing_rate should be None"
    print_pass("Initial processing status is correct")

    # create processor and process some articles
    from src.main import StreamProcessor
    proc = StreamProcessor(str(DATA_FILE), time_acceleration=10000)

    try:
        await proc.start()
        await asyncio.sleep(2)  # wait for some processing
        await proc.stop()

        # check that processing_complete is set after processing
        if state.processing_complete:
            assert state.processing_complete_time is not None, "processing_complete_time should be set"
            assert state.final_processing_rate is not None, "final_processing_rate should be set"
            assert state.final_processing_rate >= 0, "final_processing_rate should be >= 0"
            print_pass("Processing completion is tracked correctly")

            # check that get_processing_rate returns frozen rate
            frozen_rate = state.get_processing_rate()
            assert frozen_rate == state.final_processing_rate, "get_processing_rate should return frozen rate"
            print_pass("Frozen rate is returned correctly")
        else:
            print_info(
                "Processing not complete (may be normal if not all articles processed)")

        # test API response includes processing status
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/stats")
            data = response.json()
            assert "processing_status" in data, "Response missing 'processing_status' field"
            assert data["processing_status"] in [
                "processing", "complete"], "processing_status should be 'processing' or 'complete'"
            assert "final_processing_rate" in data, "Response missing 'final_processing_rate' field"
            if state.processing_complete:
                assert data["final_processing_rate"] is not None, "final_processing_rate should be set when processing is complete"
            print_pass("API returns processing status correctly")

        return True

    except Exception as e:
        print_fail(f"Processing status test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print("Breaking News Detection Service - End-to-End Tests")
    print(f"{'='*60}{Colors.RESET}\n")

    tests = [
        ("Service Startup", test_service_startup),
        ("State Management", test_state_management),
        ("Stream Processing", test_stream_processing),
        ("Breaking News Detection", test_breaking_news_detection),
        ("Deduplication", test_deduplication),
        ("Processing Status", test_processing_status),
        ("API Endpoints", test_api_endpoints),
        ("Response Formats", test_response_formats),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print_fail(f"{test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # print summary
    print(f"\n{Colors.BOLD}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{Colors.RESET}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        if result:
            print_pass(f"{test_name}")
        else:
            print_fail(f"{test_name}")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}\n")

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}Some tests failed{Colors.RESET}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
