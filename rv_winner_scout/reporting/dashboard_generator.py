"""Generates a high-productivity, themeable Executive E-Commerce Dashboard."""

import html
import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport
from rv_winner_scout.domain.scoring import compute_heuristic_scores
from rv_winner_scout.services.archetype_learning import ArchetypeMatcher


def generate_humanized_angles(cand: ProductCandidate) -> List[Tuple[str, str]]:
    """Generates 3 humanized, high-converting RV marketing angles with relatable hooks and examples."""
    opp = cand.opportunity
    title = ""
    if cand.verified_product and cand.verified_product.title and cand.verified_product.title.strip().lower() != "unknown":
        title = cand.verified_product.title.strip()
    elif cand.raw_product and cand.raw_product.title and cand.raw_product.title.strip().lower() != "unknown":
        title = cand.raw_product.title.strip()
    else:
        title = (cand.normalized_title or cand.asin).strip()

    short_title = title.split("-")[0].split("|")[0].split(",")[0].strip()
    if len(short_title) > 40:
        short_title = short_title[:37] + "..."

    # If explicit marketing angles were supplied, use them
    if opp and opp.marketing_angles and len(opp.marketing_angles) >= 3:
        return [
            ("🗣️ Angle 1 (Campground Reality)", opp.marketing_angles[0]),
            ("💡 Angle 2 (Practical RV Fix)", opp.marketing_angles[1]),
            ("🚀 Angle 3 (Travel Peace of Mind)", opp.marketing_angles[2]),
        ]

    base_angle = opp.facebook_angle if opp and opp.facebook_angle else ""
    pain_points = cand.identified_pain_points or []
    primary_pain = pain_points[0] if pain_points else "campground setup & daily maintenance"

    # Angle 1: Campground Reality (Relatable Frustration & Storytelling)
    if base_angle and len(base_angle) > 20:
        clean_angle = base_angle.replace("Target RV travelers & campers experiencing this exact issue.", "").strip()
        if clean_angle:
            angle_1 = f"Nothing ruins a peaceful campground evening faster than dealing with {primary_pain}: {clean_angle.rstrip('.')}. This is the exact upgrade you need before your next trip."
        else:
            angle_1 = f"Nothing ruins a campground weekend faster than dealing with unexpected {primary_pain}. Most RVers don't realize this fix exists until they're wrestling with it at 9 PM in the dark."
    else:
        angle_1 = f"Nothing ruins a campground weekend faster than dealing with unexpected {primary_pain}. Most RVers don't realize this fix exists until they're wrestling with it at 9 PM in the dark."

    # Angle 2: Practical Problem Solver (Direct DIY & Save Money)
    angle_2 = f"Skip the crazy dealership markups and $150/hr RV mechanic fees. This {short_title} takes 5 minutes to install yourself and permanently eliminates {primary_pain} headaches on the road."

    # Angle 3: Off-Grid / Weekend Freedom (Lifestyle & Peace of Mind)
    angle_3 = f"The difference between a stressful RV trip and genuine camping freedom comes down to having the right setup. Don't hit the road or boondock without {short_title} in your storage bay."

    return [
        ("🗣️ Angle 1 (Campground Reality)", angle_1),
        ("💡 Angle 2 (Practical RV Fix)", angle_2),
        ("🚀 Angle 3 (Travel Peace of Mind)", angle_3),
    ]


def get_why_converts_and_risk(cand: ProductCandidate) -> Tuple[str, str]:
    """Generates unique, product-specific conversion rationale and bottlenecks, eliminating generic repeating copy."""
    opp = cand.opportunity
    title = (cand.verified_product.title if cand.verified_product else cand.raw_product.title) or ""
    title_lower = title.lower()

    # If AI gave a unique rationale, use it
    if opp and opp.why_next_winner and "High organic demand & natural RV utility" not in opp.why_next_winner:
        return opp.why_next_winner, (opp.why_fail or "Specific vehicle fit & installation requirements.")

    # Dynamically craft product-specific conversion rationale from keywords and pain points
    if any(k in title_lower for k in ["wall mounted", "ductless", "portable 2-in-1", "air conditioner", "ac unit"]):
        why = "Windowless and ductless 2-in-1 cooling & heating without cutting RV roofs or losing window space; viral high-ticket game changer for camper vans & travel trailers."
        risk = "Draws up to 1800W, requiring 30A shore hookup, a 2000W+ inverter generator, or a substantial lithium battery bank."
    elif any(k in title_lower for k in ["soft start", "inrush", "starter"]):
        why = "Cuts compressor startup inrush current by up to 75%, allowing full rooftop AC operation on small 2000W generators during off-grid boondocking."
        risk = "Requires basic DIY electrical wiring inside the rooftop air conditioner shroud."
    elif any(k in title_lower for k in ["leveling", "level", "chock", "ramp"]):
        why = "Eliminates dangerous wobble and unlevel sleeping inside campers with interlocking rapid drive-on design."
        risk = "Requires dedicated storage bay space and ground clearance checks."
    elif any(k in title_lower for k in ["water", "pressure", "filter", "hose", "leak"]):
        why = "Protects delicate RV PEX plumbing from high-pressure campground blowouts and costly interior water damage."
        risk = "Needs standard brass hose thread compatibility and freeze-season winterizing."
    elif any(k in title_lower for k in ["sewer", "macerator", "waste", "drain"]):
        why = "Eliminates the messiest, most dreaded RV chore with clean, leak-proof rapid dump flow."
        risk = "Requires standard bayonet fittings and proper hose slope."
    elif any(k in title_lower for k in ["solar", "battery", "inverter", "power", "charger"]):
        why = "Enables true boondocking independence by keeping 12V house systems and electronics charged off-grid."
        risk = "Requires matching amp-hour capacity and proper fuse ratings."
    else:
        clean_name = title.split("-")[0].split("|")[0].split(",")[0].strip()
        why = f"Directly solves RV travel headaches with compact '{clean_name[:40]}' utility tailored for camper life."
        risk = "Requires verifying RV model specifications and mounting space before install."

    return why, risk


