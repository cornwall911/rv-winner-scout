"""Deduplication service enforcing Canonical URL as primary and ASIN/Title-hash as supporting."""

import hashlib
import re
from typing import Optional, Set
from rv_winner_scout.adapters.amazon.category_crawler import canonicalize_amazon_url, extract_asin


def normalize_title(title: str) -> str:
    """Normalizes product title by stripping non-alphanumerics, spaces, and lowercase conversion."""
    cleaned = re.sub(r"[^\w\s]", "", title.lower())
    return " ".join(cleaned.split())


def compute_title_hash(title: str) -> str:
    """Computes a sha256 fingerprint of the normalized title."""
    return hashlib.sha256(normalize_title(title).encode("utf-8")).hexdigest()[:16]


def normalize_concept_tokens(title: str) -> Set[str]:
    """Extracts essential functional keyword stems from a product title for concept deduplication."""
    t = title.lower()
    # Strip specs, dimensions, units, voltages, wattages, etc.
    t = re.sub(r"\b\d+(\.\d+)?\s*(in|inch|\"|p|k|w|v|gpm|amp|ah|gal|lb|lbs|oz|ft|mm|cm|m)\b", " ", t)
    t = re.sub(r"\b\d{2,5}\b", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)

    stopwords = {
        "for", "and", "with", "the", "in", "to", "a", "an", "of", "on", "by", "from",
        "direct", "easy", "free", "kit", "replacement", "upgrade", "new", "pack",
        "universal", "heavy", "duty", "pro", "ultra", "premium", "high", "quality",
        "rv", "camper", "trailer", "motorhome", "travel", "car", "truck", "auto",
        "set", "piece", "pieces", "black", "white", "portable",
    }

    tokens: Set[str] = set()
    for w in t.split():
        if len(w) > 2 and w not in stopwords:
            # Simple stemming for English plurals
            if w.endswith("ies"):
                w = w[:-3] + "y"
            elif w.endswith("es") and not w.endswith("ses"):
                w = w[:-2]
            elif w.endswith("s") and not w.endswith("ss"):
                w = w[:-1]
            tokens.add(w)
    return tokens


# Known concept anchors where two products sharing both words are functionally identical concepts
CONCEPT_ANCHORS = [
    {"backup", "camera"},
    {"rear", "camera"},
    {"reversing", "camera"},
    {"air", "cooler"},
    {"evaporative", "cooler"},
    {"air", "conditioner"},
    {"ceiling", "fan"},
    {"socket", "fan"},
    {"sleeper", "sofa"},
    {"sofa", "bed"},
    {"ice", "maker"},
    {"washing", "machine"},
    {"water", "dispenser"},
    {"knife", "holder"},
    {"knife", "magnetic"},
    {"outdoor", "griddle"},
    {"tabletop", "griddle"},
    {"movie", "projector"},
    {"electric", "skillet"},
    {"awning", "screen"},
    {"awning", "shade"},
    {"drawer", "organizer"},
    {"storage", "tent"},
    {"bike", "tent"},
    {"soft", "start"},
    {"inrush", "limiter"},
    {"propane", "detector"},
    {"gas", "detector"},
    {"skylight", "insulator"},
    {"cassette", "toilet"},
    {"shower", "head"},
    {"macerator", "pump"},
    {"tank", "sensor"},
    {"power", "station"},
    {"surge", "protector"},
]


def are_same_concept(title_a: str, title_b: str) -> bool:
    """Determines whether two product titles represent the exact same functional concept / product idea.

    Used to enforce the rule: 'If it's the same product idea across different brands, include only one.'
    """
    tokens_a = normalize_concept_tokens(title_a)
    tokens_b = normalize_concept_tokens(title_b)

    if not tokens_a or not tokens_b:
        return False

    # 1. Exact or near-exact anchor concept match
    for anchor in CONCEPT_ANCHORS:
        if anchor.issubset(tokens_a) and anchor.issubset(tokens_b):
            return True

    # 2. Token overlap similarity (Jaccard on minimum set)
    overlap = tokens_a.intersection(tokens_b)
    min_len = min(len(tokens_a), len(tokens_b))
    if min_len > 0:
        overlap_ratio = len(overlap) / min_len
        # If at least 60% of significant functional keywords match and at least 2 tokens overlap
        if overlap_ratio >= 0.60 and len(overlap) >= 2:
            return True

    return False


class DeduplicationService:
    """Tracks seen canonical URLs, ASINs, title hashes, and concept clusters within and across runs."""

    def __init__(self, existing_asins: Optional[Set[str]] = None) -> None:
        self.seen_urls: Set[str] = set()
        self.seen_asins: Set[str] = set(existing_asins or [])
        self.seen_title_hashes: Set[str] = set()
        self.registered_titles: List[str] = []

    def is_duplicate(self, url: str, title: str) -> bool:
        """Determines if a product has already been encountered in this run or previously."""
        canonical_url = canonicalize_amazon_url(url)
        asin = extract_asin(canonical_url)
        title_hash = compute_title_hash(title)

        # 1. Primary deduplication by canonical URL
        if canonical_url in self.seen_urls:
            return True

        # 2. Supporting deduplication by ASIN
        if asin and asin in self.seen_asins:
            return True

        # 3. Supporting deduplication by normalized title hash
        if title_hash in self.seen_title_hashes:
            return True

        return False

    def is_concept_duplicate(self, title: str) -> bool:
        """Checks if a functionally identical concept has already been registered."""
        for registered in self.registered_titles:
            if are_same_concept(title, registered):
                return True
        return False

    def register(self, url: str, title: str) -> None:
        """Registers the product identifiers into the deduplication registry."""
        canonical_url = canonicalize_amazon_url(url)
        asin = extract_asin(canonical_url)
        title_hash = compute_title_hash(title)

        self.seen_urls.add(canonical_url)
        if asin:
            self.seen_asins.add(asin)
        self.seen_title_hashes.add(title_hash)
        self.registered_titles.append(title)

