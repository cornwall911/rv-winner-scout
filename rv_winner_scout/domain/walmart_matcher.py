"""High-confidence product matching engine between Amazon and Walmart.

Enforces strict identity rules:
- Agreement on brand
- Agreement on model / size / spec tokens
- Detection and rejection of accessory vs main product
- Rejection when model number appears only on one side
- Price sanity range check (within 25%)
- URL normalization to bare /ip/<slug>/<id> without tracking parameters
"""

import re
from typing import Optional, Set, Tuple
from pydantic import BaseModel, Field


ACCESSORY_TOKENS = {
    "cover", "door", "mount", "mounting", "bracket", "case", "bag", "holder",
    "filter", "replacement", "adapter", "cable", "cord", "hose only", "remote only",
    "switch only", "hardware", "knob", "screw", "latch", "lock only", "gasket", "seal",
    "shroud", "blade", "motor only", "cap only"
}


class WalmartMatch(BaseModel):
    asin: str
    title: str
    walmart_item_url: str
    walmart_item_id: str
    walmart_title: str
    walmart_price: float
    amazon_price: float
    match_confidence: str = "high"
    match_reason: str
    image_url: Optional[str] = None
    score: float
    verified_at: str


class MatchDecision(BaseModel):
    is_match: bool
    confidence: str  # "high", "medium", "none"
    reason: str
    walmart_item_id: Optional[str] = None
    clean_walmart_url: Optional[str] = None


def extract_walmart_item_id(url: str) -> Optional[str]:
    """Extracts numeric item id from a Walmart /ip/ URL."""
    if not url:
        return None
    clean = url.split("?")[0]
    m = re.search(r"/ip/(?:[^/]+/)?(\d+)", clean)
    return m.group(1) if m else None


def clean_walmart_url(url: str) -> Optional[str]:
    """Normalizes Walmart URL to bare /ip/<slug>/<id> or /ip/<id> without query params."""
    if not url:
        return None
    bare = url.split("?")[0].rstrip("/")
    if not bare.startswith("http"):
        bare = "https://www.walmart.com" + bare
    return bare


def extract_brand(title: str) -> Optional[str]:
    """Heuristic extraction of brand token (leading capitalized token or known brand)."""
    words = title.strip().split()
    if not words:
        return None
    # Check leading token
    first = words[0].strip(",.:;|'\"")
    # If first token is generic number or year, look at second
    if re.match(r"^\d{4}$", first) and len(words) > 1:
        return words[1].strip(",.:;|'\"")
    return first


def extract_model_numbers(text: str) -> Set[str]:
    """Extracts explicit model numbers (e.g. 00-933066, 10-20270, Solar 1, CS-1002)."""
    # Alphanumeric with hyphens or specific letter-number sequences
    patterns = [
        r"\b\d{2}-\d{5,7}\b",           # e.g. 00-933066, 10-20270
        r"\b[A-Z]{1,4}-\d{3,6}[A-Z]?\b", # e.g. CS-1002, AV-100
        r"\b[A-Za-z]+\s*\d{1,4}[A-Za-z]?\b",  # e.g. Solar 1, 1000 Plus
    ]
    models = set()
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            token = m.group(0).strip().lower()
            # Exclude generic dimensions like 12v, 110v, 1080p, 50ft
            if not re.match(r"^\d+(?:v|w|ft|in|inch|btu|p|kw|amp|gal)$", token):
                models.add(token)
    return models


def extract_spec_tokens(text: str) -> Set[str]:
    """Extracts key measurement / capacity / size specs."""
    specs = set()
    # BTU
    for m in re.finditer(r"(\d+[\d,]*\s*btu)", text, re.IGNORECASE):
        specs.add(re.sub(r"[, ]", "", m.group(1).lower()))
    # Watts / KW
    for m in re.finditer(r"(\d+[\d\.]*\s*(?:kw|watts|w|wh))\b", text, re.IGNORECASE):
        specs.add(re.sub(r" ", "", m.group(1).lower()))
    # Length (ft / inch)
    for m in re.finditer(r"(\d+[\d\.]*\s*(?:ft|feet|inch|in|''|\"))\b", text, re.IGNORECASE):
        val = re.sub(r"['\"]", "inch", m.group(1).lower())
        specs.add(re.sub(r" ", "", val))
    # Voltage (12V, 24V, 110V)
    for m in re.finditer(r"(\d+\s*v(?:olt)?)\b", text, re.IGNORECASE):
        specs.add(re.sub(r" ", "", m.group(1).lower()))
    return specs


def is_accessory(title: str) -> Tuple[bool, Optional[str]]:
    """Checks if the title indicates an accessory, part, or replacement rather than main unit."""
    t_lower = title.lower()
    for tok in ACCESSORY_TOKENS:
        # Check whole word match
        if re.search(r"\b" + re.escape(tok) + r"\b", t_lower):
            # Check if it's not part of a main product phrase like 'refrigerator door latch' where latch is the product
            return True, tok
    return False, None


