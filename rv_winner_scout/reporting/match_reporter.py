"""Persistence and status reporter for verified Walmart matches and run telemetry."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_public_dir() -> Path:
    """Returns the base public directory."""
    # Look for public directory relative to repo root
    current = Path(__file__).resolve()
    # current: rv_winner_scout/reporting/match_reporter.py -> parent x 3 is repo root
    repo_root = current.parent.parent.parent
    pub = repo_root / "public"
    pub.mkdir(parents=True, exist_ok=True)
    return pub


def load_walmart_matches(filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Loads existing verified Walmart matches."""
    path = filepath or (get_public_dir() / "walmart_matches.json")
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("Could not load walmart_matches.json from %s: %s", path, e)
        return []


def merge_walmart_matches(
    existing: List[Dict[str, Any]],
    new_matches: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Merges new matches into existing list, deduplicating by walmart_item_id and asin."""
    # Index by walmart_item_id and asin
    by_item_id: Dict[str, Dict[str, Any]] = {}
    
    for item in existing:
        wid = str(item.get("walmart_item_id", "")).strip()
        if wid:
            by_item_id[wid] = item

    for item in new_matches:
        wid = str(item.get("walmart_item_id", "")).strip()
        if not wid:
            continue
        # Overwrite or add with updated metrics
        by_item_id[wid] = item

    # Sort descending by score
    merged = list(by_item_id.values())
    merged.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    return merged


def save_walmart_matches(
    matches: List[Dict[str, Any]],
    filepath: Optional[Path] = None
) -> Path:
    """Saves Walmart matches to public/walmart_matches.json."""
    path = filepath or (get_public_dir() / "walmart_matches.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d verified Walmart matches to %s", len(matches), path)
    return path


def save_run_status(
    started_at: str,
    finished_at: str,
    amazon_ok: bool,
    amazon_seen: int,
    amazon_error: Optional[str],
    walmart_ok: bool,
    walmart_blocked: bool,
    walmart_searched: int,
    walmart_matched_high: int,
    walmart_no_match: int,
    walmart_error: Optional[str],
    errors: List[str],
    filepath: Optional[Path] = None
) -> Path:
    """Writes public/run_status.json complying with Contract B."""
    path = filepath or (get_public_dir() / "run_status.json")
    path.parent.mkdir(parents=True, exist_ok=True)

    status_data = {
        "started_at": started_at,
        "finished_at": finished_at,
        "amazon": {
            "ok": amazon_ok,
            "products_seen": amazon_seen,
            "error": amazon_error
        },
        "walmart": {
            "ok": walmart_ok,
            "blocked": walmart_blocked,
            "searched": walmart_searched,
            "matched_high": walmart_matched_high,
            "no_match": walmart_no_match,
            "error": walmart_error
        },
        "errors": errors
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)
    logger.info("Recorded run status in %s: walmart blocked=%s", path, walmart_blocked)
    return path
