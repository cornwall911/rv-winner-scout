"""Generates a high-productivity, themeable Executive E-Commerce Dashboard."""

import html
import json
import os
import re
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
    total_count = len(all_candidates)
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
<html lang="en" data-theme="campfire" data-mode="night">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="dark light">
    <meta name="referrer" content="no-referrer">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>RV Winner Scout · Executive Dashboard ({run_date})</title>
    <link rel="preload" href="fonts/fraunces-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="preload" href="fonts/manrope-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
    <script>
    /* Reel Factory early inline theme script: sets look before first paint (no flash) */
    (function(){{
        var d=document.documentElement,t="campfire",m="night",s="";
        try{{t=localStorage.getItem("rf_theme")||t;m=localStorage.getItem("rf_start")||m;s=sessionStorage.getItem("rf_mode_s")||""}}catch(e){{}}
        if(s)m=s;
        if(m==="auto"){{var h=new Date().getHours();m=h>=6&&h<18?"day":"night"}}
        d.setAttribute("data-theme",t);
        d.setAttribute("data-mode",m);
    }})();
    </script>
    <style>
        /* Reel Factory Fonts */
        @font-face{{font-family:"Fraunces";src:url(fonts/fraunces-latin-400-normal.woff2) format("woff2");font-weight:400;font-display:swap}}
        @font-face{{font-family:"Fraunces";src:url(fonts/fraunces-latin-500-normal.woff2) format("woff2");font-weight:500;font-display:swap}}
        @font-face{{font-family:"Fraunces";src:url(fonts/fraunces-latin-400-italic.woff2) format("woff2");font-weight:400;font-style:italic;font-display:swap}}
        @font-face{{font-family:"Manrope";src:url(fonts/manrope-latin-400-normal.woff2) format("woff2");font-weight:400;font-display:swap}}
        @font-face{{font-family:"Manrope";src:url(fonts/manrope-latin-500-normal.woff2) format("woff2");font-weight:500;font-display:swap}}
        @font-face{{font-family:"Manrope";src:url(fonts/manrope-latin-600-normal.woff2) format("woff2");font-weight:600;font-display:swap}}
        @font-face{{font-family:"Manrope";src:url(fonts/manrope-latin-700-normal.woff2) format("woff2");font-weight:700 800;font-display:swap}}
        @font-face{{font-family:"Plex Arabic";src:url(fonts/ibm-plex-sans-arabic-arabic-400-normal.woff2) format("woff2");font-weight:400 500;font-display:swap}}
        @font-face{{font-family:"Plex Arabic";src:url(fonts/ibm-plex-sans-arabic-arabic-600-normal.woff2) format("woff2");font-weight:600 800;font-display:swap}}

        /* Reel Factory Design System Tokens */
        :root {{
            --r: 16px;
            --serif: "Fraunces", Georgia, "Times New Roman", serif;
            --sans: "Manrope", "Plex Arabic", "Segoe UI", system-ui, sans-serif;
            --mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
        }}

        :root[data-mode="night"] {{
            color-scheme: dark;
            --ok: #4ADE80;
            --warn: #F5B544;
            --err: #FF7B6B;
            --run: #7CC4FF;
            --shadow: 0 18px 50px #0008;
        }}

        :root[data-mode="day"] {{
            color-scheme: light;
            --ok: #15803D;
            --warn: #B45309;
            --err: #C2321F;
            --run: #1D4ED8;
            --shadow: 0 18px 50px #2a1d0c1f;
        }}

        /* 1. Campfire (Default) */
        :root[data-theme="campfire"][data-mode="night"] {{
            --bg: #121417; --side: #0F1114; --card: #181B20; --card2: #1E2228; --line: #2A2F37;
            --fg: #F1ECE4; --muted: #A59D91; --pill: #232830; --accent: #F2A541; --on-accent: #1A1208; --accent2: #F7C27A;
        }}
        :root[data-theme="campfire"][data-mode="day"] {{
            --bg: #EAE4D8; --side: #DFD8C9; --card: #F3EEE3; --card2: #ECE6D9; --line: #D3CAB8;
            --fg: #1D1A15; --muted: #6A6155; --pill: #E2DACA; --accent: #E8953A; --on-accent: #1A1208; --accent2: #9A5410;
        }}

        /* 2. Forest */
        :root[data-theme="forest"][data-mode="night"] {{
            --bg: #0E1512; --side: #0B110E; --card: #131C18; --card2: #18231E; --line: #24332B;
            --fg: #EEF0E8; --muted: #9AA597; --pill: #1D2A24; --accent: #E2B86B; --on-accent: #1A1408; --accent2: #EBCB8D;
        }}
        :root[data-theme="forest"][data-mode="day"] {{
            --bg: #E3E7DB; --side: #D9DFCF; --card: #EFF2E8; --card2: #E8ECDF; --line: #CCD5C4;
            --fg: #17201A; --muted: #5E6B60; --pill: #DAE1D0; --accent: #D1A250; --on-accent: #1A1408; --accent2: #76561A;
        }}

        /* 3. Lakeside */
        :root[data-theme="lakeside"][data-mode="night"] {{
            --bg: #0B141B; --side: #091118; --card: #101C25; --card2: #14232E; --line: #1F3442;
            --fg: #E8F1F4; --muted: #93A7B2; --pill: #18293A; --accent: #3FD6C9; --on-accent: #04201D; --accent2: #7FE6DC;
        }}
        :root[data-theme="lakeside"][data-mode="day"] {{
            --bg: #DFEAEE; --side: #D4E2E8; --card: #EBF3F5; --card2: #E4EEF1; --line: #C3D6DE;
            --fg: #0F1E26; --muted: #557080; --pill: #D4E3E9; --accent: #22B8AA; --on-accent: #04201D; --accent2: #0B6F66;
        }}

        /* 4. Ember */
        :root[data-theme="ember"][data-mode="night"] {{
            --bg: #141213; --side: #100E0F; --card: #1B1819; --card2: #221E1F; --line: #322B2C;
            --fg: #F4ECE8; --muted: #A89C98; --pill: #2A2425; --accent: #F26B4A; --on-accent: #210904; --accent2: #F79A80;
        }}
        :root[data-theme="ember"][data-mode="day"] {{
            --bg: #EDE3DE; --side: #E3D7D1; --card: #F6EEEA; --card2: #EFE6E1; --line: #D9C8C0;
            --fg: #221715; --muted: #6E5C57; --pill: #E6D9D2; --accent: #EF6646; --on-accent: #210904; --accent2: #A9381C;
        }}

        /* 5. Desert */
        :root[data-theme="desert"][data-mode="night"] {{
            --bg: #15120E; --side: #110E0B; --card: #1C1813; --card2: #231E18; --line: #352D24;
            --fg: #F3ECE1; --muted: #A89A86; --pill: #2A231C; --accent: #E9C08A; --on-accent: #1C140A; --accent2: #F1D3AA;
        }}
        :root[data-theme="desert"][data-mode="day"] {{
            --bg: #EBE2D2; --side: #E1D6C3; --card: #F5EEE1; --card2: #EEE6D6; --line: #D8CAB3;
            --fg: #201A12; --muted: #6D604E; --pill: #E5DAC5; --accent: #DDA866; --on-accent: #1C140A; --accent2: #87561B;
        }}

        /* Registered Color Properties for View Transitions */
        @property --bg{{syntax:"<color>";inherits:true;initial-value:#121417}}
        @property --side{{syntax:"<color>";inherits:true;initial-value:#0F1114}}
        @property --card{{syntax:"<color>";inherits:true;initial-value:#181B20}}
        @property --card2{{syntax:"<color>";inherits:true;initial-value:#1E2228}}
        @property --line{{syntax:"<color>";inherits:true;initial-value:#2A2F37}}
        @property --fg{{syntax:"<color>";inherits:true;initial-value:#F1ECE4}}
        @property --muted{{syntax:"<color>";inherits:true;initial-value:#A59D91}}
        @property --pill{{syntax:"<color>";inherits:true;initial-value:#232830}}
        @property --accent{{syntax:"<color>";inherits:true;initial-value:#F2A541}}
        @property --accent2{{syntax:"<color>";inherits:true;initial-value:#F7C27A}}
        @property --on-accent{{syntax:"<color>";inherits:true;initial-value:#1A1208}}
        @property --ok{{syntax:"<color>";inherits:true;initial-value:#4ADE80}}
        @property --warn{{syntax:"<color>";inherits:true;initial-value:#F5B544}}
        @property --err{{syntax:"<color>";inherits:true;initial-value:#FF7B6B}}
        @property --run{{syntax:"<color>";inherits:true;initial-value:#7CC4FF}}

        ::view-transition-old(root){{animation:none}}
        ::view-transition-new(root){{animation:vtIn .9s ease-in-out both;mix-blend-mode:normal}}
        ::view-transition-group(root){{animation-duration:.9s}}
        @keyframes vtIn{{from{{opacity:0}}to{{opacity:1}}}}
        html.switching:not(.vt){{
            transition: --bg 1.8s ease, --side 1.8s ease, --card 1.8s ease, --card2 1.8s ease,
                        --line 1.8s ease, --fg 1.8s ease, --muted 1.8s ease, --pill 1.8s ease,
                        --accent 1.8s ease, --accent2 1.8s ease, --on-accent 1.8s ease,
                        --ok 1.8s ease, --warn 1.8s ease, --err 1.8s ease, --run 1.8s ease;
        }}

        /* Base & Reset */
        * {{ box-sizing: border-box; scrollbar-width: thin; scrollbar-color: var(--line) transparent; margin: 0; padding: 0; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            background: var(--bg);
            color: var(--fg);
            font: 14.5px/1.55 var(--sans);
            -webkit-font-smoothing: antialiased;
            min-height: 100vh;
        }}
        :focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
        svg.i {{ width: 18px; height: 18px; flex: none; stroke: currentColor; fill: none; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }}

        /* App Grid Layout */
        .app {{
            display: grid;
            grid-template-columns: 248px minmax(0, 1fr);
            min-height: 100vh;
        }}

        /* Sticky 248px Sidebar */
        .side {{
            background: var(--side);
            border-right: 1px solid var(--line);
            padding: 22px 16px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            position: sticky;
            top: 0;
            height: 100vh;
            overflow-y: auto;
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 11px;
            font-weight: 700;
            font-size: 16.5px;
            padding: 2px 8px 20px;
            letter-spacing: -.01em;
            color: var(--fg);
        }}
        .logo .mark {{ width: 34px; height: 34px; flex: none; }}
        .nav {{ display: flex; flex-direction: column; gap: 2px; }}
        .nav a {{
            display: flex;
            align-items: center;
            gap: 11px;
            padding: 9px 12px;
            border-radius: 11px;
            color: var(--muted);
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            transition: background-color .38s ease, color .38s ease, box-shadow .38s ease, transform .38s ease;
        }}
        .nav a svg {{ transition: color .38s ease, transform .38s ease; }}
        .nav a:hover svg {{ transform: scale(1.08); }}
        .nav a:active {{ transform: scale(.985); }}
        .nav a:hover {{ background: var(--card); color: var(--fg); }}
        .nav a.on {{
            background: color-mix(in srgb, var(--accent) 16%, transparent);
            color: var(--fg);
            box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 30%, transparent);
        }}
        .nav a.on svg {{ color: var(--accent); }}
        .nav .ct {{
            margin-left: auto;
            font-size: 11.5px;
            background: var(--card2);
            border: 1px solid var(--line);
            padding: 0 8px;
            border-radius: 99px;
            color: var(--muted);
            font-variant-numeric: tabular-nums;
        }}
        .sp {{ flex: 1; }}
        .machine {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 14px;
            font-size: 12px;
            color: var(--muted);
        }}
        .machine b {{ color: var(--fg); display: block; font-size: 13px; margin-bottom: 4px; }}
        .meter {{ height: 5px; border-radius: 9px; background: var(--pill); overflow: hidden; margin: 8px 0 3px; }}
        .meter span {{ display: block; height: 100%; background: var(--accent); border-radius: 9px; transition: width .6s; }}
        .statuspill {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 99px;
            padding: 7px 12px;
            font-size: 12.5px;
            color: var(--fg);
        }}
        .statuspill .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--ok);
            flex: none;
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--ok) 22%, transparent);
        }}
        .copy {{ font-size: 11px; color: var(--muted); padding: 8px 8px 0; opacity: .85; }}

        /* Main Content Wrapper */
        .mainwrap {{ min-width: 0; display: flex; flex-direction: column; }}

        /* Opaque Sticky Topbar */
        .topbar {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            padding: 14px 30px;
            position: sticky;
            top: 0;
            z-index: 20;
            background: var(--bg);
            border-bottom: 1px solid var(--line);
        }}
        .greet {{ flex: 1; min-width: 200px; font-size: 13.5px; color: var(--muted); }}
        .greet em {{ font-style: italic; color: var(--accent); font-family: var(--serif); font-size: 15px; }}

        /* Theme Selector Dropdown */
        .theme-select-wrap {{ display: inline-flex; align-items: center; }}
        .theme-dropdown {{
            width: auto;
            padding: 7px 12px;
            border-radius: 99px;
            background: var(--card);
            border: 1px solid var(--line);
            color: var(--fg);
            font: inherit;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all .2s;
        }}
        .theme-dropdown:hover {{ border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); }}

        /* Buttons (Reel Factory) */
        button, .btn {{
            font: inherit;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 8px 14px;
            border-radius: 12px;
            border: 1px solid var(--line);
            background: var(--card);
            color: var(--fg);
            cursor: pointer;
            text-decoration: none;
            transition: background .15s, border-color .15s, filter .15s, transform .2s;
        }}
        button:hover, .btn:hover {{
            border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
            background: var(--card2);
        }}
        button:active, .btn:active {{ transform: scale(.985); }}
        .pri, .primary {{
            border-color: transparent !important;
            background: var(--accent) !important;
            color: var(--on-accent) !important;
        }}
        .pri:hover, .primary:hover {{ filter: brightness(1.06); }}
        .modebtn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            border-radius: 99px !important;
            padding: 7px 14px !important;
        }}
        .modebtn svg {{ color: var(--accent); }}
        .btn-logout {{ color: var(--muted); }}
        .btn-logout:hover {{ color: var(--err); border-color: var(--err); }}

        /* Content Body */
        .content-body {{
            max-width: 1320px;
            padding: 22px 30px 80px;
            display: grid;
            gap: 18px;
            width: 100%;
        }}

        /* Hero Banner */
        .hero {{
            position: relative;
            border-radius: 22px;
            overflow: hidden;
            min-height: clamp(200px, 24vw, 300px);
            border: 1px solid var(--line);
            isolation: isolate;
            display: flex;
            align-items: center;
            box-shadow: var(--shadow);
            background: var(--card);
        }}
        .hero:before {{
            content: "";
            position: absolute;
            inset: 0;
            z-index: -1;
            pointer-events: none;
            background: radial-gradient(ellipse at 85% 50%, color-mix(in srgb, var(--accent) 14%, transparent) 0%, transparent 65%),
                        linear-gradient(90deg, color-mix(in srgb, var(--bg) 92%, transparent) 0%, color-mix(in srgb, var(--bg) 60%, transparent) 40%, transparent 80%);
        }}
        .hero-in {{
            padding: 34px 40px;
            max-width: 680px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }}
        .kick {{
            font-size: 11.5px;
            letter-spacing: .18em;
            text-transform: uppercase;
            font-weight: 700;
            color: var(--accent2);
        }}
        .display {{
            margin: 0;
            font-family: var(--serif);
            font-weight: 400;
            font-size: clamp(28px, 3.2vw, 46px);
            line-height: 1.05;
            letter-spacing: -.02em;
            color: var(--fg);
        }}
        .display em {{
            font-style: italic;
            color: var(--accent);
        }}
        .hero-in p {{
            margin: 0;
            font-size: 15px;
            color: var(--muted);
            max-width: 48ch;
            line-height: 1.5;
        }}
        .hero-acts {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 4px;
        }}

        /* KPI Tiles (.tiles and .tile from Reel Factory) */
        .tiles {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 14px;
        }}
        .tile {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: var(--r);
            padding: 16px 18px;
            display: flex;
            gap: 14px;
            align-items: center;
            box-shadow: var(--shadow);
            transition: border-color .38s ease, transform .38s ease;
        }}
        .tile:hover {{
            border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
            transform: translateY(-1px);
        }}
        .tile .ic {{
            flex: none;
            width: 44px;
            height: 44px;
            border-radius: 13px;
            display: grid;
            place-items: center;
            color: var(--c);
            background: color-mix(in srgb, var(--c) 14%, transparent);
        }}
        .tile .ic svg {{ width: 21px; height: 21px; }}
        .tile .k, .kpi-label {{
            font-size: 12.5px;
            color: var(--fg);
            font-weight: 600;
            margin-bottom: 2px;
        }}
        .tile .v, .kpi-num {{
            font-size: 26px;
            font-weight: 700;
            line-height: 1.1;
            font-variant-numeric: tabular-nums;
            color: var(--fg);
        }}
        .tile .s {{ font-size: 11.5px; color: var(--muted); margin-top: 2px; }}

        /* Filter Toolbar (Reel Factory .card style) */
        .toolbar {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 12px;
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: var(--r);
            padding: 16px 20px;
            box-shadow: var(--shadow);
        }}
        .search-input {{
            flex: 1 1 240px;
            min-width: 200px;
            padding: 10px 14px;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: var(--card2);
            color: var(--fg);
            font: inherit;
            transition: border-color .2s;
        }}
        .search-input:focus {{
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 24%, transparent);
        }}
        .filter-tabs {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            border-radius: 99px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--line);
            cursor: pointer;
            transition: all .2s;
        }}
        .filter-btn:hover {{
            background: var(--card2);
            color: var(--fg);
        }}
        .filter-btn.active {{
            background: var(--accent);
            color: var(--on-accent);
            border-color: var(--accent);
        }}
        .toolbar-side-actions {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-left: auto;
            flex-wrap: wrap;
        }}
        .price-toggle-btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            border-radius: 99px;
            background: var(--card2);
            border: 1px solid var(--line);
            color: var(--fg);
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all .2s;
        }}
        .price-toggle-btn:hover {{
            border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
        }}
        .price-toggle-btn.active {{
            background: color-mix(in srgb, var(--accent) 18%, transparent);
            border-color: var(--accent);
            color: var(--accent);
        }}
        .sort-wrapper {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }}
        .sort-label {{
            font-size: 12px;
            font-weight: 600;
            color: var(--muted);
        }}
        .sort-select {{
            width: auto;
            padding: 7px 12px;
            border-radius: 12px;
            background: var(--card2);
            border: 1px solid var(--line);
            color: var(--fg);
            font: inherit;
            font-size: 13px;
        }}

        /* Results Meta Bar */
        .results-meta-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 4px;
            font-size: 13px;
            color: var(--muted);
            font-variant-numeric: tabular-nums;
        }}

        /* Product Cards Grid & Responsive Layout */
        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 18px;
            width: 100%;
        }}
                @media (max-width: 768px) {{
            .cards-grid {{ grid-template-columns: 1fr; }}
            .filter-btn, .price-toggle-btn {{
                min-height: 44px;
                padding: 10px 16px;
            }}
            .page-btn {{
                min-height: 44px;
                min-width: 44px;
            }}
            .search-input {{
                min-height: 44px;
            }}
            .btn-store {{
                min-height: 44px;
            }}
        }}

        /* High-Performance Pagination Visibility */
        .cards-grid .product-card {{ display: none; }}
        .cards-grid.initialized .product-card.page-active {{
            display: flex;
            animation: cardFadeIn 0.22s ease-out;
        }}
        @keyframes cardFadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .cards-grid:not(.initialized) .product-card:nth-child(-n+24) {{ display: flex; }}

        /* Product Card (Reel Factory Warm Card) */
        .product-card {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: var(--r);
            padding: 20px;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 16px;
            box-shadow: var(--shadow);
            transition: border-color .38s ease, box-shadow .38s ease, transform .38s ease;
            position: relative;
        }}
        .product-card:hover {{
            border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
            transform: translateY(-2px);
        }}
        .card-top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .badge-group {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .status-pill {{
            font-size: 11.5px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 99px;
            background: var(--pill);
            color: var(--muted);
            border: 1px solid var(--line);
            letter-spacing: .02em;
        }}
        .status-pill.badge-winner {{
            background: color-mix(in srgb, var(--accent) 18%, transparent);
            color: var(--accent);
            border-color: color-mix(in srgb, var(--accent) 35%, transparent);
        }}
        .status-pill.badge-should-test {{
            background: color-mix(in srgb, var(--run) 18%, transparent);
            color: var(--run);
            border-color: color-mix(in srgb, var(--run) 35%, transparent);
        }}
        .status-pill.badge-candidate {{
            background: var(--pill);
            color: var(--muted);
            border-color: var(--line);
        }}
        .score-pill {{
            font-size: 11.5px;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 99px;
            background: var(--card2);
            color: var(--fg);
            border: 1px solid var(--line);
            font-variant-numeric: tabular-nums;
        }}
        .archetype-pill {{
            font-size: 11px;
            padding: 3px 10px;
            border-radius: 99px;
            background: var(--pill);
            color: var(--muted);
            border: 1px solid var(--line);
        }}
        .asin-pill {{
            font-size: 11px;
            color: var(--muted);
            background: var(--card2);
            border: 1px solid var(--line);
            padding: 2px 8px;
            border-radius: 6px;
            font-family: var(--mono);
        }}

        /* Delta Pills */
        .delta-pill {{
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 99px;
            font-variant-numeric: tabular-nums;
        }}
        .delta-improved {{
            background: color-mix(in srgb, var(--ok) 18%, transparent);
            color: var(--ok);
            border: 1px solid color-mix(in srgb, var(--ok) 35%, transparent);
        }}
        .delta-declined {{
            background: color-mix(in srgb, var(--err) 18%, transparent);
            color: var(--err);
            border: 1px solid color-mix(in srgb, var(--err) 35%, transparent);
        }}

        /* Image Box */
        .product-image-box {{
            width: 100%;
            height: 220px;
            background: var(--card2);
            border: 1px solid var(--line);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .product-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 10px;
            transition: transform .38s ease;
        }}
        .product-card:hover .product-img {{
            transform: scale(1.03);
        }}

        /* Card Content */
        .card-body {{
            display: flex;
            flex-direction: column;
            gap: 14px;
            flex: 1;
        }}
        .product-title {{
            font-family: var(--serif);
            font-weight: 500;
            font-size: 21px;
            line-height: 1.25;
            letter-spacing: -.01em;
            color: var(--fg);
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin: 0;
        }}

        /* BSR & Price Meta Box */
        .bsr-meta-box {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            background: var(--card2);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px 14px;
        }}
        .meta-item {{ display: flex; flex-direction: column; gap: 3px; }}
        .meta-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: .08em;
            color: var(--muted);
            font-weight: 600;
        }}
        .meta-val {{
            font-size: 15px;
            font-weight: 700;
            color: var(--fg);
            font-variant-numeric: tabular-nums;
        }}
        .meta-val.highlight {{ color: var(--accent); }}

        /* Arbitrage Stores Row */
        .stores-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }}
        .btn-store {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 9px 12px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 13px;
            text-decoration: none;
            cursor: pointer;
            transition: background .15s, border-color .15s, filter .15s;
        }}
        .btn-amazon {{
            background: var(--accent);
            color: var(--on-accent);
            border: none;
        }}
        .btn-amazon:hover {{ filter: brightness(1.06); }}
        .btn-walmart {{
            background: var(--card2);
            color: var(--fg);
            border: 1px solid var(--line);
        }}
        .btn-walmart:hover {{
            border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
        }}

        /* Marketing & Commercial Insights */
        .insights-box {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            background: var(--card2);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 14px;
        }}
        .insight-row {{ display: flex; flex-direction: column; gap: 4px; }}
        .insight-label-why {{
            font-size: 11.5px;
            text-transform: uppercase;
            letter-spacing: .18em;
            font-weight: 700;
            color: var(--accent2);
        }}
        .insight-label-risk {{
            font-size: 11.5px;
            text-transform: uppercase;
            letter-spacing: .18em;
            font-weight: 700;
            color: var(--warn);
        }}
        .insight-text {{
            font-size: 13.5px;
            line-height: 1.45;
            color: var(--fg);
            margin: 0;
        }}

        /* Marketing Angles Container */
        .angles-container {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 2px;
        }}
        .angle-item {{
            background: var(--card2);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .angle-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .angle-title {{
            font-size: 11.5px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .14em;
            color: var(--accent2);
        }}
        .btn-copy-angle {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 3px 9px;
            font-size: 11.5px;
            font-weight: 600;
            color: var(--muted);
            cursor: pointer;
            transition: all .2s;
        }}
        .btn-copy-angle:hover {{
            border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
            color: var(--fg);
        }}
        .angle-text {{
            font-size: 13px;
            line-height: 1.4;
            color: var(--fg);
            margin: 0;
        }}

        /* Empty State */
        .empty-state {{
            grid-column: 1 / -1;
            background: var(--card);
            border: 1px dashed var(--line);
            border-radius: 18px;
            padding: 48px 24px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}
        .empty-icon {{ font-size: 44px; }}
        .empty-title {{
            font-family: var(--serif);
            font-weight: 500;
            font-size: 22px;
            color: var(--fg);
        }}
        .empty-desc {{
            color: var(--muted);
            font-size: 14.5px;
            max-width: 50ch;
            line-height: 1.5;
        }}

        /* Pagination Controls */
        .pagination-wrapper {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            padding: 20px 4px;
            border-top: 1px solid var(--line);
            margin-top: 10px;
        }}
        .pagination-buttons {{
            display: flex;
            align-items: center;
            gap: 5px;
            flex-wrap: wrap;
        }}
        .page-btn {{
            font: inherit;
            font-size: 13px;
            font-weight: 600;
            min-width: 36px;
            height: 36px;
            padding: 0 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            border: 1px solid var(--line);
            background: var(--card);
            color: var(--fg);
            cursor: pointer;
            transition: all .2s;
        }}
        .page-btn:hover:not(:disabled) {{
            border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
            background: var(--card2);
        }}
        .page-btn.active {{
            background: var(--accent) !important;
            color: var(--on-accent) !important;
            border-color: var(--accent) !important;
        }}
        .page-btn:disabled {{
            opacity: .4;
            cursor: not-allowed;
        }}
        .page-ellipsis {{
            min-width: 24px;
            text-align: center;
            color: var(--muted);
        }}
        .pagination-size-selector {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--muted);
        }}
        .pagination-size-selector select {{
            width: auto;
            padding: 6px 10px;
            border-radius: 10px;
            background: var(--card2);
            border: 1px solid var(--line);
            color: var(--fg);
            font: inherit;
            font-size: 12.5px;
        }}

        /* Floating Side Quick Price Filter */
        .floating-side-widget {{
            position: fixed;
            bottom: 24px;
            left: 24px;
            z-index: 900;
        }}
        .floating-side-btn {{
            background: var(--card);
            border: 1px solid var(--line);
            color: var(--fg);
            border-radius: 99px;
            padding: 9px 16px;
            font-size: 13px;
            font-weight: 600;
            box-shadow: var(--shadow);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all .2s;
        }}
        .floating-side-btn:hover {{
            border-color: var(--accent);
            background: var(--card2);
        }}
        .floating-side-btn.active {{
            background: var(--accent);
            color: var(--on-accent);
            border-color: var(--accent);
        }}

        /* Toast Messages */
        .toast-msg {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: var(--card2);
            border: 1px solid var(--line);
            border-left: 3px solid var(--accent);
            color: var(--fg);
            padding: 12px 18px;
            border-radius: 12px;
            box-shadow: var(--shadow);
            z-index: 9999;
            display: none;
            font-size: 13.5px;
            font-weight: 600;
            transition: opacity .3s ease;
        }}

        /* Login Screen Overlay (Reel Factory .dlg style) */
        .login-overlay {{
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: #000a;
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .login-card {{
            background: var(--card);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 34px;
            width: min(440px, 100%);
            box-shadow: var(--shadow);
            display: flex;
            flex-direction: column;
            gap: 16px;
            text-align: center;
        }}
        .login-icon {{ font-size: 34px; margin-bottom: -4px; }}
        .login-title {{
            font-family: var(--serif);
            font-weight: 500;
            font-size: 26px;
            letter-spacing: -.01em;
            color: var(--fg);
            margin: 0;
        }}
        .login-subtitle {{
            font-size: 11.5px;
            text-transform: uppercase;
            letter-spacing: .18em;
            font-weight: 700;
            color: var(--accent2);
            margin: -6px 0 6px;
        }}
        .login-error {{
            display: none;
            background: color-mix(in srgb, var(--err) 12%, var(--card));
            border: 1px solid color-mix(in srgb, var(--err) 40%, transparent);
            color: var(--err);
            border-radius: 10px;
            padding: 8px 12px;
            font-size: 12.5px;
            font-weight: 600;
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
            font-size: 12px;
            font-weight: 600;
            color: var(--muted);
        }}
        .login-input {{
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: var(--card2);
            color: var(--fg);
            font: inherit;
        }}
        .login-input:focus {{
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 24%, transparent);
        }}
        .login-options {{ display: flex; justify-content: space-between; align-items: center; }}
        .remember-label {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12.5px;
            color: var(--muted);
            cursor: pointer;
        }}
        .remember-label input {{ accent-color: var(--accent); }}
        .btn-submit-login {{
            background: var(--accent);
            color: var(--on-accent);
            border: none;
            border-radius: 12px;
            padding: 12px;
            font-size: 14.5px;
            font-weight: 700;
            cursor: pointer;
            transition: filter .15s;
            margin-top: 6px;
        }}
        .btn-submit-login:hover {{ filter: brightness(1.06); }}

        
        /* Fix 2 (R-25): Day Mode Contrast Corrections (WCAG AA > 4.5:1) */
        :root[data-mode="day"] .status-pill.badge-winner {{
            color: var(--accent2);
            border-color: color-mix(in srgb, var(--accent2) 35%, transparent);
            background: color-mix(in srgb, var(--accent2) 14%, transparent);
        }}
        :root[data-mode="day"] .meta-val.highlight {{
            color: var(--accent2);
        }}
        :root[data-mode="day"] .display em {{
            color: var(--accent2);
        }}
        :root[data-mode="day"] .greet em {{
            color: var(--accent2);
        }}
        :root[data-mode="day"] .kpi-num.v[style*="var(--accent)"] {{
            color: var(--accent2) !important;
        }}

        /* Media Queries (Responsive at 375px, 768px, 1440px) */
        @media (max-width: 1000px) {{
            .app {{ grid-template-columns: 1fr; }}
            .side {{ display: none; }}
            .topbar, .content-body {{ padding-left: 14px; padding-right: 14px; }}
        }}
        @media (max-width: 760px) {{
            .hero-in {{ padding: 26px 20px; }}
            .display {{ font-size: 30px; }}
            .toolbar {{ flex-direction: column; align-items: stretch; }}
            .toolbar-side-actions {{ margin-left: 0; width: 100%; justify-content: space-between; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            * {{ animation-iteration-count: 1 !important; }}
        }}
    </style>
</head>
<body>
    <!-- SVG Icon Symbols (Reel Factory Design System) -->
    <svg width="0" height="0" style="position:absolute;display:none" aria-hidden="true">
        <symbol id="i-home" viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></symbol>
        <symbol id="i-box" viewBox="0 0 24 24"><path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/></symbol>
        <symbol id="i-play" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="m10 9 5 3-5 3z"/></symbol>
        <symbol id="i-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></symbol>
        <symbol id="i-moon" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></symbol>
        <symbol id="i-check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></symbol>
        <symbol id="i-compass" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/></symbol>
        <symbol id="i-alert" viewBox="0 0 24 24"><path d="M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/></symbol>
        <symbol id="i-focus" viewBox="0 0 24 24"><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><circle cx="12" cy="12" r="3"/></symbol>
        <symbol id="i-refresh" viewBox="0 0 24 24"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></symbol>
    </svg>

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

    <!-- Main Dashboard Container -->
    <div class="dashboard-container" id="dashboardContainer" style="display: none;">
        <div class="app">
            <!-- Sticky Sidebar (248px) -->
            <aside class="side">
                <div class="logo">
                    <svg class="mark" viewBox="0 0 34 34" aria-hidden="true">
                        <rect width="34" height="34" rx="10" fill="var(--accent)"/>
                        <path d="M7 23c4.5-8 7.5-11 10-11s5.5 3 10 11" fill="none" stroke="var(--on-accent)" stroke-width="2.6" stroke-linecap="round"/>
                        <circle cx="24" cy="10.5" r="2.7" fill="var(--on-accent)"/>
                    </svg>
                    RV Winner Scout
                </div>
                <nav class="nav" id="sidebarNav">
                    <a href="#cardsGrid" class="on" data-tab="all" onclick="setFilter('all', this); return false;">
                        <svg class="i"><use href="#i-home"/></svg>All Products <span class="ct" id="sideCountAll">{total_count}</span>
                    </a>
                    <a href="#cardsGrid" data-tab="winner" onclick="setFilter('winner', this); return false;">
                        <svg class="i"><use href="#i-box"/></svg>Winners <span class="ct" id="sideCountWinners">{winners_count}</span>
                    </a>
                    <a href="#cardsGrid" data-tab="should_test" onclick="setFilter('should_test', this); return false;">
                        <svg class="i"><use href="#i-play"/></svg>Should Test <span class="ct" id="sideCountShouldTest">{should_test_count}</span>
                    </a>
                    <a href="#cardsGrid" data-tab="candidate" onclick="setFilter('candidate', this); return false;">
                        <svg class="i"><use href="#i-compass"/></svg>Candidates <span class="ct" id="sideCountCandidates">{candidates_count}</span>
                    </a>
                </nav>
                <div class="sp"></div>
                <div class="machine" id="machine">
                    <b>Scout Intelligence</b>
                    <span>Autonomous 24/7 Scan</span>
                    <div class="meter"><span style="width:100%"></span></div>
                    <span>Daily Catalog Audit</span>
                </div>
                <div class="statuspill" id="sideStatus">
                    <span class="dot"></span><span id="sideStatusText">Live Feed Active</span>
                </div>
                <div class="copy">© 2026 Almostafa · All rights reserved</div>
            </aside>

            <!-- Main Content Area -->
            <div class="mainwrap">
                <!-- Topbar -->
                <header class="topbar">
                    <div class="greet">RV Market Scout · <em>Daily Winners Feed</em> ({run_date})</div>

                    <!-- Theme Selector Dropdown (Reel Factory 5 Themes) -->
                    <div class="theme-select-wrap">
                        <select id="themeSelector" class="theme-dropdown" onchange="setThemeName(this.value)" title="Choose theme">
                            <option value="campfire">🏕️ Campfire</option>
                            <option value="forest">🌲 Forest</option>
                            <option value="lakeside">🌊 Lakeside</option>
                            <option value="ember">🔥 Ember</option>
                            <option value="desert">🏜️ Desert</option>
                        </select>
                    </div>

                    <!-- Day / Night Mode Toggle (Reel Factory logic) -->
                    <button id="btnMode" class="btn modebtn" onclick="toggleDayNight()" title="Day or night - current window">
                        <svg class="i"><use href="#i-moon"/></svg><span id="modeLabel">Night</span>
                    </button>

                    <!-- Refresh Feed Button -->
                    <button id="refreshBtn" class="btn" onclick="manualRefresh()" title="Click to refresh latest discoveries">
                        <span id="refreshIcon" class="refresh-icon">🔄</span>
                        <span id="refreshText">Refresh Feed</span>
                    </button>

                    <!-- Sign Out Button -->
                    <button class="btn btn-logout" onclick="logout()" title="Sign Out">
                        🔒 Sign Out
                    </button>
                </header>

                <!-- Content Body -->
                <div class="content-body">
                    <!-- Hero Banner -->
                    <section class="hero" id="hero" aria-label="Welcome">
                        <div class="hero-in">
                            <div class="kick">RV MARKET INTELLIGENCE</div>
                            <h1 class="display">Find the <em>winning</em> RV products first.</h1>
                            <p>Automated market scout evaluating Facebook ad viability, problem-solving score, and competitor exposure.</p>
                            <div class="hero-acts">
                                <button class="btn pri" onclick="document.getElementById('searchInput').focus();"><svg class="i"><use href="#i-box"/></svg>Explore Catalog</button>
                                <button class="btn" onclick="setFilter('winner', document.querySelector('.filter-btn[data-type=winner]'));"><svg class="i"><use href="#i-play"/></svg>View Winners ({winners_count})</button>
                            </div>
                        </div>
                    </section>

                    <!-- KPI Tiles (Reel Factory .tiles and .tile) -->
                    <section class="kpi-row tiles">
                        <div class="tile">
                            <div class="ic" style="--c: var(--accent);"><svg class="i"><use href="#i-box"/></svg></div>
                            <div>
                                <div class="kpi-label k">Audited Products</div>
                                <div class="kpi-num v">{reviewed_count}</div>
                                <div class="s">Across all categories</div>
                            </div>
                        </div>

                        <div class="tile">
                            <div class="ic" style="--c: var(--ok);"><svg class="i"><use href="#i-check"/></svg></div>
                            <div>
                                <div class="kpi-label k">Qualified Winners</div>
                                <div class="kpi-num v" style="color: var(--accent)">{winners_count}</div>
                                <div class="s">Score ≥ 80.0</div>
                            </div>
                        </div>

                        <div class="tile">
                            <div class="ic" style="--c: var(--run);"><svg class="i"><use href="#i-play"/></svg></div>
                            <div>
                                <div class="kpi-label k">Should Be Tested</div>
                                <div class="kpi-num v" style="color: var(--run)">{should_test_count}</div>
                                <div class="s">High Potential</div>
                            </div>
                        </div>

                        <div class="tile">
                            <div class="ic" style="--c: var(--warn);"><svg class="i"><use href="#i-alert"/></svg></div>
                            <div>
                                <div class="kpi-label k">Changes Detected</div>
                                <div class="kpi-num v" style="color: var(--muted)">{health.products_changed}</div>
                                <div class="s">📈 {health.products_improved} Improved • 📉 {health.products_declined} Declined</div>
                            </div>
                        </div>

                        <div class="tile">
                            <div class="ic" style="--c: var(--muted);"><svg class="i"><use href="#i-focus"/></svg></div>
                            <div>
                                <div class="kpi-label k">Filtered / Sub-Threshold</div>
                                <div class="kpi-num v">{health.products_rejected}</div>
                                <div class="s">Archived / Filtered</div>
                            </div>
                        </div>
                    </section>

                    <!-- Filter Toolbar -->
                    <section class="toolbar">
                        <input type="text" id="searchInput" class="search-input" placeholder="Search by product title or ASIN..." onkeyup="filterCards()" />

                        <div class="filter-tabs">
                            <button class="filter-btn active" data-type="all" onclick="setFilter('all', this)">All ({total_count})</button>
                            <button class="filter-btn" data-type="winner" onclick="setFilter('winner', this)"><svg class="i" style="width:14px;height:14px;vertical-align:-2px"><use href="#i-check"/></svg> Winners ({winners_count})</button>
                            <button class="filter-btn" data-type="should_test" onclick="setFilter('should_test', this)"><svg class="i" style="width:14px;height:14px;vertical-align:-2px"><use href="#i-play"/></svg> Should Be Tested ({should_test_count})</button>
                            <button class="filter-btn" data-type="candidate" onclick="setFilter('candidate', this)"><svg class="i" style="width:14px;height:14px;vertical-align:-2px"><use href="#i-compass"/></svg> Candidates ({candidates_count})</button>
                            {changed_tab_btn}
                        </div>

                        <!-- Side Actions: Price Filter Toggle & Sorting -->
                        <div class="toolbar-side-actions">
                            <button id="priceFilterBtn" class="price-toggle-btn" onclick="togglePriceFilter(this)" title="Toggle hiding products over $100">
                                <span class="price-toggle-icon">🏷️</span>
                                <span id="priceToggleText">Hide &gt; $100 (≤ $100 Only)</span>
                            </button>

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
                        </div>
                    </section>

                    <!-- Floating Quick Price Toggle on the Side -->
                    <div class="floating-side-widget" id="floatingPriceWidget">
                        <button id="floatingPriceBtn" class="floating-side-btn" onclick="togglePriceFilter(this)" title="Click to show/hide products over $100">
                            <span class="float-icon">💵</span>
                            <span id="floatingPriceText">≤ $100 Only</span>
                        </button>
                    </div>

                    <!-- Results Top Meta -->
                    <div class="results-meta-bar" id="topResultsBar">
                        <div id="topPaginationInfo">Showing <span id="topRangeText">1–24</span> of <span id="topTotalText">{total_count}</span> products</div>
                    </div>

                    
                    <!-- Client-side No Results State (Fix 3: R-27) -->
                    <div id="noResultsState" class="empty-state" style="display: none; width: 100%; margin-bottom: 20px;">
                        <div class="empty-icon"><svg class="i" style="width:40px;height:40px;color:var(--muted);"><use href="#i-box"/></svg></div>
                        <h3 class="empty-title">No products match your current filters</h3>
                        <p class="empty-desc">Try clearing the search query or resetting filters to view all audited products.</p>
                        <button class="btn pri" onclick="resetFilters()">Reset All Filters</button>
                    </div>

                    <!-- Product Cards Grid -->
                    <main class="cards-grid" id="cardsGrid">
                        {cards_html if cards_html else empty_state_html}
                    </main>

                    <!-- Bottom Pagination Controls -->
                    <div class="pagination-wrapper" id="paginationWrapper">
                        <div class="pagination-buttons" id="paginationNav"></div>
                        <div class="pagination-size-selector">
                            <label for="pageSizeSelect">Show per page:</label>
                            <select id="pageSizeSelect" onchange="changePageSize(this.value)">
                                <option value="24" selected>24</option>
                                <option value="48">48</option>
                                <option value="96">96</option>
                                <option value="all">All</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast Notification Box -->
    <div id="toast" class="toast-msg"></div>

    <script>
        // Reel Factory Look & Theme Engine
        const THEMES = [
            ["campfire", "Campfire"],
            ["forest", "Forest"],
            ["lakeside", "Lakeside"],
            ["ember", "Ember"],
            ["desert", "Desert"]
        ];

        const look = {{
            theme: "campfire",
            mode: "night",
            session: ""
        }};

        try {{
            look.theme = localStorage.getItem("rf_theme") || look.theme;
            look.mode = localStorage.getItem("rf_start") || look.mode;
            look.session = sessionStorage.getItem("rf_mode_s") || "";
        }} catch(e) {{}}

        const clockMode = () => {{
            const h = new Date().getHours();
            return (h >= 6 && h < 18) ? "day" : "night";
        }};

        let switchTimer = null;
        function applyLook(animate = true) {{
            const d = document.documentElement;
            const mode = look.session || (look.mode === "auto" ? clockMode() : look.mode);
            const changed = (d.dataset.mode !== mode || d.dataset.theme !== look.theme);
            const commit = () => {{
                d.dataset.theme = look.theme;
                d.dataset.mode = mode;
            }};
            if (changed && animate) {{
                d.classList.add("switching");
                clearTimeout(switchTimer);
                switchTimer = setTimeout(() => d.classList.remove("switching", "vt"), 4200);
                if (document.startViewTransition) {{
                    d.classList.add("vt");
                    try {{
                        document.startViewTransition(commit);
                        setTimeout(commit, 2500);
                    }} catch(e) {{
                        d.classList.remove("vt");
                        commit();
                    }}
                }} else {{
                    commit();
                }}
            }} else {{
                commit();
            }}
            try {{
                localStorage.setItem("rf_theme", look.theme);
                localStorage.setItem("rf_start", look.mode);
            }} catch(e) {{}}

            const btn = document.getElementById("btnMode");
            if (btn) {{
                const iconUse = btn.querySelector("use");
                if (iconUse) iconUse.setAttribute("href", mode === "night" ? "#i-moon" : "#i-sun");
                const lbl = document.getElementById("modeLabel");
                if (lbl) lbl.textContent = mode === "night" ? "Night" : "Day";
                btn.title = (mode === "night" ? "Switch to day" : "Switch to night") + " (until you close the window - the tool always opens in " + (look.mode === "auto" ? "the clock's mode" : look.mode) + ")";
            }}
            const sel = document.getElementById("themeSelector");
            if (sel && sel.value !== look.theme) {{
                sel.value = look.theme;
            }}
        }}

        function setThemeName(theme) {{
            if (THEMES.some(t => t[0] === theme)) {{
                look.theme = theme;
                applyLook(true);
            }}
        }}

        function setTheme(theme) {{
            const map = {{ "slate": "campfire", "midnight": "lakeside", "graphite": "forest", "light": "campfire" }};
            setThemeName(map[theme] || theme);
        }}

        function toggleDayNight() {{
            const currentMode = document.documentElement.dataset.mode || "night";
            look.session = currentMode === "night" ? "day" : "night";
            try {{ sessionStorage.setItem("rf_mode_s", look.session); }} catch(e) {{}}
            applyLook(true);
        }}

        // Client-side authentication credentials
        const AUTH_USER = "Almostafa";
        const AUTH_HASH = "d7f6bc259795aebde3360364c91c781ac93edc0feaa81dead8d512f40376d726"; // SHA-256 of 'Almostafa311911@z'

        async function sha256(message) {{
            const msgBuffer = new TextEncoder().encode(message);
            const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        }}

        function checkAuth() {{
            const isAuth = localStorage.getItem('scout_auth') === 'true' || sessionStorage.getItem('scout_auth') === 'true';
            if (isAuth) {{
                document.getElementById('loginOverlay').style.display = 'none';
                document.getElementById('dashboardContainer').style.display = 'block';
            }} else {{
                document.getElementById('loginOverlay').style.display = 'flex';
                document.getElementById('dashboardContainer').style.display = 'none';
            }}
        }}

        async function attemptLogin() {{
            const user = document.getElementById('loginUser').value.trim();
            const pass = document.getElementById('loginPass').value;
            const remember = document.getElementById('rememberMe').checked;
            const errBox = document.getElementById('loginError');

            const hashed = await sha256(pass);

            if (user.toLowerCase() === AUTH_USER.toLowerCase() && hashed === AUTH_HASH) {{
                errBox.style.display = 'none';
                if (remember) {{
                    localStorage.setItem('scout_auth', 'true');
                }} else {{
                    sessionStorage.setItem('scout_auth', 'true');
                }}
                document.getElementById('loginOverlay').style.display = 'none';
                document.getElementById('dashboardContainer').style.display = 'block';
            }} else {{
                errBox.style.display = 'block';
                document.getElementById('loginPass').value = '';
                document.getElementById('loginPass').focus();
            }}
        }}

        function logout() {{
            localStorage.removeItem('scout_auth');
            sessionStorage.removeItem('scout_auth');
            checkAuth();
        }}

        // Client-side filtering & search
        let currentFilter = 'all';
        let hideOver100 = false;
        try {{
            hideOver100 = localStorage.getItem('scout_hide_over_100') === 'true';
        }} catch(e) {{}}

        // Pagination State
        let currentPage = 1;
        let itemsPerPage = 24;
        let matchingCards = [];

        function setFilter(type, btn) {{
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(b => {{
                b.classList.toggle('active', b.getAttribute('data-type') === type || b === btn);
            }});
            document.querySelectorAll('#sidebarNav a').forEach(a => {{
                a.classList.toggle('on', a.getAttribute('data-tab') === type);
            }});
            filterCards();
        }}

        function togglePriceFilter(btn) {{
            hideOver100 = !hideOver100;
            try {{
                localStorage.setItem('scout_hide_over_100', hideOver100 ? 'true' : 'false');
            }} catch(e) {{}}
            updatePriceFilterButtons();
            filterCards();
        }}

        function updatePriceFilterButtons() {{
            const mainBtn = document.getElementById('priceFilterBtn');
            const floatBtn = document.getElementById('floatingPriceBtn');
            const mainText = document.getElementById('priceToggleText');
            const floatText = document.getElementById('floatingPriceText');

            if (hideOver100) {{
                if (mainBtn) mainBtn.classList.add('active');
                if (floatBtn) floatBtn.classList.add('active');
                if (mainText) mainText.textContent = "Showing ≤ $100 Only (Click to Show All)";
                if (floatText) floatText.textContent = "≤ $100 (Active)";
            }} else {{
                if (mainBtn) mainBtn.classList.remove('active');
                if (floatBtn) floatBtn.classList.remove('active');
                if (mainText) mainText.textContent = "Hide > $100 (≤ $100 Only)";
                if (floatText) floatText.textContent = "≤ $100 Only";
            }}
        }}

        function filterCards() {{
            const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();
            const cards = Array.from(document.querySelectorAll('.product-card'));
            matchingCards = [];

            cards.forEach(card => {{
                const title = card.getAttribute('data-title') || '';
                const type = card.getAttribute('data-type') || '';
                const changed = card.getAttribute('data-changed') || 'none';
                const price = parseFloat(card.getAttribute('data-price')) || 0.0;

                const matchesSearch = !searchVal || title.includes(searchVal);
                let matchesTab = false;
                if (currentFilter === 'all') {{
                    matchesTab = true;
                }} else if (currentFilter === 'changed') {{
                    matchesTab = (changed === 'improved' || changed === 'declined');
                }} else {{
                    matchesTab = (type === currentFilter);
                }}

                const matchesPrice = !hideOver100 || (price > 0.0 && price <= 100.0);

                if (matchesSearch && matchesTab && matchesPrice) {{
                    matchingCards.push(card);
                }} else {{
                    card.classList.remove('page-active');
                }}
            }});

            const grid = document.getElementById('cardsGrid');
            if (grid) grid.classList.add('initialized');

            goToPage(1);
        }}

                function resetFilters() {{
            const searchInput = document.getElementById('searchInput');
            if (searchInput) searchInput.value = '';
            hideOver100 = false;
            try {{ localStorage.setItem('scout_hide_over_100', 'false'); }} catch(e) {{}}
            updatePriceFilterButtons();
            setFilter('all');
        }}

        function renderCurrentPage() {{
            const total = matchingCards.length;
            const cards = document.querySelectorAll('.product-card');
            cards.forEach(c => c.classList.remove('page-active'));

            if (itemsPerPage === 'all') {{
                matchingCards.forEach(c => c.classList.add('page-active'));
                updateResultsBar(1, total, total, 1, 1);
                renderPaginationNav(1, 1);
                return;
            }}

            const perPage = parseInt(itemsPerPage, 10) || 24;
            const totalPages = Math.max(1, Math.ceil(total / perPage));
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            const startIndex = (currentPage - 1) * perPage;
            const endIndex = Math.min(startIndex + perPage, total);

            for (let i = startIndex; i < endIndex; i++) {{
                if (matchingCards[i]) {{
                    matchingCards[i].classList.add('page-active');
                }}
            }}

            updateResultsBar(total > 0 ? startIndex + 1 : 0, endIndex, total, currentPage, totalPages);
            const noRes = document.getElementById('noResultsState');
            if (noRes) noRes.style.display = (total === 0) ? 'flex' : 'none';
            renderPaginationNav(currentPage, totalPages);
        }}

        function updateResultsBar(start, end, total, page, totalPages) {{
            const rangeSpan = document.getElementById('topRangeText');
            const totalSpan = document.getElementById('topTotalText');
            if (rangeSpan) {{
                rangeSpan.textContent = total > 0 ? (start + '–' + end) : '0';
            }}
            if (totalSpan) {{
                totalSpan.textContent = total.toLocaleString() + ' products (Page ' + page + ' of ' + totalPages + ')';
            }}
        }}

        function goToPage(page) {{
            currentPage = page;
            renderCurrentPage();
            const topBar = document.getElementById('topResultsBar');
            if (topBar && window.scrollY > topBar.offsetTop + 200) {{
                topBar.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }}

        function changePageSize(size) {{
            itemsPerPage = (size === 'all') ? 'all' : (parseInt(size, 10) || 24);
            goToPage(1);
        }}

        function renderPaginationNav(page, totalPages) {{
            const nav = document.getElementById('paginationNav');
            if (!nav) return;
            if (itemsPerPage === 'all' || totalPages <= 1) {{
                nav.innerHTML = '<span class="page-ellipsis" style="font-size:12px;color:var(--muted);">All ' + matchingCards.length + ' results shown</span>';
                return;
            }}

            let html = '';
            const prevDisabled = page <= 1 ? 'disabled' : '';
            html += '<button class="page-btn" ' + prevDisabled + ' onclick="goToPage(' + (page - 1) + ')" title="Previous Page">← Prev</button>';

            const maxVisibleButtons = 7;
            let startP = Math.max(1, page - 2);
            let endP = Math.min(totalPages, page + 2);

            if (startP > 1) {{
                html += '<button class="page-btn ' + (page === 1 ? 'active' : '') + '" onclick="goToPage(1)">1</button>';
                if (startP > 2) html += '<span class="page-ellipsis">…</span>';
            }}

            for (let p = startP; p <= endP; p++) {{
                const activeClass = (p === page) ? 'active' : '';
                html += '<button class="page-btn ' + activeClass + '" onclick="goToPage(' + p + ')">' + p + '</button>';
            }}

            if (endP < totalPages) {{
                if (endP < totalPages - 1) html += '<span class="page-ellipsis">…</span>';
                html += '<button class="page-btn ' + (page === totalPages ? 'active' : '') + '" onclick="goToPage(' + totalPages + ')">' + totalPages + '</button>';
            }}

            const nextDisabled = page >= totalPages ? 'disabled' : '';
            html += '<button class="page-btn ' + nextDisabled + '" onclick="goToPage(' + (page + 1) + ')" title="Next Page">Next →</button>';

            nav.innerHTML = html;
        }}

        function sortCards(sortKey) {{
            const grid = document.getElementById('cardsGrid');
            if (!grid) return;
            const cards = Array.from(grid.querySelectorAll('.product-card'));

            cards.sort((a, b) => {{
                const scoreA = parseFloat(a.getAttribute('data-score')) || 0;
                const scoreB = parseFloat(b.getAttribute('data-score')) || 0;
                const priceA = parseFloat(a.getAttribute('data-price')) || 0;
                const priceB = parseFloat(b.getAttribute('data-price')) || 0;
                const bsrA = parseInt(a.getAttribute('data-bsr')) || 9999999;
                const bsrB = parseInt(b.getAttribute('data-bsr')) || 9999999;

                if (sortKey === 'score-desc') return scoreB - scoreA;
                if (sortKey === 'score-asc') return scoreA - scoreB;
                if (sortKey === 'price-desc') return priceB - priceA;
                if (sortKey === 'price-asc') return priceA - priceB;
                if (sortKey === 'bsr-asc') return bsrA - bsrB;
                return 0;
            }});

            cards.forEach(card => grid.appendChild(card));
            filterCards();
        }}

        function manualRefresh() {{
            const icon = document.getElementById('refreshIcon');
            const text = document.getElementById('refreshText');
            if (icon) icon.style.animation = 'spin 1s linear infinite';
            if (text) text.textContent = 'Updating...';

            showToast("Fetching latest discovered products...");
            setTimeout(() => {{
                window.location.reload();
            }}, 800);
        }}

        function copyMarketingAngle(btn) {{
            const angleItem = btn.closest('.angle-item');
            const angleTextEl = angleItem.querySelector('.angle-text');
            const textToCopy = angleTextEl ? angleTextEl.textContent.trim() : '';

            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(textToCopy).then(() => {{
                    flashCopySuccess(btn);
                }}).catch(err => {{
                    fallbackCopyTextToClipboard(textToCopy, btn);
                }});
            }} else {{
                fallbackCopyTextToClipboard(textToCopy, btn);
            }}
        }}

        function fallbackCopyTextToClipboard(text, btn) {{
            const textArea = document.createElement("textarea");
            textArea.value = text;
            textArea.style.position = "fixed";
            textArea.style.top = "-9999px";
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {{
                document.execCommand('copy');
                flashCopySuccess(btn);
            }} catch (err) {{
                showToast("Failed to copy angle.");
            }}
            document.body.removeChild(textArea);
        }}

        function flashCopySuccess(btn) {{
            const originalText = btn.innerHTML;
            btn.innerHTML = '✓ Copied!';
            btn.style.color = 'var(--accent)';
            btn.style.borderColor = 'var(--accent)';
            showToast("Marketing angle copied to clipboard!");

            setTimeout(() => {{
                btn.innerHTML = originalText;
                btn.style.color = '';
                btn.style.borderColor = '';
            }}, 2000);
        }}

        function showToast(message) {{
            const toast = document.getElementById('toast');
            if (!toast) return;
            toast.textContent = message;
            toast.style.display = 'block';
            toast.style.opacity = '1';
            setTimeout(() => {{
                toast.style.opacity = '0';
                setTimeout(() => {{ toast.style.display = 'none'; }}, 300);
            }}, 3500);
        }}

        // Initialization
        applyLook(false);
        updatePriceFilterButtons();
        filterCards();
        checkAuth();
    </script>
</body>
</html>"""
    return html_content


def merge_html_with_existing(new_html: str, existing_html: str) -> str:
    """Merges new dashboard HTML with an existing dashboard HTML, preserving historical products."""
    def parse_cards(html_doc: str) -> dict:
        cards = {}
        grid_idx = html_doc.find('<main class="cards-grid" id="cardsGrid">')
        if grid_idx == -1:
            return cards
        main_content = html_doc[grid_idx:]
        end_main_idx = main_content.find('</main>')
        cards_section = main_content[:end_main_idx]

        raw_cards = cards_section.split('<div class="product-card')
        for rc in raw_cards[1:]:
            card_html = '<div class="product-card' + rc
            card_html = card_html.rstrip()

            m_asin = re.search(r'<span class="asin-pill">ASIN: ([^<]+)</span>', card_html)
            if not m_asin:
                m_asin = re.search(r'data-asin="([^"]+)"', card_html)
            if not m_asin:
                m_asin = re.search(r'B0[A-Z0-9]{8}', card_html)

            if m_asin:
                asin = m_asin.group(1) if m_asin.groups() else m_asin.group(0)
                m_type = re.search(r'data-type="([^"]+)"', card_html)
                card_type = m_type.group(1) if m_type else 'candidate'
                m_score = re.search(r'data-score="([^"]+)"', card_html)
                score = float(m_score.group(1)) if m_score else 0.0
                cards[asin] = {
                    'asin': asin,
                    'type': card_type,
                    'score': score,
                    'html': card_html
                }
        return cards

    existing_cards = parse_cards(existing_html)
    new_cards = parse_cards(new_html)

    if not existing_cards:
        return new_html

    # Merge: existing as base, new updates/adds
    merged = dict(existing_cards)
    merged.update(new_cards)

    # Sort: Winners first (score desc), Should-Test next (score desc), Candidates next (score desc)
    type_priority = {'winner': 0, 'should_test': 1, 'should_be_tested': 1, 'candidate': 2}
    sorted_cards = sorted(
        merged.values(),
        key=lambda c: (type_priority.get(c['type'], 3), -c['score'])
    )

    winners_count = sum(1 for c in sorted_cards if c['type'] == 'winner')
    should_test_count = sum(1 for c in sorted_cards if 'should' in c['type'])
    candidates_count = len(sorted_cards) - winners_count - should_test_count

    # Replace cards section in new_html
    grid_tag = '<main class="cards-grid" id="cardsGrid">'
    grid_start = new_html.find(grid_tag)
    if grid_start == -1:
        return new_html
    grid_end = new_html.find('</main>', grid_start)
    if grid_end == -1:
        return new_html

    header_part = new_html[:grid_start + len(grid_tag)]
    footer_part = new_html[grid_end:]
    cards_body = "\n        " + "\n        ".join(c['html'] for c in sorted_cards) + "\n    "
    merged_html = header_part + cards_body + footer_part

    # Update KPIs
    merged_html = re.sub(
        r'(<div class="kpi-label">Audited Products</div>\s*<div class="kpi-num"[^>]*>)[^<]+(</div>)',
        rf'\g<1>{len(sorted_cards)}\g<2>',
        merged_html
    )
    merged_html = re.sub(
        r'(<div class="kpi-label">Qualified Winners</div>\s*<div class="kpi-num"[^>]*>)[^<]+(</div>)',
        rf'\g<1>{winners_count}\g<2>',
        merged_html
    )
    merged_html = re.sub(
        r'(<div class="kpi-label">Should Be Tested</div>\s*<div class="kpi-num"[^>]*>)[^<]+(</div>)',
        rf'\g<1>{should_test_count}\g<2>',
        merged_html
    )
    # Update Filter Tabs
    merged_html = re.sub(r'All \(\d+\)', f'All ({len(sorted_cards)})', merged_html)
    merged_html = re.sub(r'Winners \(\d+\)', f'Winners ({winners_count})', merged_html)
    merged_html = re.sub(r'Should Be Tested \(\d+\)', f'Should Be Tested ({should_test_count})', merged_html)
    merged_html = re.sub(r'Candidates \(\d+\)', f'Candidates ({candidates_count})', merged_html)

    return merged_html


def export_catalog_json(html_doc: str, json_path: str) -> None:
    """Parses cards from dashboard HTML and writes a structured catalog.json."""
    grid_idx = html_doc.find('<main class="cards-grid" id="cardsGrid">')
    if grid_idx == -1:
        return
    end_main_idx = html_doc.find('</main>', grid_idx)
    cards_section = html_doc[grid_idx:end_main_idx]

    raw_cards = cards_section.split('<div class="product-card')
    catalog = []

    for rc in raw_cards[1:]:
        card_html = '<div class="product-card' + rc

        m_asin = re.search(r'<span class="asin-pill">ASIN: ([^<]+)</span>', card_html)
        asin = m_asin.group(1).strip() if m_asin else ""

        m_type = re.search(r'data-type="([^"]+)"', card_html)
        card_type = m_type.group(1).strip() if m_type else "candidate"

        m_score = re.search(r'data-score="([^"]+)"', card_html)
        score = float(m_score.group(1)) if m_score else 0.0

        m_price = re.search(r'data-price="([^"]+)"', card_html)
        price = float(m_price.group(1)) if m_price else 0.0

        m_bsr = re.search(r'data-bsr="([^"]+)"', card_html)
        bsr = int(m_bsr.group(1)) if m_bsr else 9999999

        m_title = re.search(r'<h3 class="product-title"[^>]*>([^<]+)</h3>', card_html)
        title = m_title.group(1).strip() if m_title else ""

        m_img = re.search(r'<img [^>]*src="([^"]+)"', card_html)
        img_url = m_img.group(1) if m_img else ""

        m_amz = re.search(r'href="([^"]+)"[^>]*class="btn-store btn-amazon"', card_html)
        amz_url = m_amz.group(1) if m_amz else f"https://www.amazon.com/dp/{asin}"

        m_wal = re.search(r'href="([^"]+)"[^>]*class="btn-store btn-walmart"', card_html)
        wal_url = m_wal.group(1) if m_wal else ""

        catalog.append({
            "asin": asin,
            "title": title,
            "type": card_type,
            "score": score,
            "price": price,
            "bsr": bsr,
            "image_url": img_url,
            "amazon_url": amz_url,
            "walmart_url": wal_url,
        })

    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)


def save_dashboard(
    reviewed_count: int,
    winners: List[ProductCandidate],
    near_misses: List[ProductCandidate],
    health: RunHealthReport,
    data_dir: str = "data",
    spreadsheet_id: Optional[str] = None,
    candidates: Optional[List[ProductCandidate]] = None,
    should_be_tested: Optional[List[ProductCandidate]] = None,
    cumulative: bool = True,
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

    # Cumulative merge: preserve historical products from prior runs (disabled during pytest)
    if cumulative and not os.environ.get("PYTEST_CURRENT_TEST"):
        existing_path = None
        for candidate_path in [
            os.path.join("public", "index.html"),
            os.path.join(data_dir, "reports", "index.html"),
            "index.html",
        ]:
            if os.path.isfile(candidate_path):
                existing_path = candidate_path
                break

        if existing_path:
            try:
                with open(existing_path, "r", encoding="utf-8") as f:
                    existing_html = f.read()
                html_str = merge_html_with_existing(html_str, existing_html)
            except Exception:
                pass

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

    # Also save structured JSON catalog in reports
    try:
        export_catalog_json(html_str, os.path.join(reports_dir, "catalog.json"))
    except Exception:
        pass

    # Sync to public/index.html and root index.html for Cloudflare Pages / Workers
    # Protect against test runs polluting production dashboard
    if data_dir == "data" and not os.environ.get("PYTEST_CURRENT_TEST"):
        public_dir = "public"
        os.makedirs(public_dir, exist_ok=True)
        with open(os.path.join(public_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html_str)

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_str)

        try:
            export_catalog_json(html_str, os.path.join(public_dir, "catalog.json"))
        except Exception:
            pass

    return filepath
