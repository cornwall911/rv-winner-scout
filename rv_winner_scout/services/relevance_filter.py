"""Deterministic RV relevance filtering and hard-reject validation."""

import re
from typing import List, Optional, Tuple
from rv_winner_scout.config.constants import RV_PAIN_POINTS
from rv_winner_scout.domain.enums import NewnessStatus


# Common generic keywords that represent ubiquitous, non-novel RV staples
GENERIC_STAPLE_PATTERNS = [
    r"\btoilet paper\b",
    r"\bwheel chock\b",
    r"\bleveling block\b",
    r"\bstandard sewer hose\b",
    r"\bdogbone adapter\b",
    r"\bstandard extension cord\b",
    r"\bdrinking water hose\b",
    r"\brv cover\b",
    r"\broof sealant\b",
    r"\bdicor\b",
    r"\breplacement fuse\b",
    r"\bcamco 40043\b",
    r"\blug nut\b",
    r"\blight bulb replacement\b",
]

# Ultra-niche replacement parts that lack broad audience discovery
ULTRA_NICHE_REPLACEMENT_PATTERNS = [
    r"\breplacement gasket for\b",
    r"\bcarburetor rebuild kit\b",
    r"\bwater heater heating element\b",
    r"\brv furnace control board\b",
    r"\bcircuit board replacement\b",
    r"\bmotor brush replacement\b",
    r"\bo-ring kit for\b",
]


class RelevanceFilter:
    """Evaluates product suitability, screens against hard rejects, and links to RV pain points."""

    @classmethod
    def identify_pain_points(cls, title: str, bullet_points: List[str]) -> List[str]:
        """Maps product content naturally against the 18 defined RV pain points.

        Does NOT force an RV use case if no genuine relevance exists.
        """
        combined = f"{title} {' '.join(bullet_points)}".lower()
        matched: List[str] = []

        for point in RV_PAIN_POINTS:
            # Check for direct or conceptual keyword presence
            words = point.split()
            if all(word in combined for word in words):
                matched.append(point)
            elif point == "limited space" and any(k in combined for k in ["space saving", "compact", "collapsible", "foldable", "tight space"]):
                matched.append(point)
            elif point == "storage" and any(k in combined for k in ["organizer", "rack", "pocket", "compartment"]):
                matched.append(point)
            elif point == "power" and any(k in combined for k in ["battery", "solar", "inverter", "12v", "generator", "amp"]):
                matched.append(point)
            elif point == "condensation" and any(k in combined for k in ["dehumidifier", "moisture", "damp", "mold"]):
                matched.append(point)
            elif point == "setup" and any(k in combined for k in ["quick install", "easy setup", "no drill", "plug and play"]):
                matched.append(point)

        return sorted(list(set(matched)))

    @classmethod
    def check_hard_reject(cls, title: str, bullet_points: List[str]) -> Tuple[bool, Optional[str]]:
        """Evaluates whether a product triggers mandatory hard reject criteria.

        Returns (is_rejected, rejection_reason).
        """
        combined = f"{title} {' '.join(bullet_points)}".lower()

        # 1. Common staples that every RV owner already knows
        for pat in GENERIC_STAPLE_PATTERNS:
            if re.search(pat, combined):
                return True, f"Hard reject: Ubiquitous generic RV staple ({pat})"

        # 2. Ultra-niche replacement mechanical parts
        for pat in ULTRA_NICHE_REPLACEMENT_PATTERNS:
            if re.search(pat, combined):
                return True, f"Hard reject: Ultra-niche replacement mechanical part ({pat})"

        # 3. Completely non-RV items accidentally listed in category
        rv_indicators = [
            "rv", "camper", "trailer", "motorhome", "fifth wheel", "5th wheel",
            "caravan", "van life", "boondocking", "camping", "towing"
        ]
        has_rv_mention = any(ind in combined for ind in rv_indicators)
        # If title doesn't mention RV and bullets don't mention RV/towing, reject
        if not has_rv_mention:
            return True, "Hard reject: No genuine RV relevance or camper application detected"

        return False, None

    @classmethod
    def evaluate_newness_evidence(cls, evidence_strings: List[str]) -> Tuple[NewnessStatus, List[str]]:
        """Classifies newness status based strictly on verifiable evidence.

        Never fabricates dates. If no evidence exists, status must be NOT VERIFIED.
        """
        if not evidence_strings:
            return NewnessStatus.NOT_VERIFIED, []

        verified_evidence: List[str] = []
        for ev in evidence_strings:
            verified_evidence.append(ev)

        # Amazon New Releases alone is NOT proof of newness, but 'Date First Available' is valid evidence
        for ev in evidence_strings:
            ev_lower = ev.lower()
            if "date first available" in ev_lower:
                # If available within recent year (e.g. 2025/2026)
                if any(yr in ev_lower for yr in ["2026", "2025"]):
                    return NewnessStatus.NEW, verified_evidence
                elif any(yr in ev_lower for yr in ["2024"]):
                    return NewnessStatus.EMERGING, verified_evidence
                else:
                    return NewnessStatus.ESTABLISHED, verified_evidence

        return NewnessStatus.NOT_VERIFIED, verified_evidence
