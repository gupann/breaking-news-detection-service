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
