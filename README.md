# Breaking News Detection Service

A real-time backend service that processes a continuous stream of news notifications and automatically identifies which articles qualify as "breaking news" based on multiple signals.

## Overview

This service simulates processing a real-time news stream by reading from a CSV dataset (bbc_news.csv) and analyzing each article to determine if it should be classified as breaking news. The system uses a multi-signal scoring approach that considers keyword urgency, article velocity (how quickly similar articles appear), category importance, and recency.

The service exposes a REST API and a web dashboard where you can view currently active breaking news articles, filter by topic, and see system statistics.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python3 -m uvicorn src.main:app --reload

# Open the dashboard in your browser
# http://localhost:8000
```

## Features

- Real-time news stream processing with time-accelerated simulation
- Multi-signal breaking news detection using keyword analysis, velocity tracking, category scoring, and recency
- Automatic deduplication to prevent processing the same article multiple times
- Topic extraction and clustering to identify related articles
- RESTful API with endpoints for breaking news, statistics, topics, and health checks
- Web dashboard for viewing breaking news in real-time
- State management with automatic cleanup of expired breaking news
- Optional Redis integration for distributed state management and persistence
- Processing status tracking with frozen rate calculation after completion

## Assumptions

1. **Breaking News Definition**: An article qualifies as breaking news if it has a total score of 0.50 or higher, calculated from multiple weighted signals.

2. **Time Window**: The system processes one week of data from the dataset (November 27 to December 4, 2024). Articles outside this range are filtered out.

3. **Stream Simulation**: Historical data is processed with time acceleration (1000x) to simulate a real-time stream. Each article is processed according to its original publication timestamp, but time passes faster in the simulation.

4. **Breaking News Expiration**: Breaking news articles expire after 6 hours from detection time. Expired articles are automatically removed from the active list.

5. **Velocity Window**: Articles are grouped by topic within a 30-minute sliding window to calculate velocity scores. If 3 or more articles on the same topic appear within this window, it increases the velocity score.

6. **Deduplication**: Articles with identical titles are considered duplicates and skipped. This prevents the same article from being processed multiple times.

7. **Topic Extraction**: Topics are extracted from article titles using keyword matching. The system looks for major topics (like "ukraine", "covid", "israel") and falls back to the first significant word if no major topic is found.

8. **Category Priority**: Different news categories have different priority scores. World news, Europe, and Politics have higher scores (0.85-0.90) than Entertainment or Sports (0.30).

## Design Decisions

### Architecture

The service is built using Python with FastAPI for the REST API and web server. The architecture is modular with separate components for:

- **Stream Processing**: Handles reading the CSV file, parsing articles, and simulating real-time processing
- **Scoring System**: Calculates multiple scores (keyword, velocity, category, recency) and combines them into a total score
- **State Management**: Tracks breaking news articles, seen hashes, topic windows, and system statistics
- **API Layer**: Exposes REST endpoints organized by functionality (breaking, stats, topics, health)
- **Web Dashboard**: Client-side JavaScript application that polls the API and displays breaking news

### Breaking News Detection

The system uses a weighted scoring approach with four signals:

1. **Keyword Score (40% weight)**: Analyzes article titles for urgency keywords like "breaking", "urgent", "attack", "crisis", etc. The more urgency keywords found, the higher the score.

2. **Velocity Score (35% weight)**: Tracks how quickly articles on the same topic appear. If multiple articles on a topic appear within a 30-minute window, the velocity score increases.

3. **Category Score (15% weight)**: Assigns priority scores based on the article category. World news and politics get higher scores than entertainment.

4. **Recency Score (10% weight)**: Newer articles get higher scores. Articles published within the last hour score highest, with scores decreasing over time.

The total score is calculated as: `total = (keyword * 0.40) + (velocity * 0.35) + (category * 0.15) + (recency * 0.10)`

Articles with a total score >= 0.50 are classified as breaking news.

### Example Scoring

Here's how a real article would be scored:

```
Article: "Ukraine: Urgent evacuations as Russian missiles strike Kyiv"

Keyword Score:    0.90  (detected: "urgent", "strike", "missiles")
Velocity Score:   0.70  (5 Ukraine articles in last 30 minutes)
Category Score:   0.85  (world news category)
Recency Score:    1.00  (published less than 1 hour ago)

Total = (0.90 × 0.40) + (0.70 × 0.35) + (0.85 × 0.15) + (1.00 × 0.10)
      = 0.36 + 0.245 + 0.1275 + 0.10
      = 0.8325

