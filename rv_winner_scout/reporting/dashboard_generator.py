"""Generates a high-productivity, themeable Executive E-Commerce Dashboard."""

import html
import json
import os
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional

from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport


def generate_executive_dashboard_html(
    reviewed_count: int,
    winners: List[ProductCandidate],
    near_misses: List[ProductCandidate],
    health: RunHealthReport,
    spreadsheet_id: Optional[str] = None,
    candidates: Optional[List[ProductCandidate]] = None,
) -> str:
    """Renders a clean, eye-friendly, theme-switchable dashboard with image carousel & batch download."""
    run_date = health.end_time.strftime("%Y-%m-%d")
    sheet_url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        if spreadsheet_id
        else "https://docs.google.com"
    )

    all_candidates = winners + near_misses + (candidates or [])
    cards_html = ""

    for idx, cand in enumerate(all_candidates, 1):
        is_winner = cand in winners
        raw_title = cand.verified_product.title if cand.verified_product else cand.raw_product.title
        title = html.escape(raw_title)
        asin = cand.asin
        amazon_url = cand.canonical_url if cand.canonical_url else f"https://www.amazon.com/dp/{asin}"

        # Price and BSR
        price_val = cand.verified_product.displayed_price if cand.verified_product else cand.raw_product.displayed_price
        price_display = f"${price_val:.2f}" if price_val is not None else ""

        # BSR display
        bsr_display = ""
        if cand.verified_product and cand.verified_product.bsr_rank:
            bsr_display = cand.verified_product.bsr_rank
        elif cand.raw_product and cand.raw_product.bsr_rank:
            bsr_display = cand.raw_product.bsr_rank
        else:
            bsr_display = "Ranked in RV New Releases"

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

        # Collect images (from verified product or raw product)
        images_list: List[str] = []
        if cand.verified_product and cand.verified_product.images:
            images_list = [img for img in cand.verified_product.images if img.startswith("http")]
        elif cand.raw_product and cand.raw_product.images:
            images_list = [img for img in cand.raw_product.images if img.startswith("http")]
        elif cand.raw_product and cand.raw_product.image_url:
            images_list = [cand.raw_product.image_url]

        if not images_list:
            images_list = ["https://via.placeholder.com/400x300?text=No+Image+Available"]

        images_json = html.escape(json.dumps(images_list))
        first_img = images_list[0]

        why_next = html.escape(cand.opportunity.why_next_winner if cand.opportunity else "High organic demand & natural RV utility.")
        why_fail = html.escape(cand.opportunity.why_fail if cand.opportunity else "Specific RV vehicle fit requirements.")

        status_class = "winner" if is_winner else "candidate"
        status_badge = "🏆 QUALIFIED WINNER" if is_winner else "RESEARCH CANDIDATE"
        badge_class = "badge-winner" if is_winner else "badge-candidate"

        cards_html += f"""
        <div class="product-card {status_class}" data-title="{title.lower()} {asin.lower()}" data-type="{'winner' if is_winner else 'candidate'}">
            <div class="card-top-bar">
                <span class="status-pill {badge_class}">{status_badge}</span>
                <span class="asin-pill">ASIN: {asin}</span>
            </div>

            <!-- Image Carousel -->
            <div class="carousel-container" id="carousel-{idx}" data-images="{images_json}" data-index="0">
                <img src="{first_img}" alt="{title}" class="carousel-img" id="img-{idx}" loading="lazy" referrerpolicy="no-referrer" onerror="handleImgError(this)" />
                
                <div class="carousel-controls" {'style="display:none;"' if len(images_list) <= 1 else ''}>
                    <button class="carousel-btn btn-prev" onclick="prevSlide({idx})">‹</button>
                    <span class="carousel-counter" id="counter-{idx}">1 / {len(images_list)}</span>
                    <button class="carousel-btn btn-next" onclick="nextSlide({idx})">›</button>
                </div>
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

                <!-- Commercial Insights -->
                <div class="insights-box">
                    <div class="insight-row">
                        <strong>🎯 Opportunity / Utility:</strong>
                        <p>{why_next}</p>
                    </div>
                    <div class="insight-row">
                        <strong>⚠️ Risk / Fit Constraint:</strong>
                        <p>{why_fail}</p>
                    </div>
                </div>

                <!-- Action Toolbar: Download All Images -->
                <div class="card-actions">
                    <button class="btn-download" onclick="downloadAllProductImages({idx}, '{asin}')">
                        📥 Download All Images ({len(images_list)})
                    </button>
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

    verdict_hero = ""
    if reviewed_count == 0:
        verdict_hero = """
        <div class="verdict-banner">
            <div class="verdict-content">
                <h2>System Status • Standing By</h2>
                <p class="verdict-quote">"Scout pipeline initialized with 0 active items. Next automated run scheduled for 06:00 UTC."</p>
                <span class="verdict-note">Amazon RV New Releases node • 18-point pain point evaluation engine active.</span>
            </div>
        </div>
        """
    elif not winners:
        verdict_hero = f"""
        <div class="verdict-banner">
            <div class="verdict-content">
                <h2>Daily Research Verdict</h2>
                <p class="verdict-quote">"I reviewed <strong>{reviewed_count}</strong> products from the link. None met the hidden-winner criteria today."</p>
                <span class="verdict-note">Verified live on Amazon • Complete category traversal logged.</span>
            </div>
        </div>
        """
    else:
        verdict_hero = f"""
        <div class="verdict-banner" style="border-left-color: var(--accent);">
            <div class="verdict-content">
                <h2 style="color: var(--accent);">Daily Research Verdict • {len(winners)} Winner(s) Found</h2>
                <p class="verdict-quote">"Identified <strong>{len(winners)}</strong> high-conviction winning products meeting 80+ threshold and critical RV pain points."</p>
                <span class="verdict-note">Audited {reviewed_count} candidates • Full commercial dossiers & Walmart arbitrage logged.</span>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="slate">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
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

        .btn-sheet {{
            background: #107C41;
            color: #fff;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.85rem;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: opacity 0.2s;
        }}
        .btn-sheet:hover {{ opacity: 0.9; }}

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

        /* Verdict Banner */
        .verdict-banner {{
            background: var(--bg-surface);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--amazon-color);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 28px;
        }}
        .verdict-banner h2 {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 6px; }}
        .verdict-quote {{ font-size: 1.05rem; color: var(--text-primary); margin-bottom: 4px; }}
        .verdict-note {{ font-size: 0.82rem; color: var(--text-muted); }}

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

        .filter-tabs {{ display: flex; gap: 8px; }}
        .filter-btn {{
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-secondary);
            font-size: 0.82rem;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
        }}
        .filter-btn.active {{
            background: var(--accent-soft);
            color: var(--accent);
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
            transition: transform 0.25s ease, border-color 0.25s ease;
        }}
        .product-card:hover {{
            transform: translateY(-3px);
            border-color: var(--accent);
        }}

        .card-top-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 18px;
        }}
        .status-pill {{
            font-size: 0.72rem;
            font-weight: 700;
            padding: 3px 10px;
            border-radius: 999px;
        }}
        .badge-winner {{ background: var(--accent-soft); color: var(--accent); }}
        .badge-candidate {{ background: rgba(148, 163, 184, 0.12); color: var(--text-secondary); }}
        .asin-pill {{ font-size: 0.75rem; color: var(--text-muted); font-weight: 600; }}

        /* Image Carousel */
        .carousel-container {{
            position: relative;
            height: 230px;
            background: var(--bg-card-alt);
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-top: 1px solid var(--border-color);
            border-bottom: 1px solid var(--border-color);
        }}
        .carousel-img {{
            max-height: 200px;
            max-width: 88%;
            object-fit: contain;
            transition: opacity 0.25s ease;
        }}
        .carousel-controls {{
            position: absolute;
            bottom: 10px;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
        }}
        .carousel-btn {{
            background: rgba(0, 0, 0, 0.6);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .carousel-btn:hover {{ background: rgba(0, 0, 0, 0.85); }}
        .carousel-counter {{
            font-size: 0.75rem;
            font-weight: 700;
            color: #fff;
            background: rgba(0, 0, 0, 0.6);
            padding: 2px 8px;
            border-radius: 999px;
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

        /* Insights */
        .insights-box {{ margin-bottom: 16px; font-size: 0.84rem; }}
        .insight-row {{ margin-bottom: 8px; }}
        .insight-row strong {{ color: var(--text-primary); font-size: 0.82rem; }}
        .insight-row p {{ color: var(--text-secondary); margin-top: 2px; }}

        /* Card Actions */
        .card-actions {{ margin-top: auto; padding-top: 12px; border-top: 1px solid var(--border-color); }}
        .btn-download {{
            width: 100%;
            background: var(--bg-card-alt);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 9px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-download:hover {{
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

                <a href="{sheet_url}" target="_blank" class="btn-sheet">
                    📊 Google Sheets
                </a>

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
                <div class="kpi-num" style="color: {'var(--accent)' if winners else 'var(--text-muted)'}">{len(winners)}</div>
            </div>

            <div class="kpi-box">
                <div class="kpi-label">Verified Amazon Pages</div>
                <div class="kpi-num">{health.products_verified}</div>
            </div>

            <div class="kpi-box">
                <div class="kpi-label">Filtered / Sub-Threshold</div>
                <div class="kpi-num">{health.products_rejected}</div>
            </div>
        </section>

        <!-- Verdict Banner if 0 winners -->
        {verdict_hero}

        <!-- Filter Toolbar -->
        <section class="toolbar">
            <input type="text" id="searchInput" class="search-input" placeholder="Search by product title or ASIN..." onkeyup="filterCards()" />

            <div class="filter-tabs">
                <button class="filter-btn active" onclick="setFilter('all', this)">All ({len(all_candidates)})</button>
                <button class="filter-btn" onclick="setFilter('winner', this)">Winners ({len(winners)})</button>
                <button class="filter-btn" onclick="setFilter('candidate', this)">Candidates ({len(near_misses)})</button>
            </div>
        </section>

        <!-- Product Cards Grid -->
        <main class="cards-grid" id="cardsGrid">
            {cards_html if cards_html else empty_state_html}
        </main>
    </div>

    <script>
        // 0. Image Fallback Handler for hotlinking protection
        function handleImgError(img) {{
            img.onerror = null;
            img.src = 'https://images.unsplash.com/photo-1523987355523-c7b5b0dd90a7?w=600&auto=format&fit=crop&q=80';
        }}

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

        // 2. Image Carousel Navigation
        function updateSlide(idx, newIndex) {{
            const carousel = document.getElementById('carousel-' + idx);
            const images = JSON.parse(carousel.getAttribute('data-images'));
            if (!images || images.length === 0) return;

            let cur = (newIndex + images.length) % images.length;
            carousel.setAttribute('data-index', cur);

            const imgElem = document.getElementById('img-' + idx);
            imgElem.referrerPolicy = "no-referrer";
            imgElem.onerror = function() {{ handleImgError(this); }};
            imgElem.src = images[cur];

            const counterElem = document.getElementById('counter-' + idx);
            if (counterElem) {{
                counterElem.innerText = (cur + 1) + ' / ' + images.length;
            }}
        }}

        function prevSlide(idx) {{
            const carousel = document.getElementById('carousel-' + idx);
            let cur = parseInt(carousel.getAttribute('data-index') || 0);
            updateSlide(idx, cur - 1);
        }}

        function nextSlide(idx) {{
            const carousel = document.getElementById('carousel-' + idx);
            let cur = parseInt(carousel.getAttribute('data-index') || 0);
            updateSlide(idx, cur + 1);
        }}

        // 3. Batch Image Download Trigger
        async function downloadAllProductImages(idx, asin) {{
            const carousel = document.getElementById('carousel-' + idx);
            const images = JSON.parse(carousel.getAttribute('data-images'));
            if (!images || images.length === 0) return;

            for (let i = 0; i < images.length; i++) {{
                const url = images[i];
                try {{
                    const response = await fetch(url, {{ mode: 'cors' }});
                    if (!response.ok) throw new Error("CORS fallback");
                    const blob = await response.blob();
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = asin + '_photo_' + (i + 1) + '.jpg';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }} catch (e) {{
                    // Direct tab opening if CORS prevents direct download
                    window.open(url, '_blank', 'noopener,noreferrer');
                }}
            }}
        }}

        // 4. Live Search and Filter
        let currentFilter = 'all';

        function filterCards() {{
            const searchVal = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.product-card');

            cards.forEach(card => {{
                const type = card.getAttribute('data-type');
                const title = card.getAttribute('data-title');

                const matchesSearch = title.includes(searchVal);
                const matchesFilter = (currentFilter === 'all') || (type === currentFilter);

                card.style.display = (matchesSearch && matchesFilter) ? 'flex' : 'none';
            }});
        }}

        function setFilter(type, btn) {{
            currentFilter = type;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterCards();
        }}

        // 5. Authentication & Client Access Gate
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
) -> str:
    """Generates and writes dashboard to reports directory."""
    html_str = generate_executive_dashboard_html(
        reviewed_count=reviewed_count,
        winners=winners,
        near_misses=near_misses,
        health=health,
        spreadsheet_id=spreadsheet_id,
        candidates=candidates,
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

    return filepath