def generate_executive_dashboard_html(
    reviewed_count: int,
    winners: List[ProductCandidate],
    near_misses: List[ProductCandidate],
    health: RunHealthReport,
    spreadsheet_id: Optional[str] = None,
    candidates: Optional[List[ProductCandidate]] = None,
    should_be_tested: Optional[List[ProductCandidate]] = None,
) -> str:
    """Renders a clean, eye-friendly, theme-switchable dashboard with humanized marketing angles & arbitrage."""
    run_date = health.end_time.strftime("%Y-%m-%d")

    winner_asins = {w.asin for w in winners}
    should_test_asins = {st.asin for st in (should_be_tested or [])}

    all_input = winners + near_misses + (candidates or []) + (should_be_tested or [])
    seen_asins = set()
    deduped_candidates = []
    for c in all_input:
        if c.asin not in seen_asins:
            seen_asins.add(c.asin)
            deduped_candidates.append(c)

            # Determine clean, real product title
            clean_title = ""
            if c.verified_product and c.verified_product.title and c.verified_product.title.strip().lower() != "unknown":
                clean_title = c.verified_product.title.strip()
            elif c.raw_product and c.raw_product.title and c.raw_product.title.strip().lower() != "unknown":
                clean_title = c.raw_product.title.strip()
            else:
                clean_title = (c.normalized_title or c.asin).strip()

            title_lower = clean_title.lower()

            # Breakthrough winner check (e.g. wall mounted ductless AC / portable 2-in-1 heaters for RVs)
            if ("wall mounted" in title_lower and "air conditioner" in title_lower) or ("ductless" in title_lower and "air conditioner" in title_lower):
                winner_asins.add(c.asin)
                if not c.scores or c.scores.total_score == 0.0:
                    from rv_winner_scout.domain.models import ScoreBreakdown
                    c.scores = ScoreBreakdown(
                        facebook_discovery_potential=19.0,
                        rv_facebook_exposure=14.5,
                        rv_relevance=15.0,
                        novelty_newness=14.5,
                        problem_solving_power=9.5,
                        visual_wow=9.0,
                        space_convenience=4.5,
                        impulse_click_potential=4.5,
                        rv_audience_breadth=4.5,
                        total_score=95.0,
                        is_winner=True,
                    )
            elif not c.scores or c.scores.total_score == 0.0:
                c.scores = compute_heuristic_scores(clean_title, c.exposure_level)

            # Tag as winner or should_be_tested if matching criteria
            if c.scores and c.scores.is_winner:
                winner_asins.add(c.asin)
            elif c.asin not in winner_asins:
                is_high_utility_solver = any(kw in title_lower for kw in ["soft start", "inrush limiter", "surge protector", "water pressure regulator", "macerator", "power station", "propane gas detector", "skylight insulator"])
                if c.is_should_test or (c.scores and c.scores.is_should_test) or is_high_utility_solver:
                    should_test_asins.add(c.asin)
                elif c.scores and (
                    c.scores.final_score >= 70.0
                    or (c.scores.final_score >= 50.0 and c.scores.problem_solving_power >= 7.0)
                    or c.scores.problem_solving_power >= 8.0
                ):
                    should_test_asins.add(c.asin)

    # Sort descending by score initially
    deduped_candidates.sort(
        key=lambda c: (c.scores.final_score if c.scores else 0.0), reverse=True
    )
    all_candidates = deduped_candidates
    winners_count = sum(1 for c in all_candidates if c.asin in winner_asins)
    should_test_count = sum(1 for c in all_candidates if (c.asin in should_test_asins and c.asin not in winner_asins))
    candidates_count = len(all_candidates) - winners_count - should_test_count
    cards_html = ""

    for idx, cand in enumerate(all_candidates, 1):
        is_winner = cand.asin in winner_asins
        is_should_test = (cand.asin in should_test_asins) and not is_winner

        # Clean title guarantee - NEVER display "Unknown"
        raw_title = ""
        if cand.verified_product and cand.verified_product.title and cand.verified_product.title.strip().lower() != "unknown":
            raw_title = cand.verified_product.title.strip()
        elif cand.raw_product and cand.raw_product.title and cand.raw_product.title.strip().lower() != "unknown":
            raw_title = cand.raw_product.title.strip()
        else:
            raw_title = (cand.normalized_title or cand.asin).strip()

        title = html.escape(raw_title)
        asin = cand.asin
        amazon_url = cand.canonical_url if cand.canonical_url else f"https://www.amazon.com/dp/{asin}"

        # Price and BSR
        price_val = cand.verified_product.displayed_price if cand.verified_product else (cand.raw_product.displayed_price if cand.raw_product else None)
        price_display = f"${price_val:.2f}" if price_val is not None else ""
        price_num = price_val if price_val is not None else 0.0

        # BSR display
        bsr_display = ""
        if cand.verified_product and cand.verified_product.bsr_rank:
            bsr_display = cand.verified_product.bsr_rank
        elif cand.raw_product and cand.raw_product.bsr_rank:
            bsr_display = cand.raw_product.bsr_rank
        else:
            bsr_display = "Ranked in RV New Releases"
        # Numeric BSR for sorting
        bsr_num = 9999999
        if bsr_display:
            digits = "".join(ch for ch in bsr_display.split()[0] if ch.isdigit())
            if digits:
                try:
                    bsr_num = int(digits)
                except ValueError:
                    bsr_num = 9999999

        score_val = cand.scores.final_score if cand.scores else 50.0

        # Walmart data with guaranteed functional direct link or search link
        walmart_status = cand.walmart.status.value if cand.walmart else "NOT FOUND"
        walmart_price = f"${cand.walmart.displayed_price:.2f}" if (cand.walmart and cand.walmart.displayed_price) else ""
        query_str = urllib.parse.quote_plus(raw_title[:60])
        walmart_url = (
            cand.walmart.url
            if (cand.walmart and cand.walmart.url and cand.walmart.url.startswith("http"))
            else f"https://www.walmart.com/search?q={query_str}"
        )
        walmart_label = walmart_price if walmart_price else ("Available" if walmart_status == "FOUND" else "Check Walmart")

        # Single primary product image
        img_url = ""
        if cand.verified_product and cand.verified_product.images:
            for im in cand.verified_product.images:
                if im and im.startswith("http"):
                    img_url = im
                    break
        if not img_url and cand.raw_product and cand.raw_product.images:
            for im in cand.raw_product.images:
                if im and im.startswith("http"):
                    img_url = im
                    break
        if not img_url and cand.raw_product and cand.raw_product.image_url:
            img_url = cand.raw_product.image_url

        if not img_url:
            img_url = "https://images.unsplash.com/photo-1523987355523-c7b5b0dd90a7?w=600&auto=format&fit=crop&q=80"

        # 3 Humanized marketing angles with relatable examples
        angles = generate_humanized_angles(cand)
        angles_html = ""
        for label, text in angles:
            escaped_text = html.escape(text)
            angles_html += f"""
                    <div class="insight-row angle-row">
                        <div class="insight-header">
                            <span class="insight-label-angle">{label}:</span>
                            <button class="btn-copy-sm" onclick="copySnippet(this)" data-copy="{escaped_text}" title="Copy Angle">📋 Copy</button>
                        </div>
                        <p class="insight-text">{escaped_text}</p>
                    </div>"""

        raw_why, raw_risk = get_why_converts_and_risk(cand)
        why_next = html.escape(raw_why)
        why_fail = html.escape(raw_risk)

        if is_winner:
            status_class = "winner"
            status_badge = "🏆 QUALIFIED WINNER"
            badge_class = "badge-winner"
            data_type = "winner"
        elif is_should_test:
            status_class = "should_test"
            status_badge = "🧪 SHOULD BE TESTED"
            badge_class = "badge-test"
            data_type = "should_test"
        else:
            status_class = "candidate"
            status_badge = "RESEARCH CANDIDATE"
            badge_class = "badge-candidate"
            data_type = "candidate"

        # Change delta indicator across 24h runs
        change_pill = ""
        if cand.change_type == "improved":
            delta_str = f"+{cand.score_delta:.1f}" if cand.score_delta is not None and cand.score_delta > 0 else "Improved"
            change_pill = f'<span class="delta-pill delta-improved" title="Score improved from {cand.previous_score or 0:.1f} to {score_val:.1f}">📈 {delta_str}</span>'
        elif cand.change_type == "declined":
            delta_str = f"{cand.score_delta:.1f}" if cand.score_delta is not None and cand.score_delta < 0 else "Declined"
            change_pill = f'<span class="delta-pill delta-declined" title="Score declined from {cand.previous_score or 0:.1f} to {score_val:.1f}">📉 {delta_str}</span>'
        elif cand.change_type == "updated":
            change_pill = '<span class="delta-pill delta-updated" title="Price / ranking updated">🔄 Updated</span>'

        matched_arch = ArchetypeMatcher.match_candidate(raw_title)
        archetype_pill = f'<span class="archetype-pill">{matched_arch.badge_label}</span>' if matched_arch else ""
        archetype_row_html = ""

        cards_html += f"""
        <div class="product-card {status_class}" data-title="{title.lower()} {asin.lower()}" data-type="{data_type}" data-changed="{cand.change_type or 'none'}" data-score="{score_val:.2f}" data-price="{price_num:.2f}" data-bsr="{bsr_num}">
            <div class="card-top-bar">
                <div class="badge-group">
                    <span class="status-pill {badge_class}">{status_badge}</span>
                    <span class="score-pill">⭐ {score_val:.1f} / 100</span>
                    {archetype_pill}
                    {change_pill}
                </div>
                <span class="asin-pill">ASIN: {asin}</span>
            </div>

            <!-- Single Product Image -->
            <div class="product-image-box">
                <img src="{img_url}" alt="{title}" class="product-img" loading="lazy" referrerpolicy="no-referrer" onerror="this.onerror=null;this.src='https://images.unsplash.com/photo-1523987355523-c7b5b0dd90a7?w=600&auto=format&fit=crop&q=80';" />
            </div>

            <!-- Card Content -->
            <div class="card-body">
                <h3 class="product-title" title="{title}">{title}</h3>

                <!-- BSR and Price Meta -->
                <div class="bsr-meta-box">
                    <div class="meta-item">
                        <span class="meta-label">Amazon Price</span>
                        <span class="meta-val highlight">{price_display if price_display else 'Listed on Amazon'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">Amazon Best Sellers Rank</span>
                        <span class="meta-val bsr-val">{bsr_display}</span>
                    </div>
                </div>

                <!-- Stores Arbitrage Row -->
                <div class="stores-row">
                    <a href="{amazon_url}" target="_blank" rel="noopener noreferrer" class="btn-store btn-amazon">
                        🛒 View on Amazon ↗
                    </a>
                    <a href="{walmart_url}" target="_blank" rel="noopener noreferrer" class="btn-store btn-walmart">
                        🔵 Walmart ({walmart_label}) ↗
                    </a>
                </div>

                <!-- Marketing & Commercial Insights (Angles below Why Converts & Risk) -->
                <div class="insights-box">
                    <div class="insight-row">
                        <div class="insight-header">
                            <span class="insight-label-why">🎯 Why It Converts:</span>
                        </div>
                        <p class="insight-text">{why_next}</p>
                    </div>

                    <div class="insight-row">
                        <div class="insight-header">
                            <span class="insight-label-risk">⚠️ Bottleneck / Risk:</span>
                        </div>
                        <p class="insight-text">{why_fail}</p>
                    </div>
{archetype_row_html}
{angles_html}
                </div>
            </div>
        </div>
        """

    empty_state_html = """
        <div style="grid-column: 1 / -1; background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: 16px; padding: 48px 24px; text-align: center; box-shadow: var(--card-shadow);">
            <div style="font-size: 2.8rem; margin-bottom: 14px;">📡</div>
            <h3 style="font-size: 1.25rem; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;">Scout Pipeline Initialized & Ready</h3>
            <p style="color: var(--text-secondary); max-width: 540px; margin: 0 auto; font-size: 0.92rem; line-height: 1.6;">
                The autonomous research engine is configured and waiting for the next scout run. 
                All discovered RV New Releases will be audited against the 18 pain points, verified with live pricing & Amazon BSR, and logged directly here.
            </p>
        </div>
    """

    changed_tab_btn = ""
    if health.products_changed > 0:
        changed_tab_btn = f'<button class="filter-btn" onclick="setFilter(\'changed\', this)">🔄 Changed ({health.products_changed})</button>'

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="slate">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>RV Winner Scout — Executive Dashboard ({run_date})</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        /* Modern Eye-Comfort Design System (Shadcn / Tailwind UI Inspired) */
        :root, html[data-theme="slate"] {{
            --bg-body: #0F172A;
            --bg-surface: #1E293B;
            --bg-card: #1E293B;
            --bg-card-alt: #0F172A;
            --border-color: #334155;
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --accent: #10B981;
            --accent-soft: rgba(16, 185, 129, 0.12);
            --amazon-color: #F59E0B;
            --walmart-color: #38BDF8;
            --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }}

        html[data-theme="midnight"] {{
            --bg-body: #090D16;
            --bg-surface: #111827;
            --bg-card: #111827;
            --bg-card-alt: #0B0F19;
            --border-color: #1F2937;
            --text-primary: #F9FAFB;
            --text-secondary: #9CA3AF;
            --text-muted: #6B7280;
            --accent: #06B6D4;
            --accent-soft: rgba(6, 182, 212, 0.12);
            --amazon-color: #FBBF24;
            --walmart-color: #60A5FA;
            --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        }}

        html[data-theme="graphite"] {{
            --bg-body: #121214;
            --bg-surface: #1C1C1F;
            --bg-card: #1C1C1F;
            --bg-card-alt: #161618;
            --border-color: #2E2E32;
            --text-primary: #EDEDED;
            --text-secondary: #A1A1AA;
            --text-muted: #71717A;
            --accent: #F59E0B;
            --accent-soft: rgba(245, 158, 11, 0.12);
            --amazon-color: #F59E0B;
            --walmart-color: #38BDF8;
            --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }}

        html[data-theme="light"] {{
            --bg-body: #F8FAFC;
            --bg-surface: #FFFFFF;
            --bg-card: #FFFFFF;
            --bg-card-alt: #F1F5F9;
            --border-color: #E2E8F0;
            --text-primary: #0F172A;
            --text-secondary: #475569;
            --text-muted: #94A3B8;
            --accent: #059669;
            --accent-soft: rgba(5, 150, 105, 0.1);
            --amazon-color: #D97706;
            --walmart-color: #0284C7;
            --card-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-body);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 24px 20px 80px;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}

        .dashboard-container {{ max-width: 1240px; margin: 0 auto; }}

        /* Top Navbar */
        .top-navbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 16px 24px;
            margin-bottom: 24px;
            box-shadow: var(--card-shadow);
            flex-wrap: wrap;
            gap: 16px;
        }}
        .brand-title {{ font-size: 1.3rem; font-weight: 800; letter-spacing: -0.3px; }}
        
        .nav-controls {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}

        /* Theme Picker Switcher */
        .theme-picker {{ display: flex; align-items: center; gap: 6px; background: var(--bg-card-alt); padding: 4px; border-radius: 10px; border: 1px solid var(--border-color); }}
        .theme-btn {{
            background: transparent;
            border: none;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        }}
        .theme-btn.active {{
            background: var(--bg-surface);
            color: var(--text-primary);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
        }}

        .live-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 7px 14px;
            border-radius: 999px;
            background: rgba(16, 185, 129, 0.12);
            color: #10B981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .pulse-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse-green 2s infinite;
        }}
        @keyframes pulse-green {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
        }}

        /* KPI Row */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-box {{
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: var(--card-shadow);
        }}
        .kpi-label {{ font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px; }}
        .kpi-num {{ font-size: 2rem; font-weight: 800; letter-spacing: -0.5px; color: var(--text-primary); }}

        /* Toolbar */
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px 18px;
            margin-bottom: 24px;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .search-input {{
            width: 100%;
            max-width: 360px;
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 14px;
            color: var(--text-primary);
            font-size: 0.88rem;
            outline: none;
        }}
        .search-input:focus {{ border-color: var(--accent); }}

        .filter-tabs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .filter-btn {{
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            font-size: 0.82rem;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .filter-btn:hover {{
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.05);
        }}
        .filter-btn.active {{
            background: var(--accent-soft);
            color: var(--accent);
            border-color: var(--accent);
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
        }}

        .sort-wrapper {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-left: auto;
        }}
        .sort-label {{
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 600;
            white-space: nowrap;
        }}
        .sort-select {{
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 6px 12px;
            color: var(--text-primary);
            font-size: 0.82rem;
            font-weight: 600;
            outline: none;
            cursor: pointer;
            transition: border-color 0.2s;
        }}
        .sort-select:focus {{
            border-color: var(--accent);
        }}

        /* Product Cards Grid */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 24px;
        }}
        .product-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: var(--card-shadow);
            transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.3s ease;
            animation: fadeInCard 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}
        @keyframes fadeInCard {{
            from {{
                opacity: 0;
                transform: translateY(12px) scale(0.98);
            }}
            to {{
                opacity: 1;
                transform: translateY(0) scale(1);
            }}
        }}
        .product-card:hover {{
            transform: translateY(-3px);
            border-color: var(--accent);
        }}
        .product-card.should_test:hover {{
            border-color: #38BDF8;
        }}

        .card-top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .badge-group {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .status-pill {{
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 999px;
        }}
        .badge-winner {{ background: var(--accent-soft); color: var(--accent); }}
        .badge-test {{ background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35); }}
        .badge-candidate {{ background: rgba(148, 163, 184, 0.12); color: var(--text-secondary); }}
        .score-pill {{
            background: rgba(16, 185, 129, 0.12);
            color: var(--accent);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
        }}
        .asin-pill {{ font-size: 0.75rem; color: var(--text-muted); font-weight: 600; margin-left: auto; }}
        .delta-pill {{
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
        }}
        .delta-improved {{
            background: rgba(16, 185, 129, 0.2);
            color: #10B981;
            border: 1px solid rgba(16, 185, 129, 0.45);
        }}
        .delta-declined {{
            background: rgba(239, 68, 68, 0.2);
            color: #EF4444;
            border: 1px solid rgba(239, 68, 68, 0.45);
        }}
        .delta-updated {{
            background: rgba(245, 158, 11, 0.2);
            color: #F59E0B;
            border: 1px solid rgba(245, 158, 11, 0.45);
        }}
        .archetype-pill {{
            font-size: 0.70rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 999px;
            background: rgba(99, 102, 241, 0.12);
            color: #818CF8;
            border: 1px solid rgba(99, 102, 241, 0.3);
            display: inline-flex;
            align-items: center;
            white-space: nowrap;
        }}

        /* Single Product Image */
        .product-image-box {{
            position: relative;
            height: 200px;
            background: var(--bg-card-alt);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-top: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
            padding: 10px;
        }}
        .product-img {{
            max-height: 180px;
            max-width: 90%;
            object-fit: contain;
            border-radius: 6px;
            transition: transform 0.25s ease;
        }}
        .product-card:hover .product-img {{
            transform: scale(1.03);
        }}

        /* Card Content */
        .card-body {{ padding: 18px; flex: 1; display: flex; flex-direction: column; }}
        .product-title {{
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.4;
            margin-bottom: 14px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            height: 2.8em;
        }}

        /* BSR and Price */
        .bsr-meta-box {{
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 14px;
            display: flex;
            justify-content: space-between;
            margin-bottom: 14px;
        }}
        .meta-item {{ display: flex; flex-direction: column; }}
        .meta-label {{ font-size: 0.72rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; }}
        .meta-val {{ font-size: 0.95rem; font-weight: 700; color: var(--text-primary); }}
        .highlight {{ color: var(--amazon-color); }}
        .bsr-val {{ color: var(--accent); }}

        /* Stores Row */
        .stores-row {{ display: flex; gap: 8px; margin-bottom: 14px; }}
        .btn-store {{
            flex: 1;
            padding: 8px 10px;
            border-radius: 8px;
            text-align: center;
            text-decoration: none;
            font-size: 0.78rem;
            font-weight: 700;
            transition: opacity 0.2s;
        }}
        .btn-amazon {{ background: var(--amazon-color); color: #000; }}
        .btn-walmart {{ background: #0071DC; color: #fff; }}
        .btn-store:hover {{ opacity: 0.88; }}

        /* Marketing Angles & Commercial Insights */
        .insights-box {{
            margin-bottom: 16px;
            font-size: 0.84rem;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        .insight-row {{
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 12px;
        }}
        .insight-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }}
        .insight-label-angle {{ color: #818CF8; font-size: 0.76rem; font-weight: 700; }}
        .insight-label-hook {{ color: #F43F5E; font-size: 0.76rem; font-weight: 700; }}
        .insight-label-why {{ color: var(--accent); font-size: 0.76rem; font-weight: 700; }}
        .insight-label-risk {{ color: var(--amazon-color); font-size: 0.76rem; font-weight: 700; }}
        .insight-label-archetype {{ color: #A78BFA; font-size: 0.76rem; font-weight: 700; }}
        .archetype-meta {{ color: #818CF8; font-size: 0.76rem; font-weight: 600; }}
        .insight-text {{ color: var(--text-secondary); font-size: 0.82rem; line-height: 1.45; margin: 0; }}
        .btn-copy-sm {{
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 0.70rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-copy-sm:hover {{
            background: var(--accent-soft);
            color: var(--accent);
            border-color: var(--accent);
        }}

        /* Logout Button */
        .btn-logout {{
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}
        .btn-logout:hover {{
            background: rgba(239, 68, 68, 0.15);
            border-color: #EF4444;
            color: #EF4444;
        }}

        /* Login Screen Overlay */
        .login-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(10, 10, 12, 0.92);
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 99999;
            padding: 20px;
        }}
        .login-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 38px 32px;
            width: 100%;
            max-width: 410px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.7);
            text-align: center;
            animation: modalFadeIn 0.3s ease-out;
        }}
        @keyframes modalFadeIn {{
            from {{ opacity: 0; transform: scale(0.95) translateY(10px); }}
            to {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}
        .login-icon {{
            font-size: 2.4rem;
            margin-bottom: 12px;
            display: inline-block;
        }}
        .login-title {{
            font-size: 1.35rem;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.3px;
            margin-bottom: 6px;
        }}
        .login-subtitle {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 24px;
        }}
        .login-form {{
            display: flex;
            flex-direction: column;
            gap: 14px;
            text-align: left;
        }}
        .form-group {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .form-group label {{
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.5px;
        }}
        .login-input {{
            width: 100%;
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 16px;
            color: var(--text-primary);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        .login-input:focus {{
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-soft);
        }}
        .login-options {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        .remember-label {{
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            user-select: none;
        }}
        .remember-label input[type="checkbox"] {{
            accent-color: var(--accent);
            width: 16px;
            height: 16px;
            cursor: pointer;
        }}
        .btn-submit-login {{
            background: var(--accent);
            color: #000;
            border: none;
            border-radius: 10px;
            padding: 13px;
            font-size: 0.95rem;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
            transition: opacity 0.2s, transform 0.1s;
        }}
        .btn-submit-login:hover {{ opacity: 0.92; }}
        .btn-submit-login:active {{ transform: scale(0.98); }}
        .login-error {{
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #EF4444;
            padding: 10px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            display: none;
            margin-bottom: 12px;
            text-align: center;
        }}

        /* Responsive Breakpoints for Mobile & Tablet */
        @media (max-width: 900px) {{
            .dashboard-container {{ padding: 0 4px; }}
            .kpi-row {{ grid-template-columns: repeat(2, 1fr); gap: 12px; }}
            .cards-grid {{ grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }}
        }}

        @media (max-width: 640px) {{
            body {{ padding: 14px 10px 60px; }}
            .top-navbar {{
                flex-direction: column;
                align-items: stretch;
                padding: 14px 16px;
                gap: 12px;
            }}
            .brand-title {{ text-align: center; font-size: 1.15rem; }}
            .nav-controls {{
                justify-content: space-between;
                width: 100%;
                gap: 8px;
            }}
            .theme-picker {{
                flex: 1;
                justify-content: center;
                overflow-x: auto;
            }}
            .theme-btn {{ padding: 6px 8px; font-size: 0.74rem; }}
            .live-badge, .btn-logout {{
                padding: 7px 10px;
                font-size: 0.78rem;
                white-space: nowrap;
            }}
            .kpi-row {{
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }}
            .kpi-box {{ padding: 12px 14px; border-radius: 12px; }}
            .kpi-label {{ font-size: 0.7rem; }}
            .kpi-num {{ font-size: 1.5rem; }}

            .verdict-banner {{ padding: 16px 14px; margin-bottom: 18px; }}
            .verdict-banner h2 {{ font-size: 1.05rem; }}
            .verdict-quote {{ font-size: 0.92rem; }}

            .toolbar {{
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
                padding: 10px 12px;
            }}
            .search-input {{
                max-width: 100%;
                width: 100%;
                font-size: 16px; /* Prevents auto-zoom on iOS Safari */
            }}
            .filter-tabs {{
                display: flex;
                width: 100%;
                gap: 6px;
            }}
            .filter-btn {{
                flex: 1;
                text-align: center;
                padding: 8px 4px;
                font-size: 0.74rem;
            }}
            .sort-wrapper {{
                width: 100%;
                justify-content: space-between;
                margin-left: 0;
            }}
            .sort-select {{
                flex: 1;
                font-size: 14px;
            }}

            .cards-grid {{
                grid-template-columns: 1fr;
                gap: 16px;
            }}
            .product-image-box {{
                height: 180px;
            }}
            .product-title {{
                font-size: 0.98rem;
                height: auto;
                max-height: 3em;
                -webkit-line-clamp: 2;
            }}
            .stores-row {{
                flex-direction: row;
                gap: 6px;
            }}
            .btn-store {{
                padding: 10px 8px;
                font-size: 0.76rem;
            }}

            .login-card {{
                padding: 26px 18px;
                border-radius: 16px;
            }}
            .login-input {{
                font-size: 16px; /* Prevents auto-zoom on iOS Safari */
                padding: 11px 14px;
            }}
            .btn-submit-login {{
                padding: 14px;
                font-size: 0.92rem;
            }}
        }}
    </style>
</head>
<body>
    <!-- Login Screen Overlay -->
    <div class="login-overlay" id="loginOverlay">
        <div class="login-card">
            <div class="login-icon">🔒</div>
            <h2 class="login-title">RV WINNER SCOUT</h2>
            <p class="login-subtitle">Authorized B2B Client Access</p>
            
            <div class="login-error" id="loginError">Incorrect username or password.</div>

            <form class="login-form" onsubmit="event.preventDefault(); attemptLogin();">
                <div class="form-group">
                    <label for="loginUser">Username</label>
                    <input type="text" id="loginUser" class="login-input" placeholder="Enter username" autocomplete="username" required autofocus />
                </div>
                
                <div class="form-group">
                    <label for="loginPass">Password</label>
                    <input type="password" id="loginPass" class="login-input" placeholder="••••••••••••" autocomplete="current-password" required />
                </div>

                <div class="login-options">
                    <label class="remember-label">
                        <input type="checkbox" id="rememberMe" checked />
                        <span>Remember me</span>
                    </label>
                </div>

                <button type="submit" class="btn-submit-login" id="loginSubmitBtn">Access Dashboard</button>
            </form>
        </div>
    </div>

    <div class="dashboard-container" id="dashboardContainer" style="display: none;">
        <!-- Top Navbar -->
        <header class="top-navbar">
            <div class="brand-title">RV WINNER SCOUT</div>
            
            <div class="nav-controls">
                <!-- Theme Switcher -->
                <div class="theme-picker">
                    <button class="theme-btn active" onclick="setTheme('slate')">Slate</button>
                    <button class="theme-btn" onclick="setTheme('midnight')">Midnight</button>
                    <button class="theme-btn" onclick="setTheme('graphite')">Graphite</button>
                    <button class="theme-btn" onclick="setTheme('light')">Light</button>
                </div>

                <div class="live-badge" title="Real-Time Scout Live Feed Active">
                    <span class="pulse-dot"></span> Live Feed
                </div>

                <button class="btn-logout" onclick="logout()" title="Sign Out">
                    🔒 Sign Out
                </button>
            </div>
        </header>

        <!-- KPI Row -->
        <section class="kpi-row">
            <div class="kpi-box">
                <div class="kpi-label">Audited Products</div>
                <div class="kpi-num">{reviewed_count}</div>
            </div>

            <div class="kpi-box">
                <div class="kpi-label">Qualified Winners</div>
                <div class="kpi-num" style="color: {'var(--accent)' if winners_count else 'var(--text-muted)'}">{winners_count}</div>
            </div>

            <div class="kpi-box">
                <div class="kpi-label">Should Be Tested</div>
                <div class="kpi-num" style="color: {'#38BDF8' if should_test_count else 'var(--text-muted)'}">{should_test_count}</div>
            </div>

            <div class="kpi-box">
                <div class="kpi-label">Changes Detected</div>
                <div class="kpi-num" style="color: {'#F59E0B' if health.products_changed else 'var(--text-muted)'}">{health.products_changed}</div>
                <div style="font-size:0.72rem; color:var(--text-secondary); margin-top:3px; font-weight:600;">
                    📈 {health.products_improved} Improved • 📉 {health.products_declined} Declined
                </div>
            </div>

            <div class="kpi-box">
                <div class="kpi-label">Filtered / Sub-Threshold</div>
                <div class="kpi-num">{health.products_rejected}</div>
            </div>
        </section>

        <!-- Filter Toolbar -->
        <section class="toolbar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search by product title or ASIN..." onkeyup="filterCards()" />

            <div class="filter-tabs">
                <button class="filter-btn active" onclick="setFilter('all', this)">All ({len(all_candidates)})</button>
                <button class="filter-btn" onclick="setFilter('winner', this)">🏆 Winners ({winners_count})</button>
                <button class="filter-btn" onclick="setFilter('should_test', this)">🧪 Should Be Tested ({should_test_count})</button>
                <button class="filter-btn" onclick="setFilter('candidate', this)">Candidates ({candidates_count})</button>
                {changed_tab_btn}
            </div>

            <div class="sort-wrapper">
                <label for="sortSelect" class="sort-label">Sort by:</label>
                <select id="sortSelect" class="sort-select" onchange="sortCards(this.value)">
                    <option value="score-desc">Highest Score ⭐</option>
                    <option value="score-asc">Lowest Score</option>
                    <option value="price-desc">Price: High to Low</option>
                    <option value="price-asc">Price: Low to High</option>
                    <option value="bsr-asc">Amazon BSR (Best Rank)</option>
                </select>
            </div>
        </section>

        <!-- Product Cards Grid -->
        <main class="cards-grid" id="cardsGrid">
            {cards_html if cards_html else empty_state_html}
        </main>
    </div>

    <script>
        // 1. Theme Switcher with Persistence
        function setTheme(themeName) {{
            document.documentElement.setAttribute('data-theme', themeName);
            localStorage.setItem('scout_theme', themeName);
            document.querySelectorAll('.theme-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.innerText.toLowerCase() === themeName);
            }});
        }}

        // Load saved theme
        const savedTheme = localStorage.getItem('scout_theme') || 'slate';
        setTheme(savedTheme);

        // 2. Copy Marketing / Creative Angle
        function copySnippet(btn) {{
            const text = btn.getAttribute('data-copy');
            if (!text) return;
            navigator.clipboard.writeText(text).then(() => {{
                const orig = btn.innerText;
                btn.innerText = "✓ Copied";
                btn.style.color = "var(--accent)";
                btn.style.borderColor = "var(--accent)";
                setTimeout(() => {{
                    btn.innerText = orig;
                    btn.style.color = "";
                    btn.style.borderColor = "";
                }}, 1800);
            }}).catch(err => {{
                console.error("Copy failed", err);
            }});
        }}

        // 4. Live Search and Filter
        let currentFilter = 'all';

        function filterCards() {{
            const searchVal = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.product-card');

            cards.forEach(card => {{
                const type = card.getAttribute('data-type');
                const title = card.getAttribute('data-title');
                const changed = card.getAttribute('data-changed');

                const matchesSearch = title.includes(searchVal);
                const matchesFilter = (currentFilter === 'all')
                    || (type === currentFilter)
                    || (currentFilter === 'changed' && changed && changed !== 'none');

                if (matchesSearch && matchesFilter) {{
                    if (card.style.display === 'none') {{
                        card.style.display = 'flex';
                        card.style.animation = 'none';
                        card.offsetHeight; /* trigger reflow */
                        card.style.animation = 'fadeInCard 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards';
                    }}
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        function setFilter(type, btn) {{
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterCards();
        }}

        // 5. Card Sorting
        function sortCards(sortKey) {{
            const grid = document.getElementById('cardsGrid');
            if (!grid) return;
            const cards = Array.from(grid.querySelectorAll('.product-card'));
            if (cards.length <= 1) return;

            cards.sort((a, b) => {{
                const scoreA = parseFloat(a.dataset.score) || 0;
                const scoreB = parseFloat(b.dataset.score) || 0;
                const priceA = parseFloat(a.dataset.price) || 0;
                const priceB = parseFloat(b.dataset.price) || 0;
                const bsrA = parseInt(a.dataset.bsr) || 9999999;
                const bsrB = parseInt(b.dataset.bsr) || 9999999;

                if (sortKey === 'score-desc') return scoreB - scoreA;
                if (sortKey === 'score-asc') return scoreA - scoreB;
                if (sortKey === 'price-desc') return priceB - priceA;
                if (sortKey === 'price-asc') return priceA - priceB;
                if (sortKey === 'bsr-asc') return bsrA - bsrB;
                return 0;
            }});

            cards.forEach(card => grid.appendChild(card));
        }}

        // 6. Authentication & Client Access Gate
        const AUTH_USER = "almostafa";
        const AUTH_HASH = "d7f6bc259795aebde3360364c91c781ac93edc0feaa81dead8d512f40376d726";
        const AUTH_STORAGE_KEY = "scout_portal_session_token";

        async function computeSHA256(text) {{
            if (window.crypto && window.crypto.subtle) {{
                const msgBuffer = new TextEncoder().encode(text);
                const hashBuffer = await window.crypto.subtle.digest('SHA-256', msgBuffer);
                const hashArray = Array.from(new Uint8Array(hashBuffer));
                return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
            }} else {{
                // Fallback direct match for non-crypto contexts
                return text === "Almostafa311911@z" ? AUTH_HASH : "invalid";
            }}
        }}

        function checkAuth() {{
            const remembered = localStorage.getItem(AUTH_STORAGE_KEY);
            const session = sessionStorage.getItem(AUTH_STORAGE_KEY);

            if (remembered === AUTH_HASH || session === AUTH_HASH) {{
                showDashboard();
            }} else {{
                showLogin();
            }}
        }}

        function showDashboard() {{
            const overlay = document.getElementById('loginOverlay');
            const container = document.getElementById('dashboardContainer');
            if (overlay) overlay.style.display = 'none';
            if (container) container.style.display = 'block';
        }}

        function showLogin() {{
            const overlay = document.getElementById('loginOverlay');
            const container = document.getElementById('dashboardContainer');
            if (overlay) overlay.style.display = 'flex';
            if (container) container.style.display = 'none';
            const userInput = document.getElementById('loginUser');
            if (userInput) userInput.focus();
        }}

        async function attemptLogin() {{
            const userField = document.getElementById('loginUser');
            const passField = document.getElementById('loginPass');
            const rememberMe = document.getElementById('rememberMe').checked;
            const errorElem = document.getElementById('loginError');

            errorElem.style.display = 'none';
            const userVal = userField.value.trim().toLowerCase();
            const passVal = passField.value;

            if (!userVal || !passVal) {{
                errorElem.innerText = "Please provide both username and password.";
                errorElem.style.display = 'block';
                return;
            }}

            const computedHash = await computeSHA256(passVal);

            if (userVal === AUTH_USER && computedHash === AUTH_HASH) {{
                if (rememberMe) {{
                    localStorage.setItem(AUTH_STORAGE_KEY, AUTH_HASH);
                }} else {{
                    sessionStorage.setItem(AUTH_STORAGE_KEY, AUTH_HASH);
                }}
                showDashboard();
            }} else {{
                errorElem.innerText = "Incorrect username or password. Access denied.";
                errorElem.style.display = 'block';
                passField.value = '';
                passField.focus();
            }}
        }}

        function logout() {{
            localStorage.removeItem(AUTH_STORAGE_KEY);
            sessionStorage.removeItem(AUTH_STORAGE_KEY);
            const passField = document.getElementById('loginPass');
            if (passField) passField.value = '';
            showLogin();
        }}

        // Run authentication check on startup
        checkAuth();
    </script>
</body>
</html>
"""
    return html_content


def save_dashboard(
    reviewed_count: int,
    winners: List[ProductCandidate],
    near_misses: List[ProductCandidate],
    health: RunHealthReport,
    data_dir: str = "data",
    spreadsheet_id: Optional[str] = None,
    candidates: Optional[List[ProductCandidate]] = None,
    should_be_tested: Optional[List[ProductCandidate]] = None,
) -> str:
    """Generates and writes dashboard to reports directory and public sync directory."""
    html_str = generate_executive_dashboard_html(
        reviewed_count=reviewed_count,
        winners=winners,
        near_misses=near_misses,
        health=health,
        spreadsheet_id=spreadsheet_id,
        candidates=candidates,
        should_be_tested=should_be_tested,
    )
    reports_dir = os.path.join(data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"dashboard_{health.run_id}.html"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_str)

    latest_path = os.path.join(reports_dir, "latest_dashboard.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    index_path = os.path.join(reports_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    # Sync to public/index.html and root index.html for Cloudflare Pages / Workers
    # Protect against test runs polluting production dashboard
    if data_dir == "data" and not os.environ.get("PYTEST_CURRENT_TEST"):
        public_dir = "public"
        os.makedirs(public_dir, exist_ok=True)
        with open(os.path.join(public_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_str)

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_str)

    return filepath
