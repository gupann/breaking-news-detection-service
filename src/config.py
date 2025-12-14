from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "bbc_news.csv"

TIME_ACCELERATION = 1000
BATCH_SIZE = 10