Result: 0.8325 >= 0.50 threshold → BREAKING NEWS ✓
```

### State Management

The service supports two state management modes:

1. **In-Memory (Default)**: Fast and simple, suitable for single-instance deployments. State is lost on restart. This approach:
   - Eliminates external dependencies
   - Simplifies local development
   - Is sufficient for single-process deployment

2. **Redis (Optional)**: Distributed state management that persists across restarts. Enable by setting the `REDIS_URL` environment variable. This allows multiple service instances to share state and provides persistence.

State includes:
- Active breaking news articles (dictionary keyed by article ID)
- Seen content hashes (set for deduplication)
- Topic windows (sliding windows of article timestamps per topic)
- System statistics (total processed, processing rate, uptime)

### Topic Extraction

Topic extraction uses keyword matching against known major topics (like "ukraine", "covid", "israel"), falling back to the first significant word if no major topic is found. This approach is intentionally simple and works well for the current use case.

**Production consideration**: For better accuracy, use Named Entity Recognition (NER) to extract entities and topics from article content, or implement topic clustering algorithms.

### Deduplication

Articles are deduplicated using MD5 hashes of normalized titles (lowercase, trimmed). This catches exact duplicates effectively and prevents the same article from being processed multiple times.

**Production consideration**: For detecting near-duplicates or semantically similar articles, use SimHash or MinHash algorithms which can detect similar content even with slight variations.

### Time-Simulated Stream

The CSV data is processed chronologically with configurable time acceleration:
- 1000x speed: One week of data processes in approximately 1-2 minutes
- Realistic timing between articles is preserved (scaled down)
- Enables testing of time-based features like velocity detection and recency scoring

This approach allows testing real-time behavior using historical data without waiting for actual real-time events.

### Scalability Considerations

This implementation is designed for simplicity and works well for the current scale. Here are the current approaches and production alternatives:

| Current (MVP) | Production Scale |
|---------------|------------------|
| In-memory dict | Redis Cluster |
| Single process | Multiple workers |
| Polling API | WebSocket/SSE |
| Simple keywords | ML classifier |
| Keyword topics | NER + clustering |
| MD5 hashing | SimHash/MinHash |

**Current capabilities:**
- **Asynchronous Processing**: Uses Python asyncio for non-blocking I/O, allowing the service to handle multiple requests while processing articles.
- **Efficient Data Structures**: Uses dictionaries and sets for O(1) lookups. Topic windows use time-ordered data structures for efficient range queries.
- **Automatic Cleanup**: Periodic cleanup tasks remove expired breaking news and old topic window entries to prevent memory growth.
- **Redis Support**: For production deployments, Redis enables horizontal scaling across multiple service instances.
- **Batch Processing**: Articles are processed in batches to balance throughput and responsiveness.

**When to consider stream processing frameworks:**

This codebase processes approximately 0.01 events per second. For much larger scale, consider frameworks like Apache Flink when you need:
- 1K+ events per second
- Complex windowing with exactly-once semantics
- Multi-stream joins (combining news + social media + user signals)
- Distributed state management across clusters

### API Design

The API follows RESTful principles with clear endpoint naming:

- `GET /api/breaking` - List all active breaking news (optional topic filter)
- `GET /api/stats` - System statistics and processing metrics
- `GET /api/topics` - List of active topics with article counts
- `GET /api/health` - Health check endpoint

All endpoints return JSON responses with consistent error handling.

## How to Run

### Prerequisites

- Python 3.10 or higher
- pip package manager
- (Optional) Redis server for distributed state

### Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure the `bbc_news.csv` file is in the project root directory

### Running the Service

**Basic mode (in-memory state):**
```bash
python3 -m uvicorn src.main:app --reload
```

The service will start on `http://localhost:8000`

You should see output like this:
```
Stream processor started
Loading data from /path/to/bbc_news.csv
Loaded 42115 articles
Processing week: 2024-11-27 to 2024-12-04
257 articles in time range
INFO:     Uvicorn running on http://127.0.0.1:8000
Processed 10 articles | Breaking: 0 | Latest: The Israel-Hezbollah Ceasefire
Processed 20 articles | Breaking: 1 | Latest: Israel to appeal against ICC warrants
...
Stream processing complete. Total: 249 articles
```

**With Redis (for distributed state):**
```bash
# Start Redis server first (if not already running)
redis-server

# Run the service with Redis
REDIS_URL=redis://localhost:6379 python3 -m uvicorn src.main:app --reload
```

### Accessing the Dashboard

Once the service is running, open your browser and navigate to:
```
http://localhost:8000
```

The dashboard will automatically load and display breaking news articles as they are detected. The page refreshes every 30 seconds to show the latest breaking news.

### API Usage

You can also interact with the service directly via the REST API:

**Get all breaking news:**
```bash
curl http://localhost:8000/api/breaking
```

