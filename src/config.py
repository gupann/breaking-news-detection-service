from pathlib import Path

# paths
BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "bbc_news.csv"

# stream simulation settings
TIME_ACCELERATION = 1000
BATCH_SIZE = 10

# breaking news detection thresholds
BREAKING_SCORE_THRESHOLD = 0.50
VELOCITY_WINDOW_MINUTES = 30
VELOCITY_THRESHOLD = 3

# scoring weights
WEIGHT_KEYWORD = 0.40
WEIGHT_VELOCITY = 0.35
WEIGHT_CATEGORY = 0.15
WEIGHT_RECENCY = 0.10

# urgency keywords that indicate breaking news
URGENCY_KEYWORDS = {
    # high urgency
    "breaking", "just in", "urgent", "alert", "emergency",
    # war/conflict
    "war", "invasion", "attack", "killed", "explosion", "missile",
    "bombing", "troops", "military", "airstrike", "casualties",
    "ceasefire", "strikes", "bomb", "threats", "shooting",
    # crisis
    "crisis", "catastrophe", "disaster", "evacuate", "flee",
    "collapse", "crash", "dies", "death toll", "dead",
    # political/legal urgency
    "sanctions", "resign", "impeach", "arrest", "protest",
    "coup", "election", "vote", "verdict", "sentenced",
    "convicted", "charged", "warrant", "investigation",
}

# category priority scores (extracted from URL paths)
CATEGORY_SCORES = {
    "world": 0.9,
    "europe": 0.85,
    "politics": 0.85,
    "business": 0.7,
    "technology": 0.6,
    "health": 0.6,
    "science": 0.5,
    "entertainment": 0.3,
    "sport": 0.3,
    "arts": 0.3,
}

# default category score for unknown categories
DEFAULT_CATEGORY_SCORE = 0.5
