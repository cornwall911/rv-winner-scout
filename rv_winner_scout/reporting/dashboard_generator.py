"""Generates an ultra-premium, interactive, dark-mode Executive HTML Dashboard."""

import html
import os
from datetime import datetime, timezone
from typing import List, Optional

from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport


def generate_executive_dashboard_html(
    reviewed_count: int,
    winners: List[ProductCandidate],
    near_misses: List[ProductCandidate],
    health: RunHealthReport,
    spreadsheet_id: Optional[str] = None,
) -> str:
    """Renders a self-contained, responsive, glassmorphic HTML executive report."""
    run_date = health.end_time.strftime("%Y-%m-%d")
    run_time = health.end_time.strftime("%H:%M:%S UTC")
    sheet_url = (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=1055207818"
        if spreadsheet_id
        else "https://docs.google.com"
    )

    # Winners Cards HTML
    winners_html = ""
    if winners:
        for i, w in enumerate(winners, 1):
            raw_title = w.verified_product.title if w.verified_product else w.raw_product.title
            title = html.escape(raw_title)
            score = w.scores.total_score if w.scores else 0.0
            price = f"${w.verified_product.displayed_price:.2f}" if w.verified_product and w.verified_product.displayed_price else "N/A"
            asin = w.asin
            amazon_url = w.canonical_url

            walmart_status = w.walmart.status.value if w.walmart else "NOT FOUND"
            walmart_price = f"${w.walmart.displayed_price:.2f}" if w.walmart and w.walmart.displayed_price else "N/A"
            walmart_url = w.walmart.url if w.walmart and w.walmart.url else "#"
            walmart_query = html.escape(w.walmart.search_query_used if w.walmart else "N/A")

            hook = html.escape(w.opportunity.visual_hook if w.opportunity else "High curiosity demonstration")
            fb_angle = html.escape(w.opportunity.facebook_angle if w.opportunity else "Frustrating RV pain-point resolution")
            why_next = html.escape(w.opportunity.why_next_winner if w.opportunity else "Strong novelty and organic viral fit.")
            why_fail = html.escape(w.opportunity.why_fail if w.opportunity else "Specific RV setup dependency.")

            # Generate 3 Creative Viral Post Angles
            angle_1 = html.escape(
                f"Has anyone else seen this for RVs yet, or am I the only one late to the party? 👀 Honestly had no clue this existed until today: {amazon_url}"
            )
            angle_2 = html.escape(
                f"The #1 thing that drives me crazy about our setup solved in 2 minutes. No complicated install, just works. Dropping the link in the comments for anyone with the same headache!"
            )
            angle_3 = html.escape(
                f"RV Hack of the week: Saw this selling fast on Amazon for {price}, but found the exact direct alternative on Walmart for {walmart_price}! Check both before buying: {amazon_url}"
            )

            score_color = "#10b981" if score >= 80 else "#f59e0b"

            winners_html += f"""
            <div class="winner-card">
                <div class="winner-header">
                    <div class="badge-rank">WINNER #{i}</div>
                    <div class="score-circle" style="border-color: {score_color}">
                        <span class="score-number">{score:.1f}</span>
                        <span class="score-label">/ 100</span>
                    </div>
                </div>

                <h3 class="product-title">{title}</h3>
                <div class="meta-row">
                    <span class="tag tag-asin">ASIN: {asin}</span>
                    <span class="tag tag-price">Amazon: {price}</span>
                    <span class="tag tag-newness">{w.newness.value}</span>
                    <span class="tag tag-exposure">Exposure: {w.exposure_level.value}</span>
                </div>

                <div class="arbitrage-box">
                    <div class="arb-col">
                        <span class="arb-label">Amazon Verified</span>
                        <span class="arb-val">{price}</span>
                        <a href="{amazon_url}" target="_blank" class="btn-link btn-amazon">View on Amazon ↗</a>
                    </div>
                    <div class="arb-vs">VS</div>
                    <div class="arb-col">
                        <span class="arb-label">Walmart ({walmart_status})</span>
                        <span class="arb-val">{walmart_price}</span>
                        <a href="{walmart_url}" target="_blank" class="btn-link btn-walmart">Check Walmart ↗</a>
                    </div>
                </div>

                <div class="analysis-section">
                    <div class="analysis-item">
                        <strong>🎯 The Breakthrough DNA:</strong>
                        <p>{why_next}</p>
                    </div>
                    <div class="analysis-item">
                        <strong>⚠️ Biggest Risk (Why It Could Fail):</strong>
                        <p>{why_fail}</p>
                    </div>
                </div>

                <div class="creative-studio">
                    <div class="studio-title">⚡ Ready-to-Post Viral Facebook Angles (Click to Copy):</div>
                    
                    <div class="copy-box">
                        <div class="copy-header">
                            <span>Angle 1: Pure Curiosity Hook</span>
                            <button class="btn-copy" onclick="copyText('copy-1-{i}', this)">Copy</button>
                        </div>
                        <p id="copy-1-{i}">{angle_1}</p>
                    </div>

                    <div class="copy-box">
                        <div class="copy-header">
                            <span>Angle 2: Frustrating Nightmare Solved</span>
                            <button class="btn-copy" onclick="copyText('copy-2-{i}', this)">Copy</button>
                        </div>
                        <p id="copy-2-{i}">{angle_2}</p>
                    </div>

                    <div class="copy-box">
                        <div class="copy-header">
                            <span>Angle 3: Walmart vs Amazon Price Hack</span>
                            <button class="btn-copy" onclick="copyText('copy-3-{i}', this)">Copy</button>
                        </div>
                        <p id="copy-3-{i}">{angle_3}</p>
                    </div>
                </div>
            </div>
            """
    else:
        near_misses_html = ""
        for i, nm in enumerate(near_misses[:3], 1):
            nm_title = html.escape(nm.verified_product.title if nm.verified_product else nm.raw_product.title)
            nm_score = nm.scores.total_score if nm.scores else 0.0
            nm_reason = html.escape(nm.rejection_reason or "Below 80 threshold")
            nm_link = nm.canonical_url

            near_misses_html += f"""
            <div class="near-miss-card">
                <div class="nm-top">
                    <span class="nm-rank">#{i}</span>
                    <span class="nm-score">{nm_score:.1f} / 100</span>
                </div>
                <div class="nm-title">{nm_title}</div>
                <div class="nm-reason"><strong>Bottleneck:</strong> {nm_reason}</div>
                <a href="{nm_link}" target="_blank" class="nm-link">Inspect on Amazon ↗</a>
            </div>
            """

        winners_html = f"""
        <div class="verdict-banner">
            <div class="verdict-icon">🛡️</div>
            <div class="verdict-content">
                <h2>Daily Research Verdict</h2>
                <p class="verdict-text">"I reviewed <strong>{reviewed_count}</strong> products from the link. None met the hidden-winner criteria today."</p>
                <span class="verdict-sub">Audit principle enforced: Accuracy & Zero False Positives > Saturated Inventory.</span>
            </div>
        </div>

        <h3 class="section-title">Top Near-Miss Candidates Evaluated Today</h3>
        <div class="near-misses-grid">
            {near_misses_html}
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RV Winner Scout — Executive Dashboard ({run_date})</title>
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-card: #151d30;
            --bg-card-hover: #1c2640;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-blue: #3b82f6;
            --border-color: #263352;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            padding: 24px 16px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        
        /* Header */
        .dashboard-header {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 24px;
            gap: 16px;
        }}
        .brand-title {{
            font-size: 1.6rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .brand-subtitle {{ font-size: 0.88rem; color: var(--text-muted); margin-top: 4px; }}
        .header-actions {{ display: flex; gap: 12px; align-items: center; }}
        .btn-sheet {{
            background: #107c41;
            color: #fff;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.88rem;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: opacity 0.2s;
        }}
        .btn-sheet:hover {{ opacity: 0.9; }}

        /* KPI Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .kpi-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }}
        .kpi-num {{ font-size: 2rem; font-weight: 800; color: #38bdf8; margin-bottom: 4px; }}
        .kpi-label {{ font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px; }}

        /* Verdict Banner */
        .verdict-banner {{
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--accent-amber);
            border-radius: 12px;
            padding: 24px;
            display: flex;
            gap: 18px;
            margin-bottom: 32px;
            align-items: center;
        }}
        .verdict-icon {{ font-size: 2.4rem; }}
        .verdict-text {{ font-size: 1.15rem; color: #fff; margin: 6px 0; }}
        .verdict-sub {{ font-size: 0.85rem; color: var(--text-muted); }}

        /* Winner Card */
        .winner-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 28px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .winner-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
        .badge-rank {{
            background: linear-gradient(135deg, #10b981, #059669);
            color: #fff;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 700;
        }}
        .score-circle {{
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border: 3px solid;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: rgba(0,0,0,0.2);
        }}
        .score-number {{ font-size: 1.2rem; font-weight: 800; }}
        .score-label {{ font-size: 0.65rem; color: var(--text-muted); }}
        .product-title {{ font-size: 1.25rem; font-weight: 700; margin-bottom: 12px; line-height: 1.4; }}
        
        .meta-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
        .tag {{
            background: rgba(255,255,255,0.06);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
            color: var(--text-muted);
        }}
        .tag-price {{ color: #34d399; }}

        /* Arbitrage Box */
        .arbitrage-box {{
            background: rgba(11, 15, 25, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            align-items: center;
            justify-content: space-around;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .arb-col {{ text-align: center; }}
        .arb-label {{ font-size: 0.78rem; color: var(--text-muted); display: block; margin-bottom: 4px; }}
        .arb-val {{ font-size: 1.4rem; font-weight: 800; display: block; margin-bottom: 8px; }}
        .arb-vs {{ font-weight: 900; color: var(--text-muted); font-size: 0.9rem; }}
        .btn-link {{
            padding: 6px 14px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 0.78rem;
            font-weight: 700;
            display: inline-block;
        }}
        .btn-amazon {{ background: #f59e0b; color: #000; }}
        .btn-walmart {{ background: #0071dc; color: #fff; }}

        /* Analysis */
        .analysis-section {{ margin-bottom: 20px; }}
        .analysis-item {{ margin-bottom: 12px; font-size: 0.92rem; }}
        .analysis-item strong {{ color: #38bdf8; display: block; margin-bottom: 3px; }}

        /* Creative Studio */
        .creative-studio {{
            background: rgba(11, 15, 25, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
        }}
        .studio-title {{ font-weight: 700; font-size: 0.92rem; margin-bottom: 12px; color: #fbbf24; }}
        .copy-box {{
            background: rgba(255,255,255,0.03);
            border-left: 3px solid #3b82f6;
            padding: 10px 14px;
            border-radius: 6px;
            margin-bottom: 10px;
        }}
        .copy-header {{ display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted); margin-bottom: 4px; }}
        .btn-copy {{
            background: #3b82f6;
            color: #fff;
            border: none;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.72rem;
            cursor: pointer;
        }}
        .btn-copy:hover {{ opacity: 0.85; }}

        /* Near Misses */
        .section-title {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 16px; color: #94a3b8; }}
        .near-misses-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
        .near-miss-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
        }}
        .nm-top {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .nm-rank {{ font-weight: 800; color: var(--accent-amber); }}
        .nm-score {{ font-weight: 700; color: #94a3b8; font-size: 0.88rem; }}
        .nm-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 8px; line-height: 1.4; }}
        .nm-reason {{ font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px; }}
        .nm-link {{ color: #38bdf8; text-decoration: none; font-size: 0.8rem; font-weight: 600; }}

        footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="dashboard-header">
            <div>
                <div class="brand-title">RV WINNER SCOUT</div>
                <div class="brand-subtitle">Automated Viral Affiliate Intelligence • Generated {run_date} ({run_time})</div>
            </div>
            <div class="header-actions">
                <a href="{sheet_url}" target="_blank" class="btn-sheet">
                    📊 Open Research Log Sheet
                </a>
            </div>
        </header>

        <!-- KPI Grid -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-num">{reviewed_count}</div>
                <div class="kpi-label">Products Audited</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: {'#10b981' if winners else '#94a3b8'}">{len(winners)}</div>
                <div class="kpi-label">Hidden Winners Discovered</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num">{health.products_verified}</div>
                <div class="kpi-label">Live Pages Verified</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num">{health.products_rejected}</div>
                <div class="kpi-label">Sub-Threshold / Rejected</div>
            </div>
        </div>

        <!-- Main Results -->
        {winners_html}

        <!-- Footer -->
        <footer>
            RV Winner Scout Autonomous Pipeline • Run ID: {health.run_id} • Strictly Verified Live
        </footer>
    </div>

    <script>
        function copyText(elemId, btn) {{
            const text = document.getElementById(elemId).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const orig = btn.innerText;
                btn.innerText = "Copied! ✓";
                btn.style.background = "#10b981";
                setTimeout(() => {{
                    btn.innerText = orig;
                    btn.style.background = "#3b82f6";
                }}, 1500);
            }}).catch(err => {{
                console.error("Failed to copy", err);
            }});
        }}
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
) -> str:
    """Generates and writes dashboard to reports directory."""
    html_str = generate_executive_dashboard_html(
        reviewed_count=reviewed_count,
        winners=winners,
        near_misses=near_misses,
        health=health,
        spreadsheet_id=spreadsheet_id,
    )
    reports_dir = os.path.join(data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"dashboard_{health.run_id}.html"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_str)

    # Also maintain latest_dashboard.html for easy browser opening / GitHub Pages
    latest_path = os.path.join(reports_dir, "latest_dashboard.html")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    return filepath
