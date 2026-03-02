"""Pipeline configuration: paths, city, thresholds. All from env with sensible defaults."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root (parent of pipeline/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Target city for filtering (Philadelphia: largest in Yelp Open Dataset; Austin not present)
TARGET_CITY: str = os.getenv("TARGET_CITY", "Philadelphia")

# Yelp JSON location: "Yelp JSON/yelp_dataset" or "data/raw" (must contain the academic JSON files)
YELP_DATA_PATH: Path = PROJECT_ROOT / os.getenv("YELP_DATA_PATH", "Yelp JSON/yelp_dataset").strip()

# Output directories
DATA_PROCESSED: Path = PROJECT_ROOT / "data" / "processed"
DATA_NEO4J_IMPORT: Path = PROJECT_ROOT / "data" / "neo4j-import"
DATA_DEMO: Path = PROJECT_ROOT / "data" / "demo"

# Yelp dataset filenames (relative to YELP_DATA_PATH)
BUSINESS_FILE = "yelp_academic_dataset_business.json"
REVIEW_FILE = "yelp_academic_dataset_review.json"
USER_FILE = "yelp_academic_dataset_user.json"

# Network thresholds (build plan)
MIN_SHARED_REVIEWERS: int = int(os.getenv("MIN_SHARED_REVIEWERS", "3"))
MIN_SHARED_RESTAURANTS: int = int(os.getenv("MIN_SHARED_RESTAURANTS", "5"))

# Restaurant/food category pattern (EDA-validated)
RESTAURANT_CATEGORY_PATTERN = "Restaurant|Food|Bar|Cafe|Coffee"

# Neo4j (Phase 2+)
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")


def ensure_dirs() -> None:
    """Create data output directories if they do not exist."""
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DATA_NEO4J_IMPORT.mkdir(parents=True, exist_ok=True)
    DATA_DEMO.mkdir(parents=True, exist_ok=True)
