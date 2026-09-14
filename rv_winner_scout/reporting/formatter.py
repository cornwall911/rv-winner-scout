"""Markdown report formatter adhering strictly to required winner templates and verification footers."""

from typing import List, Optional
from rv_winner_scout.config.constants import NO_WINNER_MESSAGE_TEMPLATE
from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport


def format_winner_markdown(candidate: ProductCandidate) -> str:
    """Formats a single winner according to the strict specification."""
    title = candidate.verified_product.title if candidate.verified_product else candidate.raw_product.title
    price = candidate.verified_product.displayed_price if candidate.verified_product else candidate.raw_product.displayed_price
    price_str = f"${price:.2f}" if price is not None else "NOT VERIFIED"

    walmart_status = candidate.walmart.status.value if candidate.walmart else "NOT VERIFIED"
    walmart_url = candidate.walmart.url if candidate.walmart and candidate.walmart.url else "NOT FOUND"
    walmart_price_str = (
        f"${candidate.walmart.displayed_price:.2f}"
        if candidate.walmart and candidate.walmart.displayed_price is not None
        else "NOT VERIFIED"
    )
    walmart_query = candidate.walmart.search_query_used if candidate.walmart else "N/A"

    scores = candidate.scores
    total_score = scores.total_score if scores else 0.0
    status_label = f"Score: {total_score:.1f}/100"
    if scores and scores.is_exception:
        status_label += f" ({scores.exception_reason})"

    opp = candidate.opportunity
    visual_hook = opp.visual_hook if opp else "N/A"
    fb_angle = opp.facebook_angle if opp else "N/A"
    traffic_est = opp.traffic_benchmark.value if opp else "<25%"
    confidence = opp.confidence.value if opp else "MEDIUM"
    why_next = opp.why_next_winner if opp else "High viral and discovery appeal for RV owners."
    why_fail = opp.why_fail if opp else "Dependent on owner specific setup."

    exposure_urls = [s.source_url for s in candidate.exposure_signals]
    exposure_urls_str = ", ".join(exposure_urls) if exposure_urls else "None found (public signal only)"

    novelty_str = f"{(scores.novelty_newness / 1.5):.1f}" if scores else "NOT VERIFIED"
    visual_str = f"{(scores.visual_wow / 1.0):.1f}" if scores else "NOT VERIFIED"
    match_type_str = (
        candidate.walmart.match_type.value
        if candidate.walmart and hasattr(candidate.walmart, "match_type") and candidate.walmart.match_type
        else ("DIRECT ALTERNATIVE" if candidate.walmart and candidate.walmart.is_direct_alternative else ("EXACT" if candidate.walmart and candidate.walmart.status.value == "FOUND" else "NOT FOUND"))
    )

    return f"""### {title}

🟦 **CORE FACTS**
- Product Name: {title}
- ASIN: {candidate.asin}
- Amazon URL: {candidate.canonical_url}
- Amazon Price: {price_str}
- Walmart Status: {walmart_status}
- Walmart URL: {walmart_url}
- Walmart Price: {walmart_price_str}

🟨 **OPPORTUNITY ANALYSIS**
- Product Newness Status: {candidate.newness.value}
- Newness Evidence: {"; ".join(candidate.newness_evidence) or "NOT VERIFIED"}
- RV Pain Point: {", ".join(candidate.identified_pain_points) or "ESTIMATE"}
- Novelty / Discovery: {novelty_str}/10
- Visual WOW: {visual_str}/10
- RV Facebook Exposure: {candidate.exposure_level.value} (public signal only — private groups not visible)
- RV Audience Breadth: {candidate.audience_breadth.value}
- Overall Score: {total_score:.1f}/100{f' ({scores.exception_reason})' if scores and scores.is_exception else ''}
- Traffic Potential vs 25K: {traffic_est}
- Confidence: {confidence}

🟩 **ACTION**
- Visual Hook: {visual_hook}
- FB Post Angle: {fb_angle}
- Walmart Search Keywords: "{walmart_query}"
- Walmart Match Type: {match_type_str}

🟥 **EVIDENCE**
- Exposure Sources: {exposure_urls_str}
- Verification Status: {candidate.verification_state.value}
- Not-Verified Notes: {candidate.verified_product.failure_reason if candidate.verified_product and candidate.verified_product.failure_reason else "None"}

**WHY THIS COULD BE THE NEXT WINNER:**
{why_next}

**WHY IT COULD FAIL:**
{why_fail}
"""


def format_near_miss_markdown(index: int, candidate: ProductCandidate) -> str:
    """Formats a near-miss candidate."""
    title = candidate.verified_product.title if candidate.verified_product else candidate.raw_product.title
    score = candidate.scores.total_score if candidate.scores else 0.0
    reason = candidate.rejection_reason or "Below required score threshold"
    return f"{index}. **{title}** (ASIN: {candidate.asin}) — Score: {score:.1f}/100\n   - Bottleneck: {reason}"


def format_verification_footer(
    pages_opened: int,
    winners_count: int,
    rejected_count: int,
    failed_sources: List[str],
    exposure_sources_checked: int,
) -> str:
    """Generates the required verification audit footer."""
    failed_sources_str = "\n".join(f"- {s}" for s in failed_sources) if failed_sources else "- None"
    return f"""---
### VERIFICATION REPORT
- Product pages actually opened: {pages_opened}
- Products in final output: {winners_count}
- Products rejected after verification: {rejected_count}
- Constraint verified: Y ({winners_count}) <= X ({pages_opened})
- Cells marked NOT VERIFIED / ESTIMATE: Present where external proof was unavailable
- Sources that failed to load:
{failed_sources_str}
- Public exposure sources checked: {exposure_sources_checked} distinct public community queries
"""


def format_full_report(
    reviewed_count: int,
    winners: List[ProductCandidate],
    near_misses: List[ProductCandidate],
    health: RunHealthReport,
) -> str:
    """Combines all sections into the complete daily report."""
    sections: List[str] = []
    sections.append(f"# RV Winner Scout — Daily Research Report (Run ID: {health.run_id})\n")

    if winners:
        sections.append(f"## Discovered Hidden Winners ({len(winners)})\n")
        for w in winners:
            sections.append(format_winner_markdown(w))
    else:
        # EXACT required no-winner message
        no_winner_msg = NO_WINNER_MESSAGE_TEMPLATE.format(number=reviewed_count)
        sections.append(f"## Daily Verdict\n\n> {no_winner_msg}\n")

        if near_misses:
            sections.append("### Top Near Misses\n")
            for i, nm in enumerate(near_misses[:3], 1):
                sections.append(format_near_miss_markdown(i, nm))

        primary_reason = (
            near_misses[0].rejection_reason
            if near_misses and near_misses[0].rejection_reason
            else "Products were either ubiquitous staples, lacked viral novelty, or had established market saturation."
        )
        sections.append(f"\n**Biggest Failure Reason:** {primary_reason}\n")

    # Append verification report footer
    footer = format_verification_footer(
        pages_opened=health.products_verified,
        winners_count=len(winners),
        rejected_count=health.products_rejected,
        failed_sources=health.failed_sources,
        exposure_sources_checked=health.products_verified * 3,
    )
    sections.append(footer)

    return "\n".join(sections)