def evaluate_match(
    amazon_title: str,
    amazon_price: Optional[float],
    walmart_title: str,
    walmart_price: Optional[float],
    walmart_url: str,
) -> MatchDecision:
    """Evaluates whether Walmart candidate is a HIGH-CONFIDENCE identical match to Amazon product."""
    clean_url = clean_walmart_url(walmart_url)
    item_id = extract_walmart_item_id(walmart_url)

    if not clean_url or not item_id:
        return MatchDecision(is_match=False, confidence="none", reason="Invalid or missing Walmart item ID in URL")

    # 1. Accessory check
    amz_acc, amz_acc_tok = is_accessory(amazon_title)
    wal_acc, wal_acc_tok = is_accessory(walmart_title)

    if not amz_acc and wal_acc:
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Accessory vs main product: Walmart title contains accessory token '{wal_acc_tok}' while Amazon is main product",
        )
    if amz_acc and not wal_acc:
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Accessory vs main product: Amazon title contains accessory token '{amz_acc_tok}' while Walmart is main product",
        )

    # 2. Brand agreement
    amz_brand = extract_brand(amazon_title)
    wal_brand = extract_brand(walmart_title)

    if amz_brand and wal_brand:
        if amz_brand.lower() != wal_brand.lower():
            # Check if brand appears anywhere in the other title
            if amz_brand.lower() not in walmart_title.lower() and wal_brand.lower() not in amazon_title.lower():
                return MatchDecision(
                    is_match=False,
                    confidence="none",
                    reason=f"Brand mismatch: Amazon brand '{amz_brand}' does not match Walmart brand '{wal_brand}'",
                )

    # 3. Model number symmetry
    amz_models = extract_model_numbers(amazon_title)
    wal_models = extract_model_numbers(walmart_title)

    # If Amazon has explicit strict model (like 00-933066) but Walmart does not:
    strict_amz = {m for m in amz_models if re.search(r"\d{2,}-\d{3,}", m) or re.search(r"^[a-z]{1,4}-\d{3,}", m)}
    strict_wal = {m for m in wal_models if re.search(r"\d{2,}-\d{3,}", m) or re.search(r"^[a-z]{1,4}-\d{3,}", m)}

    if strict_amz and not strict_wal:
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Model number {list(strict_amz)[0]} present in Amazon title but missing in Walmart title",
        )
    if strict_wal and not strict_amz:
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Model number {list(strict_wal)[0]} present in Walmart title but missing in Amazon title",
        )
    if strict_amz and strict_wal:
        if not strict_amz.intersection(strict_wal):
            return MatchDecision(
                is_match=False,
                confidence="none",
                reason=f"Conflicting model numbers: {list(strict_amz)} vs {list(strict_wal)}",
            )

    # 4. Spec & Size token conflict check
    amz_specs = extract_spec_tokens(amazon_title)
    wal_specs = extract_spec_tokens(walmart_title)

    # Check for direct conflicts (e.g. 25ft vs 50ft, 55000btu vs 35000btu)
    # Check length specs (ft)
    amz_ft = {s for s in amz_specs if s.endswith("ft")}
    wal_ft = {s for s in wal_specs if s.endswith("ft")}
    if amz_ft and wal_ft and not amz_ft.intersection(wal_ft):
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Size conflict: {list(amz_ft)[0]} vs {list(wal_ft)[0]}",
        )

    # Check diameter / dimension specs (inch)
    amz_inch = {s for s in amz_specs if s.endswith("inch")}
    wal_inch = {s for s in wal_specs if s.endswith("inch")}
    if amz_inch and wal_inch and not amz_inch.intersection(wal_inch):
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Dimension conflict: {list(amz_inch)[0]} vs {list(wal_inch)[0]}",
        )

    # Check BTU specs
    amz_btu = {s for s in amz_specs if s.endswith("btu")}
    wal_btu = {s for s in wal_specs if s.endswith("btu")}
    if amz_btu and wal_btu and not amz_btu.intersection(wal_btu):
        return MatchDecision(
            is_match=False,
            confidence="none",
            reason=f"Capacity conflict: {list(amz_btu)[0]} vs {list(wal_btu)[0]}",
        )

    # 5. Price sanity check
    if amazon_price and walmart_price and amazon_price > 0 and walmart_price > 0:
        ratio = max(amazon_price, walmart_price) / min(amazon_price, walmart_price)
        if ratio > 1.35:  # Over 35% difference implies different tier/bundle
            return MatchDecision(
                is_match=False,
                confidence="none",
                reason=f"Price discrepancy outside sane range: Amazon ${amazon_price:.2f} vs Walmart ${walmart_price:.2f} (ratio {ratio:.2f})",
            )

    # 6. Overall token overlap
    orig_tokens = set(re.findall(r"\w+", amazon_title.lower()))
    cand_tokens = set(re.findall(r"\w+", walmart_title.lower()))
    stopwords = {"for", "the", "and", "with", "a", "an", "in", "on", "of", "to", "by", "is", "new", "rv", "camper"}
    meaningful_overlap = (orig_tokens - stopwords).intersection(cand_tokens - stopwords)

    if len(meaningful_overlap) < 3:
        return MatchDecision(
            is_match=False,
            confidence="medium",
            reason=f"Insufficient title overlap ({len(meaningful_overlap)} matching keywords)",
        )

    # Build match reason
    brand_str = f"same brand ({amz_brand})" if amz_brand else "compatible brand"
    spec_str = f", matching specs ({list(amz_specs.intersection(wal_specs))})" if amz_specs.intersection(wal_specs) else ""
    price_diff_pct = abs(amazon_price - walmart_price) / amazon_price * 100.0 if (amazon_price and walmart_price and amazon_price > 0) else 0.0

    return MatchDecision(
        is_match=True,
        confidence="high",
        reason=f"{brand_str}{spec_str}, price within {price_diff_pct:.1f}%",
        walmart_item_id=item_id,
        clean_walmart_url=clean_url,
    )