**Response example:**
```json
{
  "count": 3,
  "breaking_news": [
    {
      "id": "abc123",
      "title": "Ukraine: Major offensive launched in eastern region",
      "description": "Ukrainian forces have launched...",
      "link": "https://www.bbc.com/news/...",
      "category": "world",
      "score": 0.85,
      "detected_keywords": ["offensive", "launched"],
      "topic": "ukraine",
      "pub_date": "2024-11-27T10:00:00Z",
      "detected_at": "2024-11-27T10:05:00Z",
      "time_ago": "5m ago"
    }
  ]
}
```

**Get breaking news for a specific topic:**
```bash
curl http://localhost:8000/api/breaking?topic=ukraine
```

**Get system statistics:**
```bash
curl http://localhost:8000/api/stats
```

**Response example:**
```json
{
  "total_processed": 249,
  "breaking_news_count": 3,
  "active_topics": 8,
  "processing_rate": 42.5,
  "processing_status": "complete",
  "final_processing_rate": 42.5,
  "simulation_time": "2024-12-04T23:59:59Z",
  "real_start_time": "2024-12-15T10:00:00Z",
  "uptime_seconds": 1800
}
```

**Get active topics:**
```bash
curl http://localhost:8000/api/topics
```

**Response example:**
```json
{
  "count": 5,
  "topics": [
    {"topic": "ukraine", "article_count": 12},
    {"topic": "israel", "article_count": 8},
    {"topic": "covid", "article_count": 5}
  ]
}
```

**Health check:**
```bash
curl http://localhost:8000/api/health
```

**Response example:**
```json
{
  "status": "healthy",
  "processor_running": true,
  "state_store": "in-memory",
  "redis_url": null,
  "timestamp": "2024-12-15T10:30:00Z"
}
```

## Testing

The project includes comprehensive test suites to verify functionality.

### End-to-End Tests

Run the full test suite:
```bash
python3 test_e2e.py
```

This tests:
- Service startup and initialization
- State management operations
- Stream processing and article ingestion
- Breaking news detection logic
- Deduplication functionality
- Processing status tracking
- All API endpoints
- Response format validation

### Redis Tests

If you have Redis running, test the Redis integration:
```bash
python3 test_redis.py
```

This verifies:
- Redis connection
- State store operations with Redis
- State persistence across restarts

## Project Structure

```
breaking-news-detection-service/
├── bbc_news.csv              # Dataset file
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── test_e2e.py              # End-to-end test suite
├── test_redis.py            # Redis integration tests
├── src/
│   ├── __init__.py
│   ├── main.py              # Main application and stream processor
│   ├── config.py            # Configuration settings
│   ├── models.py            # Pydantic data models
│   ├── state.py             # In-memory state store
│   ├── state_redis.py       # Redis state store implementation
│   ├── scoring.py           # Breaking news scoring logic
│   └── api/                 # API endpoints
│       ├── __init__.py
│       ├── routes.py        # API router configuration
│       ├── breaking.py      # Breaking news endpoint
│       ├── stats.py         # Statistics endpoint
│       ├── topics.py        # Topics endpoint
│       ├── health.py        # Health check endpoint
│       └── utils.py         # API utility functions
└── static/                  # Web dashboard files
    ├── index.html          # Dashboard HTML
    ├── css/                # Stylesheets
    ├── js/                 # JavaScript files
    └── images/             # Images and assets
```

## Configuration

Key configuration options can be modified in `src/config.py`:

- `BREAKING_SCORE_THRESHOLD`: Minimum score to qualify as breaking news (default: 0.50)
- `VELOCITY_WINDOW_MINUTES`: Time window for velocity calculation (default: 30 minutes)
- `VELOCITY_THRESHOLD`: Minimum articles needed for velocity detection (default: 3)
- `BREAKING_NEWS_TTL_HOURS`: How long breaking news stays active (default: 6 hours)
- `TIME_ACCELERATION`: Speed multiplier for stream simulation (default: 1000x)
- Scoring weights: Adjust the importance of each signal (keyword, velocity, category, recency)

## Dependencies

Main dependencies used in this project:

- **FastAPI** - Modern web framework for building REST APIs
- **Uvicorn** - ASGI server for running the FastAPI application
- **Pandas** - Data processing library for reading and parsing CSV files
- **python-dateutil** - Date parsing utilities
- **Pydantic** - Data validation and serialization
- **Redis** (optional) - Distributed state management and persistence

## Notes

- The service processes articles in chronological order based on their publication timestamps
- Breaking news articles are automatically removed after 6 hours
- The dashboard updates every 30 seconds to show the latest breaking news
- Processing status shows "processing" while articles are being ingested, then switches to "complete" with a frozen rate
- Topic filtering allows you to view breaking news for specific topics like "ukraine", "covid", "israel", etc.