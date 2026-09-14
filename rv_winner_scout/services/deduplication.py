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


class DeduplicationService:
    """Tracks seen canonical URLs, ASINs, and title hashes within and across runs."""

    def __init__(self, existing_asins: Optional[Set[str]] = None) -> None:
        self.seen_urls: Set[str] = set()
        self.seen_asins: Set[str] = set(existing_asins or [])
        self.seen_title_hashes: Set[str] = set()

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

    def register(self, url: str, title: str) -> None:
        """Registers the product identifiers into the deduplication registry."""
        canonical_url = canonicalize_amazon_url(url)
        asin = extract_asin(canonical_url)
        title_hash = compute_title_hash(title)

        self.seen_urls.add(canonical_url)
        if asin:
            self.seen_asins.add(asin)
        self.seen_title_hashes.add(title_hash)
