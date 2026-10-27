

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

MIN_WORKERS = 1
MAX_WORKERS = 3

SCALE_UP_THRESHOLD = 3
SCALE_DOWN_THRESHOLD = 1

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
